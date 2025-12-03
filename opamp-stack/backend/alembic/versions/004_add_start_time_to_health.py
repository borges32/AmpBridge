"""add start_time_unix_nano to agent_health

Revision ID: 004
Revises: 003
Create Date: 2025-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_add_start_time_to_health'
down_revision: Union[str, None] = '003_cleanup_old_health_records'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add start_time_unix_nano field to agent_health table."""
    op.add_column('agent_health', sa.Column('start_time_unix_nano', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    """Remove start_time_unix_nano field from agent_health table."""
    op.drop_column('agent_health', 'start_time_unix_nano')
