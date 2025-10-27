"""SQLAlchemy database models."""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, DateTime, Text, JSON, Boolean,
    ForeignKey, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Job type enumeration."""
    CONFIG_UPDATE = "config_update"
    BULK_CONFIG_UPDATE = "bulk_config_update"


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    VIEWER = "viewer"


class Agent(Base):
    """Agent model representing OpAMP agents."""
    
    __tablename__ = "agents"
    
    id = Column(String(255), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    env = Column(String(100), nullable=True, index=True)
    os = Column(String(100), nullable=True)
    arch = Column(String(100), nullable=True)
    version = Column(String(100), nullable=True)
    
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_status = Column(String(50), default="unknown")
    last_config_version = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    status_snapshots = relationship("AgentStatusSnapshot", back_populates="agent", cascade="all, delete-orphan")
    configs = relationship("Config", back_populates="agent", cascade="all, delete-orphan")
    job_runs = relationship("JobRun", back_populates="agent", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_agent_env_status", "env", "last_status"),
        Index("idx_agent_last_seen", "last_seen"),
    )


class AgentStatusSnapshot(Base):
    """Agent status snapshot for historical tracking."""
    
    __tablename__ = "agent_status_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(255), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    status_metadata = Column("metadata", JSON, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="status_snapshots")
    
    # Indexes
    __table_args__ = (
        Index("idx_status_agent_timestamp", "agent_id", "timestamp"),
        Index("idx_status_timestamp", "timestamp"),
    )


class Config(Base):
    """Configuration version tracking."""
    
    __tablename__ = "configs"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(255), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    config_yaml = Column(Text, nullable=False)
    applied_by = Column(String(255), nullable=False)
    checksum = Column(String(64), nullable=False)  # SHA256 hash
    
    # Relationships
    agent = relationship("Agent", back_populates="configs")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("agent_id", "version", name="uq_agent_config_version"),
        Index("idx_config_agent_timestamp", "agent_id", "timestamp"),
        Index("idx_config_checksum", "checksum"),
    )


class Job(Base):
    """Background job tracking."""
    
    __tablename__ = "jobs"
    
    id = Column(String(36), primary_key=True, index=True)  # UUID
    type = Column(String(50), nullable=False)
    payload_json = Column(JSON, nullable=False)
    status = Column(String(20), default=JobStatus.PENDING, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(255), nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    total_agents = Column(Integer, default=0, nullable=False)
    successful_agents = Column(Integer, default=0, nullable=False)
    failed_agents = Column(Integer, default=0, nullable=False)
    
    error_message = Column(Text, nullable=True)
    
    # Relationships
    job_runs = relationship("JobRun", back_populates="job", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="chk_job_progress"),
        Index("idx_job_status_created", "status", "created_at"),
        Index("idx_job_created_by", "created_by"),
    )


class JobRun(Base):
    """Individual job run per agent."""
    
    __tablename__ = "job_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String(255), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    
    status = Column(String(20), default=JobStatus.PENDING, nullable=False)
    attempt = Column(Integer, default=1, nullable=False)
    
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    job = relationship("Job", back_populates="job_runs")
    agent = relationship("Agent", back_populates="job_runs")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("job_id", "agent_id", name="uq_job_agent"),
        Index("idx_jobrun_job_status", "job_id", "status"),
        Index("idx_jobrun_agent", "agent_id"),
    )


class User(Base):
    """Application users."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.VIEWER, nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class AuditLog(Base):
    """Audit log for tracking user actions."""
    
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    actor = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=True)  # agent, config, job
    target_id = Column(String(255), nullable=True)
    details_json = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    # Indexes
    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_actor", "actor"),
        Index("idx_audit_target", "target_type", "target_id"),
    )