"""add pipeline health table

Revision ID: 002
Revises: 001
Create Date: 2025-11-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_pipeline_health'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_pipeline_health table
    op.create_table(
        'agent_pipeline_health',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('instance_id', sa.String(length=255), nullable=False),
        sa.Column('component_type', sa.String(length=50), nullable=False),
        sa.Column('component_name', sa.String(length=255), nullable=False),
        sa.Column('parent_pipeline', sa.String(length=255), nullable=True),
        sa.Column('healthy', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(length=100), nullable=False),
        sa.Column('status_time_unix_nano', sa.BigInteger(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['agents.instance_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_pipeline_health_instance_created', 'agent_pipeline_health', ['instance_id', 'created_at'])
    op.create_index('idx_pipeline_health_component', 'agent_pipeline_health', ['component_type', 'component_name'])
    op.create_index('idx_pipeline_health_parent', 'agent_pipeline_health', ['parent_pipeline'])
    op.create_index(op.f('ix_agent_pipeline_health_instance_id'), 'agent_pipeline_health', ['instance_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_agent_pipeline_health_instance_id'), table_name='agent_pipeline_health')
    op.drop_index('idx_pipeline_health_parent', table_name='agent_pipeline_health')
    op.drop_index('idx_pipeline_health_component', table_name='agent_pipeline_health')
    op.drop_index('idx_pipeline_health_instance_created', table_name='agent_pipeline_health')
    
    # Drop table
    op.drop_table('agent_pipeline_health')
