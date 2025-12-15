"""
Repository layer for Agent database operations.
Provides CRUD operations for Agent model.
"""
import logging
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, update
from sqlalchemy.orm import selectinload

from app.models.models import Agent, AgentHealth, AgentConfig, AgentPipelineHealth
from app.schemas import AgentCreate, AgentUpdate

logger = logging.getLogger(__name__)


class AgentRepository:
    """Repository for Agent database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, agent_data: AgentCreate) -> Agent:
        """Create a new agent."""
        agent = Agent(**agent_data.model_dump())
        agent.last_seen_at = datetime.utcnow()
        
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)
        return agent
    
    async def get_by_instance_id(self, instance_id: str) -> Optional[Agent]:
        """Get agent by instance_id."""
        result = await self.db.execute(
            select(Agent).where(Agent.instance_id == instance_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_host_name(self, host_name: str) -> Optional[Agent]:
        """Get agent by host_name."""
        result = await self.db.execute(
            select(Agent).where(Agent.host_name == host_name)
        )
        return result.scalar_one_or_none()
    
    async def get_by_instance_id_with_relations(self, instance_id: str) -> Optional[Agent]:
        """Get agent with health and config relations."""
        result = await self.db.execute(
            select(Agent)
            .options(selectinload(Agent.health_records), selectinload(Agent.configs))
            .where(Agent.instance_id == instance_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Agent]:
        """Get all agents with pagination."""
        result = await self.db.execute(
            select(Agent)
            .order_by(desc(Agent.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_all_filtered(
        self, 
        skip: int = 0, 
        limit: int = 100,
        os_type: Optional[str] = None,
        connected: Optional[bool] = None,
        healthy: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[Agent]:
        """Get all agents with pagination and filters."""
        query = select(Agent)
        
        # Apply filters
        if os_type:
            query = query.where(Agent.os_type == os_type)
        
        if connected is not None:
            query = query.where(Agent.is_connected == connected)
        
        if healthy is not None:
            query = query.where(Agent.healthy == healthy)
        
        if search:
            # Search in hostname, instance_id, or service_name
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Agent.host_name.ilike(search_pattern),
                    Agent.instance_id.ilike(search_pattern),
                    Agent.service_name.ilike(search_pattern)
                )
            )
        
        # Apply ordering and pagination
        query = query.order_by(desc(Agent.updated_at)).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def count_filtered(
        self,
        os_type: Optional[str] = None,
        connected: Optional[bool] = None,
        healthy: Optional[bool] = None,
        search: Optional[str] = None
    ) -> int:
        """Count total number of agents with filters."""
        query = select(func.count(Agent.id))
        
        # Apply same filters as get_all_filtered
        if os_type:
            query = query.where(Agent.os_type == os_type)
        
        if connected is not None:
            query = query.where(Agent.is_connected == connected)
        
        if healthy is not None:
            query = query.where(Agent.healthy == healthy)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Agent.host_name.ilike(search_pattern),
                    Agent.instance_id.ilike(search_pattern),
                    Agent.service_name.ilike(search_pattern)
                )
            )
        
        result = await self.db.execute(query)
        return result.scalar_one()
    
    async def count(self) -> int:
        """Count total number of agents."""
        result = await self.db.execute(select(func.count(Agent.id)))
        return result.scalar_one()
    
    async def update(self, agent: Agent, agent_data: AgentUpdate) -> Agent:
        """Update agent information."""
        update_data = agent_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(agent, field, value)
        
        agent.last_seen_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(agent)
        return agent
    
    async def upsert(self, instance_id: str, agent_data: dict) -> Agent:
        """Create or update an agent."""
        agent = await self.get_by_instance_id(instance_id)
        
        if agent:
            # Update existing agent
            for field, value in agent_data.items():
                if hasattr(agent, field):
                    setattr(agent, field, value)
            agent.last_seen_at = datetime.utcnow()
        else:
            # Create new agent
            agent = Agent(**agent_data)
            agent.last_seen_at = datetime.utcnow()
            self.db.add(agent)
        
        await self.db.commit()
        await self.db.refresh(agent)
        return agent
    
    async def upsert_by_hostname(self, instance_id: str, host_name: str, agent_data: dict) -> Agent:
        """Create or update an agent using hostname as sync key.
        
        When USE_HOSTNAME_AS_SYNC_KEY is enabled, this method:
        1. First tries to find agent by hostname
        2. If found, updates it with new instance_id and data
        3. If not found, falls back to instance_id lookup
        4. Creates new agent if neither hostname nor instance_id exist
        
        This allows agents to maintain their history even when instance_id changes.
        """
        # Try to find by hostname first
        agent = await self.get_by_host_name(host_name)
        
        old_instance_id = None
        if agent:
            # Found by hostname - need to check if instance_id changed
            old_instance_id = agent.instance_id
        else:
            # Fallback to instance_id
            agent = await self.get_by_instance_id(instance_id)
        
        if agent:
            # Update existing agent
            for field, value in agent_data.items():
                if hasattr(agent, field):
                    setattr(agent, field, value)
            
            # If instance_id changed, update related tables
            if old_instance_id and old_instance_id != instance_id:
                logger.info(f"Hostname '{host_name}': instance_id changed from '{old_instance_id}' to '{instance_id}' - updating related records")
                await self._update_related_instance_ids(old_instance_id, instance_id)
                # Explicitly update the instance_id
                agent.instance_id = instance_id
            
            agent.last_seen_at = datetime.utcnow()
        else:
            # Create new agent
            agent = Agent(**agent_data)
            agent.last_seen_at = datetime.utcnow()
            self.db.add(agent)
        
        await self.db.commit()
        await self.db.refresh(agent)
        return agent
    
    async def bulk_upsert(self, agents_data: List[dict]) -> List[Agent]:
        """Bulk create or update agents.
        
        Optimized for performance with large batches:
        - Single query to fetch existing agents (by instance_id or hostname)
        - Batch updates and inserts
        - Single commit
        - Supports USE_HOSTNAME_AS_SYNC_KEY mode
        
        Args:
            agents_data: List of agent data dicts with instance_id
            
        Returns:
            List of created/updated Agent objects
        """
        if not agents_data:
            return []
        
        from app.core.config import settings
        
        # Extract instance_ids and hostnames
        instance_ids = [data['instance_id'] for data in agents_data]
        hostnames = [data.get('host_name') for data in agents_data if data.get('host_name')]
        
        logger.info(f"bulk_upsert: USE_HOSTNAME_AS_SYNC_KEY={settings.USE_HOSTNAME_AS_SYNC_KEY}, agents={len(agents_data)}, hostnames={len(hostnames)}")
        
        # Fetch existing agents by instance_id AND hostname (if hostname sync is enabled)
        existing_agents_by_instance = {}
        existing_agents_by_hostname = {}
        
        # Always fetch by instance_id first
        result = await self.db.execute(
            select(Agent).where(Agent.instance_id.in_(instance_ids))
        )
        for agent in result.scalars().all():
            existing_agents_by_instance[agent.instance_id] = agent
            if agent.host_name:
                existing_agents_by_hostname[agent.host_name] = agent
        
        logger.info(f"Found {len(existing_agents_by_instance)} agents by instance_id, {len(existing_agents_by_hostname)} with hostnames")
        
        # If hostname sync is enabled, also fetch by hostname
        if settings.USE_HOSTNAME_AS_SYNC_KEY and hostnames:
            result = await self.db.execute(
                select(Agent).where(Agent.host_name.in_(hostnames))
            )
            for agent in result.scalars().all():
                if agent.host_name:
                    existing_agents_by_hostname[agent.host_name] = agent
        
        updated_agents = []
        new_agents = []
        now = datetime.utcnow()
        
        # Separate updates and inserts
        for data in agents_data:
            instance_id = data['instance_id']
            host_name = data.get('host_name')
            
            agent = None
            old_instance_id = None
            
            # Find existing agent
            if settings.USE_HOSTNAME_AS_SYNC_KEY and host_name:
                # Try hostname first
                agent = existing_agents_by_hostname.get(host_name)
                if agent:
                    old_instance_id = agent.instance_id
                    logger.info(f"[HOSTNAME-SYNC] Found agent by hostname '{host_name}': existing instance_id='{agent.instance_id}', new instance_id='{instance_id}'")
                else:
                    logger.info(f"[HOSTNAME-SYNC] No existing agent found for hostname '{host_name}', will check instance_id")
            
            if not agent:
                # Fallback to instance_id
                agent = existing_agents_by_instance.get(instance_id)
                if agent:
                    logger.info(f"[HOSTNAME-SYNC] Found agent by instance_id '{instance_id}'")
                else:
                    logger.info(f"[HOSTNAME-SYNC] No existing agent found for instance_id '{instance_id}', will create new")
            
            if agent:
                # Update existing agent
                if old_instance_id and old_instance_id != instance_id:
                    logger.info(f"Hostname '{host_name}': instance_id changed from '{old_instance_id}' to '{instance_id}' - CASCADE update will preserve history")
                
                # Update all fields including instance_id
                # ON UPDATE CASCADE foreign keys will automatically update related tables
                for field, value in data.items():
                    if hasattr(agent, field):
                        setattr(agent, field, value)
                
                agent.last_seen_at = now
                updated_agents.append(agent)
            else:
                # Create new
                agent = Agent(**data)
                agent.last_seen_at = now
                new_agents.append(agent)
                self.db.add(agent)
        
        # Single commit for all operations
        await self.db.commit()
        
        # Refresh all agents
        all_agents = updated_agents + new_agents
        for agent in all_agents:
            await self.db.refresh(agent)
        
        return all_agents
    
    async def mark_disconnected(self, instance_ids_to_keep: List[str]) -> int:
        """Mark agents as disconnected if they're not in the provided list.
        Also marks them as unhealthy since a disconnected agent cannot be healthy."""
        from sqlalchemy import update
        
        result = await self.db.execute(
            update(Agent)
            .where(Agent.instance_id.notin_(instance_ids_to_keep))
            .where(Agent.is_connected == True)
            .values(is_connected=False, healthy=False)
        )
        await self.db.commit()
        return result.rowcount
    
    async def get_agents_with_alerts(self) -> List[Agent]:
        """Get all agents with config alerts."""
        result = await self.db.execute(
            select(Agent)
            .where(Agent.alert_config == True)
            .order_by(desc(Agent.updated_at))
        )
        return list(result.scalars().all())
    
    async def get_statistics(self) -> dict:
        """Get agent statistics."""
        # Total agents
        total = await self.db.execute(select(func.count(Agent.id)))
        total_agents = total.scalar_one()
        
        # Connected agents
        connected = await self.db.execute(
            select(func.count(Agent.id)).where(Agent.is_connected == True)
        )
        connected_agents = connected.scalar_one()
        
        # Healthy agents
        healthy = await self.db.execute(
            select(func.count(Agent.id)).where(Agent.healthy == True)
        )
        healthy_agents = healthy.scalar_one()
        
        # OS distribution
        os_dist = await self.db.execute(
            select(Agent.os_type, func.count(Agent.id))
            .group_by(Agent.os_type)
        )
        os_distribution = {row[0] or "unknown": row[1] for row in os_dist.all()}
        
        return {
            "total_agents": total_agents,
            "connected_agents": connected_agents,
            "disconnected_agents": total_agents - connected_agents,
            "healthy_agents": healthy_agents,
            "unhealthy_agents": total_agents - healthy_agents,
            "os_distribution": os_distribution
        }
    
    async def delete(self, agent: Agent) -> None:
        """Delete an agent."""
        await self.db.delete(agent)
        await self.db.commit()
    
    async def delete_with_history(self, instance_id: str) -> bool:
        """Delete an agent and all its associated history.
        
        This will cascade delete:
        - All health records (agent_health)
        - All config versions (agent_configs)
        - All pipeline health records (agent_pipeline_health)
        
        Args:
            instance_id: Agent instance ID
            
        Returns:
            True if agent was found and deleted, False if not found
        """
        agent = await self.get_by_instance_id(instance_id)
        
        if not agent:
            return False
        
        # Delete agent - cascades to all related records
        await self.db.delete(agent)
        await self.db.commit()
        
        return True
    
    async def _update_related_instance_ids(self, old_instance_id: str, new_instance_id: str) -> None:
        """Update instance_id in all related tables.
        
        When hostname-based sync detects an instance_id change, this method
        updates all related records to use the new instance_id.
        
        Uses SET CONSTRAINTS to defer foreign key checks until commit.
        
        Updates:
        - agent_health.instance_id
        - agent_configs.instance_id
        - agent_pipeline_health.instance_id
        
        Args:
            old_instance_id: Previous instance_id
            new_instance_id: New instance_id
        """
        from sqlalchemy import text
        
        # Defer foreign key constraint checks
        await self.db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        
        # Update agent_health
        result = await self.db.execute(
            update(AgentHealth)
            .where(AgentHealth.instance_id == old_instance_id)
            .values(instance_id=new_instance_id)
        )
        health_updated = result.rowcount
        
        # Update agent_configs
        result = await self.db.execute(
            update(AgentConfig)
            .where(AgentConfig.instance_id == old_instance_id)
            .values(instance_id=new_instance_id)
        )
        config_updated = result.rowcount
        
        # Update agent_pipeline_health
        result = await self.db.execute(
            update(AgentPipelineHealth)
            .where(AgentPipelineHealth.instance_id == old_instance_id)
            .values(instance_id=new_instance_id)
        )
        pipeline_updated = result.rowcount
        
        logger.info(
            f"Updated instance_id from '{old_instance_id}' to '{new_instance_id}': "
            f"health={health_updated}, configs={config_updated}, pipeline={pipeline_updated}"
        )
