"""
Database models for the OpAMP backend system.
Uses SQLAlchemy 2.0 with async support.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Text, BigInteger, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """
    User model for authentication and authorization.
    Stores user credentials and profile information.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    login: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    agent_configs: Mapped[list["AgentConfig"]] = relationship("AgentConfig", back_populates="updated_by_user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, login='{self.login}', email='{self.email}')>"


class Agent(Base):
    """
    Agent model representing OpAMP agents.
    Stores basic agent information and current status.
    """
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instance_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    host_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    os_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    os_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    service_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    service_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    host_arch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    healthy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_sync: Mapped[str] = mapped_column(String(50), default="UNKNOWN", nullable=False)  # IN_SYNC, OUT_OF_SYNC, UNKNOWN
    alert_config: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    health_records: Mapped[list["AgentHealth"]] = relationship("AgentHealth", back_populates="agent", cascade="all, delete-orphan")
    configs: Mapped[list["AgentConfig"]] = relationship("AgentConfig", back_populates="agent", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_agent_status', 'status_sync', 'is_connected'),
        Index('idx_agent_alert', 'alert_config'),
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, instance_id='{self.instance_id}', host_name='{self.host_name}')>"


class AgentHealth(Base):
    """
    Agent health model for tracking agent health status.
    Stores historical health information for each agent.
    """
    __tablename__ = "agent_health"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instance_id: Mapped[str] = mapped_column(String(255), ForeignKey("agents.instance_id", ondelete="CASCADE"), nullable=False, index=True)
    healthy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)  # StatusOK, StatusFailed, etc.
    status_time_unix_nano: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    component_health_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string if needed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="health_records")

    # Indexes
    __table_args__ = (
        Index('idx_health_instance_created', 'instance_id', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<AgentHealth(id={self.id}, instance_id='{self.instance_id}', healthy={self.healthy}, status='{self.status}')>"


class AgentConfig(Base):
    """
    Agent configuration model for versioning effective configurations.
    Stores configuration history with version tracking.
    """
    __tablename__ = "agent_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instance_id: Mapped[str] = mapped_column(String(255), ForeignKey("agents.instance_id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_config: Mapped[str] = mapped_column(Text, nullable=False)  # YAML/JSON config content
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256 hash for change detection
    source: Mapped[str] = mapped_column(String(50), default="SYNC_JOB", nullable=False)  # SYNC_JOB, MANUAL_UPDATE, API_UPDATE
    updated_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="configs")
    updated_by_user: Mapped[Optional["User"]] = relationship("User", back_populates="agent_configs")

    # Indexes
    __table_args__ = (
        Index('idx_config_instance_version', 'instance_id', 'version'),
        Index('idx_config_hash', 'config_hash'),
    )

    def __repr__(self) -> str:
        return f"<AgentConfig(id={self.id}, instance_id='{self.instance_id}', version={self.version}, source='{self.source}')>"
