"""
Repository layer for AgentHealth database operations.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete

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
    
    async def cleanup_old_records(self, instance_id: str, keep_last: int = 10) -> int:
        """
        Delete old health records, keeping only the last N records for an agent.
        
        Args:
            instance_id: Agent instance ID
            keep_last: Number of records to keep (default: 10)
            
        Returns:
            Number of records deleted
        """
        # Get IDs of records to keep
        result = await self.db.execute(
            select(AgentHealth.id)
            .where(AgentHealth.instance_id == instance_id)
            .order_by(desc(AgentHealth.created_at))
            .limit(keep_last)
        )
        ids_to_keep = [row[0] for row in result.all()]
        
        if not ids_to_keep:
            return 0
        
        # Delete records not in the keep list
        delete_result = await self.db.execute(
            delete(AgentHealth)
            .where(
                AgentHealth.instance_id == instance_id,
                AgentHealth.id.not_in(ids_to_keep)
            )
        )
        
        await self.db.commit()
        return delete_result.rowcount
