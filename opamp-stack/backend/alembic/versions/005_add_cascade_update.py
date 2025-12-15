"""Add ON UPDATE CASCADE to foreign keys

Revision ID: 005_add_cascade_update
Revises: 004_add_start_time_to_health
Create Date: 2025-12-15 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_add_cascade_update'
down_revision = '004_add_start_time_to_health'
branch_labels = None
depends_on = None


def upgrade():
    """Add ON UPDATE CASCADE to all foreign keys referencing agents.instance_id"""
    
    # Drop and recreate foreign keys with ON UPDATE CASCADE
    
    # agent_health
    op.drop_constraint('agent_health_instance_id_fkey', 'agent_health', type_='foreignkey')
    op.create_foreign_key(
        'agent_health_instance_id_fkey',
        'agent_health', 'agents',
        ['instance_id'], ['instance_id'],
        onupdate='CASCADE',
        ondelete='CASCADE'
    )
    
    # agent_configs
    op.drop_constraint('agent_configs_instance_id_fkey', 'agent_configs', type_='foreignkey')
    op.create_foreign_key(
        'agent_configs_instance_id_fkey',
        'agent_configs', 'agents',
        ['instance_id'], ['instance_id'],
        onupdate='CASCADE',
        ondelete='CASCADE'
    )
    
    # agent_pipeline_health
    op.drop_constraint('agent_pipeline_health_instance_id_fkey', 'agent_pipeline_health', type_='foreignkey')
    op.create_foreign_key(
        'agent_pipeline_health_instance_id_fkey',
        'agent_pipeline_health', 'agents',
        ['instance_id'], ['instance_id'],
        onupdate='CASCADE',
        ondelete='CASCADE'
    )


def downgrade():
    """Revert foreign keys to original state (without ON UPDATE CASCADE)"""
    
    # agent_health
    op.drop_constraint('agent_health_instance_id_fkey', 'agent_health', type_='foreignkey')
    op.create_foreign_key(
        'agent_health_instance_id_fkey',
        'agent_health', 'agents',
        ['instance_id'], ['instance_id'],
        ondelete='CASCADE'
    )
    
    # agent_configs
    op.drop_constraint('agent_configs_instance_id_fkey', 'agent_configs', type_='foreignkey')
    op.create_foreign_key(
        'agent_configs_instance_id_fkey',
        'agent_configs', 'agents',
        ['instance_id'], ['instance_id'],
        ondelete='CASCADE'
    )
    
    # agent_pipeline_health
    op.drop_constraint('agent_pipeline_health_instance_id_fkey', 'agent_pipeline_health', type_='foreignkey')
    op.create_foreign_key(
        'agent_pipeline_health_instance_id_fkey',
        'agent_pipeline_health', 'agents',
        ['instance_id'], ['instance_id'],
        ondelete='CASCADE'
    )
