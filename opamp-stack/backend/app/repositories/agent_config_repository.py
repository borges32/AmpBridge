"""
Repository layer for AgentConfig database operations.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.models.models import AgentConfig
from app.schemas import AgentConfigCreate


class AgentConfigRepository:
    """Repository for AgentConfig database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, config_data: AgentConfigCreate) -> AgentConfig:
        """Create a new config version."""
        config = AgentConfig(**config_data.model_dump())
        
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config
    
    async def get_latest_by_instance_id(self, instance_id: str) -> Optional[AgentConfig]:
        """Get the latest config version for an agent."""
        result = await self.db.execute(
            select(AgentConfig)
            .where(AgentConfig.instance_id == instance_id)
            .order_by(desc(AgentConfig.version))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_next_version(self, instance_id: str) -> int:
        """Get the next version number for an agent's config."""
        result = await self.db.execute(
            select(func.max(AgentConfig.version))
            .where(AgentConfig.instance_id == instance_id)
        )
        max_version = result.scalar_one_or_none()
        return (max_version or 0) + 1
    
    async def get_history_by_instance_id(
        self, 
        instance_id: str, 
        limit: int = 100
    ) -> List[AgentConfig]:
        """Get config version history for an agent."""
        result = await self.db.execute(
            select(AgentConfig)
            .where(AgentConfig.instance_id == instance_id)
            .order_by(desc(AgentConfig.version))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_version(self, instance_id: str, version: int) -> Optional[AgentConfig]:
        """Get a specific config version."""
        result = await self.db.execute(
            select(AgentConfig)
            .where(AgentConfig.instance_id == instance_id)
            .where(AgentConfig.version == version)
        )
        return result.scalar_one_or_none()
