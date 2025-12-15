"""
Repository layer for Agent database operations.
Provides CRUD operations for Agent model.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import selectinload

from app.models.models import Agent, AgentHealth, AgentConfig
from app.schemas import AgentCreate, AgentUpdate


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
    
    async def bulk_upsert(self, agents_data: List[dict]) -> List[Agent]:
        """Bulk create or update agents.
        
        Optimized for performance with large batches:
        - Single query to fetch existing agents
        - Batch updates and inserts
        - Single commit
        
        Args:
            agents_data: List of agent data dicts with instance_id
            
        Returns:
            List of created/updated Agent objects
        """
        if not agents_data:
            return []
        
        # Extract instance_ids
        instance_ids = [data['instance_id'] for data in agents_data]
        
        # Fetch existing agents in one query
        result = await self.db.execute(
            select(Agent).where(Agent.instance_id.in_(instance_ids))
        )
        existing_agents = {agent.instance_id: agent for agent in result.scalars().all()}
        
        updated_agents = []
        new_agents = []
        now = datetime.utcnow()
        
        # Separate updates and inserts
        for data in agents_data:
            instance_id = data['instance_id']
            
            if instance_id in existing_agents:
                # Update existing
                agent = existing_agents[instance_id]
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
