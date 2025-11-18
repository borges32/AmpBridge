"""
Repository layer for AgentHealth database operations.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.models import AgentHealth
from app.schemas import AgentHealthCreate


class AgentHealthRepository:
    """Repository for AgentHealth database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, health_data: AgentHealthCreate) -> AgentHealth:
        """Create a new health record."""
        health = AgentHealth(**health_data.model_dump())
        
        self.db.add(health)
        await self.db.commit()
        await self.db.refresh(health)
        return health
    
    async def get_latest_by_instance_id(self, instance_id: str) -> Optional[AgentHealth]:
        """Get the latest health record for an agent."""
        result = await self.db.execute(
            select(AgentHealth)
            .where(AgentHealth.instance_id == instance_id)
            .order_by(desc(AgentHealth.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_history_by_instance_id(
        self, 
        instance_id: str, 
        limit: int = 100
    ) -> List[AgentHealth]:
        """Get health history for an agent."""
        result = await self.db.execute(
            select(AgentHealth)
            .where(AgentHealth.instance_id == instance_id)
            .order_by(desc(AgentHealth.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
