"""
Repository layer for AgentPipelineHealth database operations.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete

from app.models.models import AgentPipelineHealth
from app.schemas import AgentPipelineHealthCreate


class AgentPipelineHealthRepository:
    """Repository for AgentPipelineHealth database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, health_data: AgentPipelineHealthCreate) -> AgentPipelineHealth:
        """Create a new pipeline health record."""
        health = AgentPipelineHealth(**health_data.model_dump())

        self.db.add(health)
        await self.db.commit()
        await self.db.refresh(health)
        return health

    async def get_latest_by_instance_and_component(
        self,
        instance_id: str,
        component_name: str
    ) -> Optional[AgentPipelineHealth]:
        """Get the latest health record for a specific component of an agent."""
        result = await self.db.execute(
            select(AgentPipelineHealth)
            .where(
                AgentPipelineHealth.instance_id == instance_id,
                AgentPipelineHealth.component_name == component_name
            )
            .order_by(desc(AgentPipelineHealth.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history_by_instance_id(
        self,
        instance_id: str,
        limit: int = 100
    ) -> List[AgentPipelineHealth]:
        """Get pipeline health history for an agent (all pipelines)."""
        result = await self.db.execute(
            select(AgentPipelineHealth)
            .where(AgentPipelineHealth.instance_id == instance_id)
            .order_by(desc(AgentPipelineHealth.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_all_by_instance_id(self, instance_id: str) -> int:
        """
        Delete all pipeline health records for an agent.
        Used to clear old data before inserting new sync data.

        Args:
            instance_id: Agent instance ID

        Returns:
            Number of records deleted
        """
        delete_result = await self.db.execute(
            delete(AgentPipelineHealth)
            .where(AgentPipelineHealth.instance_id == instance_id)
        )

        await self.db.commit()
        return delete_result.rowcount

    async def get_history_by_component(
        self,
        instance_id: str,
        component_name: str,
        limit: int = 100
    ) -> List[AgentPipelineHealth]:
        """Get health history for a specific component of an agent."""
        result = await self.db.execute(
            select(AgentPipelineHealth)
            .where(
                AgentPipelineHealth.instance_id == instance_id,
                AgentPipelineHealth.component_name == component_name
            )
            .order_by(desc(AgentPipelineHealth.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def cleanup_old_records(
        self,
        instance_id: str,
        component_name: str,
        keep_last: int = 5
    ) -> int:
        """
        Delete old component health records, keeping only the last N records.

        Args:
            instance_id: Agent instance ID
            component_name: Component name
            keep_last: Number of records to keep (default: 5)

        Returns:
            Number of records deleted
        """
        # Get IDs of records to keep
        result = await self.db.execute(
            select(AgentPipelineHealth.id)
            .where(
                AgentPipelineHealth.instance_id == instance_id,
                AgentPipelineHealth.component_name == component_name
            )
            .order_by(desc(AgentPipelineHealth.created_at))
            .limit(keep_last)
        )
        ids_to_keep = [row[0] for row in result.all()]

        if not ids_to_keep:
            return 0

        # Delete records not in the keep list
        delete_result = await self.db.execute(
            delete(AgentPipelineHealth)
            .where(
                AgentPipelineHealth.instance_id == instance_id,
                AgentPipelineHealth.component_name == component_name,
                AgentPipelineHealth.id.not_in(ids_to_keep)
            )
        )

        await self.db.commit()
        return delete_result.rowcount

    async def bulk_create(self, health_data_list: List[AgentPipelineHealthCreate]) -> List[AgentPipelineHealth]:
        """Bulk create pipeline health records.

        Does NOT commit — caller (service layer) is responsible for committing
        the transaction to ensure atomicity across multiple bulk operations.

        Args:
            health_data_list: List of pipeline health data to create

        Returns:
            List of created AgentPipelineHealth objects
        """
        if not health_data_list:
            return []

        health_records = [
            AgentPipelineHealth(**health_data.model_dump())
            for health_data in health_data_list
        ]

        self.db.add_all(health_records)
        await self.db.flush()

        return health_records

    async def bulk_delete_by_instance_ids(self, instance_ids: List[str]) -> int:
        """Delete all pipeline health records for multiple agents.

        Does NOT commit — caller (service layer) is responsible for committing.

        Args:
            instance_ids: List of agent instance IDs

        Returns:
            Number of records deleted
        """
        if not instance_ids:
            return 0

        delete_result = await self.db.execute(
            delete(AgentPipelineHealth)
            .where(AgentPipelineHealth.instance_id.in_(instance_ids))
        )

        return delete_result.rowcount

    async def bulk_upsert(self, health_data_list: List[AgentPipelineHealthCreate]) -> int:
        """Bulk upsert pipeline health records using DELETE+INSERT within a single transaction.

        Replaces all pipeline health for the affected instance_ids with the new data.
        More efficient than separate bulk_delete + bulk_create because it avoids
        an intermediate commit and reduces round-trips.

        Does NOT commit — caller is responsible.

        Args:
            health_data_list: List of pipeline health data

        Returns:
            Number of records inserted
        """
        if not health_data_list:
            return 0

        # Collect unique instance_ids from the data
        instance_ids = list({h.instance_id for h in health_data_list})

        # Delete existing records for those instances
        await self.db.execute(
            delete(AgentPipelineHealth)
            .where(AgentPipelineHealth.instance_id.in_(instance_ids))
        )

        # Insert new records
        health_records = [
            AgentPipelineHealth(**health_data.model_dump())
            for health_data in health_data_list
        ]
        self.db.add_all(health_records)
        await self.db.flush()

        return len(health_records)
