"""Initial migration - create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2025-11-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('login', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_login'), 'users', ['login'], unique=True)

    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('instance_id', sa.String(length=255), nullable=False),
        sa.Column('host_name', sa.String(length=255), nullable=True),
        sa.Column('os_type', sa.String(length=100), nullable=True),
        sa.Column('os_description', sa.String(length=500), nullable=True),
        sa.Column('healthy', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status_sync', sa.String(length=50), nullable=False, server_default='UNKNOWN'),
        sa.Column('alert_config', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_connected', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agents_instance_id'), 'agents', ['instance_id'], unique=True)
    op.create_index('idx_agent_status', 'agents', ['status_sync', 'is_connected'])
    op.create_index('idx_agent_alert', 'agents', ['alert_config'])

    # Create agent_health table
    op.create_table(
        'agent_health',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('instance_id', sa.String(length=255), nullable=False),
        sa.Column('healthy', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status', sa.String(length=100), nullable=False),
        sa.Column('status_time_unix_nano', sa.BigInteger(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('component_health_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['agents.instance_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_health_instance_id'), 'agent_health', ['instance_id'])
    op.create_index('idx_health_instance_created', 'agent_health', ['instance_id', 'created_at'])

    # Create agent_configs table
    op.create_table(
        'agent_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('instance_id', sa.String(length=255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('effective_config', sa.Text(), nullable=False),
        sa.Column('config_hash', sa.String(length=64), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='SYNC_JOB'),
        sa.Column('updated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['agents.instance_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_configs_instance_id'), 'agent_configs', ['instance_id'])
    op.create_index('idx_config_instance_version', 'agent_configs', ['instance_id', 'version'])
    op.create_index('idx_config_hash', 'agent_configs', ['config_hash'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('idx_config_hash', table_name='agent_configs')
    op.drop_index('idx_config_instance_version', table_name='agent_configs')
    op.drop_index(op.f('ix_agent_configs_instance_id'), table_name='agent_configs')
    op.drop_table('agent_configs')

    op.drop_index('idx_health_instance_created', table_name='agent_health')
    op.drop_index(op.f('ix_agent_health_instance_id'), table_name='agent_health')
    op.drop_table('agent_health')

    op.drop_index('idx_agent_alert', table_name='agents')
    op.drop_index('idx_agent_status', table_name='agents')
    op.drop_index(op.f('ix_agents_instance_id'), table_name='agents')
    op.drop_table('agents')

    op.drop_index(op.f('ix_users_login'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
