#!/usr/bin/env python3
"""
Fix duplicate hostname records in the database.

This script identifies and merges duplicate agent records that have
the same hostname but different instance_ids. It keeps the most recent
record and merges all historical data.

Usage:
    python fix_duplicate_hostnames.py [--dry-run] [--hostname HOSTNAME]

Examples:
    # Preview what would be fixed
    python fix_duplicate_hostnames.py --dry-run
    
    # Fix specific hostname
    python fix_duplicate_hostnames.py --hostname DESKTOP-C49UQO6
    
    # Fix all duplicates
    python fix_duplicate_hostnames.py
    
    # From container
    docker exec -it opamp-backend python fix_duplicate_hostnames.py
"""
import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.models import Agent, AgentHealth, AgentConfig, AgentPipelineHealth


class DuplicateHostnameFixer:
    """Fixes duplicate hostname records."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.engine = create_async_engine(settings.DATABASE_URL, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def find_duplicates(self, session: AsyncSession, hostname: str = None) -> dict:
        """Find agents with duplicate hostnames."""
        
        if hostname:
            # Find specific hostname duplicates
            query = select(Agent).where(Agent.host_name == hostname).order_by(Agent.last_seen_at.desc())
        else:
            # Find all duplicates
            # First get hostnames with duplicates
            subquery = (
                select(Agent.host_name)
                .where(Agent.host_name.isnot(None))
                .group_by(Agent.host_name)
                .having(func.count(Agent.id) > 1)
            )
            result = await session.execute(subquery)
            duplicate_hostnames = [row[0] for row in result.all()]
            
            if not duplicate_hostnames:
                return {}
            
            # Get all agents with duplicate hostnames
            query = select(Agent).where(Agent.host_name.in_(duplicate_hostnames)).order_by(
                Agent.host_name, Agent.last_seen_at.desc()
            )
        
        result = await session.execute(query)
        agents = result.scalars().all()
        
        # Group by hostname
        duplicates = {}
        for agent in agents:
            if agent.host_name not in duplicates:
                duplicates[agent.host_name] = []
            duplicates[agent.host_name].append(agent)
        
        # Filter to only include actual duplicates
        return {k: v for k, v in duplicates.items() if len(v) > 1}
    
    async def merge_agents(self, session: AsyncSession, hostname: str, agents: list) -> dict:
        """Merge duplicate agents, keeping the most recent one."""
        
        if len(agents) < 2:
            return {"status": "skip", "reason": "No duplicates"}
        
        # Sort by last_seen_at descending (most recent first)
        agents_sorted = sorted(agents, key=lambda a: a.last_seen_at or datetime.min, reverse=True)
        
        # Keep the most recent agent
        keep_agent = agents_sorted[0]
        remove_agents = agents_sorted[1:]
        
        stats = {
            "hostname": hostname,
            "kept_instance_id": keep_agent.instance_id,
            "removed_instance_ids": [a.instance_id for a in remove_agents],
            "health_merged": 0,
            "configs_merged": 0,
            "pipeline_merged": 0
        }
        
        print(f"\n  Hostname: {hostname}")
        print(f"  Keeping:  {keep_agent.instance_id} (last_seen: {keep_agent.last_seen_at})")
        
        for remove_agent in remove_agents:
            print(f"  Removing: {remove_agent.instance_id} (last_seen: {remove_agent.last_seen_at})")
            
            if not self.dry_run:
                # Merge agent_health
                result = await session.execute(
                    text("""
                        UPDATE agent_health 
                        SET instance_id = :keep_id 
                        WHERE instance_id = :remove_id
                    """),
                    {"keep_id": keep_agent.instance_id, "remove_id": remove_agent.instance_id}
                )
                stats["health_merged"] += result.rowcount
                
                # Merge agent_configs
                result = await session.execute(
                    text("""
                        UPDATE agent_configs 
                        SET instance_id = :keep_id 
                        WHERE instance_id = :remove_id
                    """),
                    {"keep_id": keep_agent.instance_id, "remove_id": remove_agent.instance_id}
                )
                stats["configs_merged"] += result.rowcount
                
                # Merge agent_pipeline_health
                result = await session.execute(
                    text("""
                        UPDATE agent_pipeline_health 
                        SET instance_id = :keep_id 
                        WHERE instance_id = :remove_id
                    """),
                    {"keep_id": keep_agent.instance_id, "remove_id": remove_agent.instance_id}
                )
                stats["pipeline_merged"] += result.rowcount
                
                # Delete the duplicate agent
                await session.delete(remove_agent)
        
        if not self.dry_run:
            await session.commit()
            print(f"  ✓ Merged: health={stats['health_merged']}, configs={stats['configs_merged']}, pipeline={stats['pipeline_merged']}")
        else:
            print(f"  [DRY RUN] Would merge records")
        
        return stats
    
    async def run(self, hostname: str = None) -> bool:
        """Execute the fix process."""
        
        try:
            async with self.async_session() as session:
                print("\n" + "=" * 60)
                print("DUPLICATE HOSTNAME FIXER")
                print("=" * 60)
                
                if self.dry_run:
                    print("\n🔍 DRY RUN MODE - No changes will be made\n")
                
                # Find duplicates
                print("\nSearching for duplicate hostnames...")
                duplicates = await self.find_duplicates(session, hostname)
                
                if not duplicates:
                    print("✓ No duplicate hostnames found!")
                    return True
                
                print(f"\nFound {len(duplicates)} hostname(s) with duplicates:")
                for hn, agents in duplicates.items():
                    print(f"  - {hn}: {len(agents)} records")
                
                # Fix each hostname
                print("\n" + "=" * 60)
                print("MERGING DUPLICATES")
                print("=" * 60)
                
                all_stats = []
                for hn, agents in duplicates.items():
                    stats = await self.merge_agents(session, hn, agents)
                    all_stats.append(stats)
                
                # Summary
                print("\n" + "=" * 60)
                print("SUMMARY")
                print("=" * 60)
                
                total_removed = sum(len(s["removed_instance_ids"]) for s in all_stats)
                total_health = sum(s["health_merged"] for s in all_stats)
                total_configs = sum(s["configs_merged"] for s in all_stats)
                total_pipeline = sum(s["pipeline_merged"] for s in all_stats)
                
                print(f"  Hostnames processed:     {len(all_stats)}")
                print(f"  Duplicate agents removed: {total_removed}")
                
                if not self.dry_run:
                    print(f"  Health records merged:    {total_health}")
                    print(f"  Config records merged:    {total_configs}")
                    print(f"  Pipeline records merged:  {total_pipeline}")
                    print("\n✅ Duplicates fixed successfully!")
                else:
                    print("\n🔍 Dry run complete. Use without --dry-run to apply changes.")
                
                print("=" * 60)
                
                return True
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await self.engine.dispose()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix duplicate hostname records in database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be fixed without making changes'
    )
    
    parser.add_argument(
        '--hostname',
        type=str,
        help='Fix only specific hostname (e.g., DESKTOP-C49UQO6)'
    )
    
    args = parser.parse_args()
    
    # Confirmation for actual fix
    if not args.dry_run:
        print("\n⚠️  WARNING: This will merge duplicate agent records!")
        print("   - The most recent agent record will be kept")
        print("   - Older duplicate records will be deleted")
        print("   - Historical data will be merged to the kept record")
        print("\n   This operation is IRREVERSIBLE!")
        
        if args.hostname:
            print(f"\n   Target: {args.hostname}")
        else:
            print("\n   Target: ALL duplicate hostnames")
        
        response = input("\nType 'YES' to continue: ")
        if response != 'YES':
            print("\n❌ Operation cancelled.")
            return 1
    
    # Run fixer
    fixer = DuplicateHostnameFixer(dry_run=args.dry_run)
    success = await fixer.run(hostname=args.hostname)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
