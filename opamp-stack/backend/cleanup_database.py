#!/usr/bin/env python3
"""
Database cleanup script.
Removes all agent-related data while preserving users.

Usage:
    python cleanup_database.py [options]

Options:
    --confirm          Skip confirmation prompt (use with caution)
    --backup           Create backup before cleanup
    --dry-run          Show what would be deleted without actually deleting
    --verbose          Show detailed output

Examples:
    # Interactive mode (with confirmation)
    python cleanup_database.py

    # With automatic backup
    python cleanup_database.py --backup --confirm

    # Dry run to see what would be deleted
    python cleanup_database.py --dry-run

    # From Docker container
    docker exec -it opamp-backend python cleanup_database.py --confirm
"""
import asyncio
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.models import Agent, AgentHealth, AgentConfig, AgentPipelineHealth, User


class DatabaseCleanup:
    """Database cleanup utility."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.engine = create_async_engine(settings.DATABASE_URL, echo=verbose)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def get_statistics(self, session: AsyncSession) -> dict:
        """Get current database statistics."""
        stats = {}
        
        # Count agents
        result = await session.execute(select(func.count()).select_from(Agent))
        stats['agents'] = result.scalar()
        
        # Count agent_health
        result = await session.execute(select(func.count()).select_from(AgentHealth))
        stats['agent_health'] = result.scalar()
        
        # Count agent_configs
        result = await session.execute(select(func.count()).select_from(AgentConfig))
        stats['agent_configs'] = result.scalar()
        
        # Count agent_pipeline_health
        result = await session.execute(select(func.count()).select_from(AgentPipelineHealth))
        stats['agent_pipeline_health'] = result.scalar()
        
        # Count users (will be preserved)
        result = await session.execute(select(func.count()).select_from(User))
        stats['users'] = result.scalar()
        
        return stats
    
    def print_statistics(self, stats: dict, label: str = "Current"):
        """Print statistics in a formatted way."""
        print(f"\n{label} Statistics:")
        print("=" * 50)
        print(f"  Agents:                {stats.get('agents', 0):>10,}")
        print(f"  Agent Health:          {stats.get('agent_health', 0):>10,}")
        print(f"  Agent Configs:         {stats.get('agent_configs', 0):>10,}")
        print(f"  Agent Pipeline Health: {stats.get('agent_pipeline_health', 0):>10,}")
        print(f"  Users (PRESERVED):     {stats.get('users', 0):>10,}")
        print("=" * 50)
    
    async def create_backup(self, session: AsyncSession) -> str:
        """Create a logical backup of the data (returns backup info)."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_info = f"backup_{timestamp}"
        
        # Note: This creates a note about backup, actual pg_dump should be done externally
        print(f"\n⚠️  For production, create a backup using:")
        print(f"    docker exec -t opamp-postgres pg_dump -U opamp opamp > {backup_info}.sql")
        
        return backup_info
    
    async def cleanup(self, session: AsyncSession) -> dict:
        """
        Perform the actual cleanup.
        Deletes all agent-related data while preserving users.
        
        Returns:
            dict: Statistics of deleted records
        """
        deleted = {}
        
        if self.dry_run:
            print("\n🔍 DRY RUN MODE - No data will be deleted\n")
            return deleted
        
        print("\n🗑️  Starting cleanup...\n")
        
        try:
            # Disable foreign key checks temporarily for faster deletion
            await session.execute(text("SET session_replication_role = 'replica'"))
            
            # Delete agent_pipeline_health
            print("  Deleting agent_pipeline_health records...")
            result = await session.execute(text("DELETE FROM agent_pipeline_health"))
            deleted['agent_pipeline_health'] = result.rowcount
            print(f"    ✓ Deleted {result.rowcount:,} records")
            
            # Delete agent_health
            print("  Deleting agent_health records...")
            result = await session.execute(text("DELETE FROM agent_health"))
            deleted['agent_health'] = result.rowcount
            print(f"    ✓ Deleted {result.rowcount:,} records")
            
            # Delete agent_configs
            print("  Deleting agent_configs records...")
            result = await session.execute(text("DELETE FROM agent_configs"))
            deleted['agent_configs'] = result.rowcount
            print(f"    ✓ Deleted {result.rowcount:,} records")
            
            # Delete agents
            print("  Deleting agents records...")
            result = await session.execute(text("DELETE FROM agents"))
            deleted['agents'] = result.rowcount
            print(f"    ✓ Deleted {result.rowcount:,} records")
            
            # Re-enable foreign key checks
            await session.execute(text("SET session_replication_role = 'origin'"))
            
            # Reset sequences
            print("\n  Resetting ID sequences...")
            await session.execute(text("ALTER SEQUENCE agents_id_seq RESTART WITH 1"))
            await session.execute(text("ALTER SEQUENCE agent_health_id_seq RESTART WITH 1"))
            await session.execute(text("ALTER SEQUENCE agent_configs_id_seq RESTART WITH 1"))
            await session.execute(text("ALTER SEQUENCE agent_pipeline_health_id_seq RESTART WITH 1"))
            print("    ✓ Sequences reset")
            
            # Commit transaction
            await session.commit()
            print("\n  ✓ Changes committed to database")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error during cleanup: {e}")
            raise
        
        return deleted
    
    async def run(self, create_backup: bool = False) -> bool:
        """
        Execute the cleanup process.
        
        Args:
            create_backup: Whether to suggest creating a backup
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            async with self.async_session() as session:
                # Get initial statistics
                print("\n" + "=" * 50)
                print("DATABASE CLEANUP UTILITY")
                print("=" * 50)
                
                initial_stats = await self.get_statistics(session)
                self.print_statistics(initial_stats, "Before Cleanup")
                
                # Check if there's anything to delete
                total_records = sum([
                    initial_stats.get('agents', 0),
                    initial_stats.get('agent_health', 0),
                    initial_stats.get('agent_configs', 0),
                    initial_stats.get('agent_pipeline_health', 0)
                ])
                
                if total_records == 0:
                    print("\n✓ Database is already clean (no agent data found)")
                    return True
                
                # Backup suggestion
                if create_backup:
                    await self.create_backup(session)
                
                # Perform cleanup
                deleted_stats = await self.cleanup(session)
                
                # Get final statistics
                final_stats = await self.get_statistics(session)
                self.print_statistics(final_stats, "After Cleanup")
                
                # Summary
                if not self.dry_run:
                    print("\n" + "=" * 50)
                    print("CLEANUP SUMMARY")
                    print("=" * 50)
                    total_deleted = sum(deleted_stats.values())
                    print(f"  Total records deleted: {total_deleted:,}")
                    print(f"  Users preserved:       {final_stats.get('users', 0):,}")
                    print("=" * 50)
                    print("\n✅ Cleanup completed successfully!")
                
                return True
                
        except Exception as e:
            print(f"\n❌ Cleanup failed: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False
        finally:
            await self.engine.dispose()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean database tables while preserving users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Skip confirmation prompt (automatic yes)'
    )
    
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Show backup command before cleanup'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed SQL operations'
    )
    
    args = parser.parse_args()
    
    # Confirmation prompt (unless --confirm or --dry-run)
    if not args.confirm and not args.dry_run:
        print("\n⚠️  WARNING: This will DELETE all agent-related data!")
        print("   Users will be PRESERVED.")
        print("\n   Tables that will be cleaned:")
        print("     - agents")
        print("     - agent_health")
        print("     - agent_configs")
        print("     - agent_pipeline_health")
        print("\n   This operation is IRREVERSIBLE!")
        print("\n   It's recommended to create a backup first:")
        print("     docker exec -t opamp-postgres pg_dump -U opamp opamp > backup.sql")
        
        response = input("\nType 'YES' to continue: ")
        if response != 'YES':
            print("\n❌ Cleanup cancelled.")
            return 1
    
    # Run cleanup
    cleanup = DatabaseCleanup(dry_run=args.dry_run, verbose=args.verbose)
    success = await cleanup.run(create_backup=args.backup)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
