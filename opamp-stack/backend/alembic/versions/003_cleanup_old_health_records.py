"""cleanup old health records - keep last 5

Revision ID: 003
Revises: 002
Create Date: 2025-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_cleanup_old_health_records'
down_revision: Union[str, None] = '002_add_pipeline_health'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Clean up old agent_health records, keeping only the last 5 records per agent.
    This migration runs a SQL query that:
    1. Identifies records to keep (last 5 per instance_id)
    2. Deletes all other records
    """
    # Use raw SQL to delete old records efficiently
    # This query keeps only the last 5 records per agent based on created_at
    op.execute("""
        DELETE FROM agent_health
        WHERE id NOT IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY instance_id 
                           ORDER BY created_at DESC
                       ) AS row_num
                FROM agent_health
            ) AS ranked
            WHERE row_num <= 5
        )
    """)


def downgrade() -> None:
    """
    Downgrade is not applicable for this migration as we cannot 
    restore deleted historical data.
    """
    pass
