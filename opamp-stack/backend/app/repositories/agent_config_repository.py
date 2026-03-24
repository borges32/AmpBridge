"""
Repository layer for AgentConfig database operations.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload

from app.models.models import AgentConfig, User
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
            .options(selectinload(AgentConfig.updated_by_user))
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
            .options(selectinload(AgentConfig.updated_by_user))
            .where(AgentConfig.instance_id == instance_id)
            .order_by(desc(AgentConfig.version))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_version(self, instance_id: str, version: int) -> Optional[AgentConfig]:
        """Get a specific config version."""
        result = await self.db.execute(
            select(AgentConfig)
            .options(selectinload(AgentConfig.updated_by_user))
            .where(AgentConfig.instance_id == instance_id)
            .where(AgentConfig.version == version)
        )
        return result.scalar_one_or_none()
    
    async def bulk_create(self, config_data_list: List[AgentConfigCreate]) -> List[AgentConfig]:
        """Bulk create config records.

        Does NOT commit — caller (service layer) is responsible for committing
        the transaction to ensure atomicity across multiple bulk operations.

        Args:
            config_data_list: List of config data to create

        Returns:
            List of created AgentConfig objects
        """
        if not config_data_list:
            return []

        configs = [
            AgentConfig(**config_data.model_dump())
            for config_data in config_data_list
        ]

        self.db.add_all(configs)
        await self.db.flush()

        return configs
    
    async def get_latest_configs_bulk(self, instance_ids: List[str]) -> dict:
        """Get latest config for multiple agents in one query.
        
        Args:
            instance_ids: List of instance IDs
            
        Returns:
            Dict mapping instance_id to latest AgentConfig
        """
        if not instance_ids:
            return {}
        
        # Subquery to get max version per instance_id
        subquery = (
            select(
                AgentConfig.instance_id,
                func.max(AgentConfig.version).label('max_version')
            )
            .where(AgentConfig.instance_id.in_(instance_ids))
            .group_by(AgentConfig.instance_id)
            .subquery()
        )
        
        # Join to get full config records
        result = await self.db.execute(
            select(AgentConfig)
            .join(
                subquery,
                (AgentConfig.instance_id == subquery.c.instance_id) &
                (AgentConfig.version == subquery.c.max_version)
            )
        )
        
        configs = result.scalars().all()
        return {config.instance_id: config for config in configs}
