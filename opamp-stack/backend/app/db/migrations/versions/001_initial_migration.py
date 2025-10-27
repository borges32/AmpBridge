"""Initial migration - create all tables

Revision ID: 001_initial_migration
Revises: 
Create Date: 2024-10-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001_initial_migration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create agents table
    op.create_table('agents',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('env', sa.String(length=100), nullable=True),
        sa.Column('os', sa.String(length=100), nullable=True),
        sa.Column('arch', sa.String(length=100), nullable=True),
        sa.Column('version', sa.String(length=100), nullable=True),
        sa.Column('first_seen', sa.DateTime(), nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=False),
        sa.Column('last_status', sa.String(length=50), nullable=True),
        sa.Column('last_config_version', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agents_id'), 'agents', ['id'], unique=False)
    op.create_index('idx_agent_env_status', 'agents', ['env', 'last_status'], unique=False)
    op.create_index('idx_agent_last_seen', 'agents', ['last_seen'], unique=False)

    # Create jobs table
    op.create_table('jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=False),
        sa.Column('total_agents', sa.Integer(), nullable=False),
        sa.Column('successful_agents', sa.Integer(), nullable=False),
        sa.Column('failed_agents', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.CheckConstraint('progress >= 0 AND progress <= 100', name='chk_job_progress'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_id'), 'jobs', ['id'], unique=False)
    op.create_index('idx_job_status_created', 'jobs', ['status', 'created_at'], unique=False)
    op.create_index('idx_job_created_by', 'jobs', ['created_by'], unique=False)

    # Create agent_status_snapshots table
    op.create_table('agent_status_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(length=255), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_status_snapshots_id'), 'agent_status_snapshots', ['id'], unique=False)
    op.create_index('idx_status_agent_timestamp', 'agent_status_snapshots', ['agent_id', 'timestamp'], unique=False)
    op.create_index('idx_status_timestamp', 'agent_status_snapshots', ['timestamp'], unique=False)

    # Create configs table
    op.create_table('configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=100), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('config_yaml', sa.Text(), nullable=False),
        sa.Column('applied_by', sa.String(length=255), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id', 'version', name='uq_agent_config_version')
    )
    op.create_index(op.f('ix_configs_id'), 'configs', ['id'], unique=False)
    op.create_index('idx_config_agent_timestamp', 'configs', ['agent_id', 'timestamp'], unique=False)
    op.create_index('idx_config_checksum', 'configs', ['checksum'], unique=False)

    # Create job_runs table
    op.create_table('job_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('agent_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('attempt', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id', 'agent_id', name='uq_job_agent')
    )
    op.create_index(op.f('ix_job_runs_id'), 'job_runs', ['id'], unique=False)
    op.create_index('idx_jobrun_job_status', 'job_runs', ['job_id', 'status'], unique=False)
    op.create_index('idx_jobrun_agent', 'job_runs', ['agent_id'], unique=False)

    # Create audit_log table
    op.create_table('audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('actor', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=True),
        sa.Column('target_id', sa.String(length=255), nullable=True),
        sa.Column('details_json', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_id'), 'audit_log', ['id'], unique=False)
    op.create_index('idx_audit_timestamp', 'audit_log', ['timestamp'], unique=False)
    op.create_index('idx_audit_actor', 'audit_log', ['actor'], unique=False)
    op.create_index('idx_audit_target', 'audit_log', ['target_type', 'target_id'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('job_runs')
    op.drop_table('configs')
    op.drop_table('agent_status_snapshots')
    op.drop_table('jobs')
    op.drop_table('agents')
    op.drop_table('users')