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
    
    async def mark_disconnected(self, instance_ids_to_keep: List[str]) -> int:
        """Mark agents as disconnected if they're not in the provided list."""
        from sqlalchemy import update
        
        result = await self.db.execute(
            update(Agent)
            .where(Agent.instance_id.notin_(instance_ids_to_keep))
            .where(Agent.is_connected == True)
            .values(is_connected=False)
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
