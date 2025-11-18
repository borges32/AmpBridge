"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ===== User Schemas =====
class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    login: str = Field(..., min_length=3, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Agent Schemas =====
class AgentBase(BaseModel):
    instance_id: str
    host_name: Optional[str] = None
    os_type: Optional[str] = None
    os_description: Optional[str] = None


class AgentCreate(AgentBase):
    healthy: bool = False
    status_sync: str = "UNKNOWN"
    alert_config: bool = False


class AgentUpdate(BaseModel):
    host_name: Optional[str] = None
    os_type: Optional[str] = None
    os_description: Optional[str] = None
    healthy: Optional[bool] = None
    status_sync: Optional[str] = None
    alert_config: Optional[bool] = None
    is_connected: Optional[bool] = None


class AgentResponse(AgentBase):
    id: int
    healthy: bool
    status_sync: str
    alert_config: bool
    is_connected: bool
    started_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    agents: list[AgentResponse]


# ===== Agent Health Schemas =====
class AgentHealthBase(BaseModel):
    instance_id: str
    healthy: bool
    status: str


class AgentHealthCreate(AgentHealthBase):
    status_time_unix_nano: Optional[int] = None
    last_error: Optional[str] = None
    component_health_summary: Optional[str] = None


class AgentHealthResponse(AgentHealthBase):
    id: int
    status_time_unix_nano: Optional[int] = None
    last_error: Optional[str] = None
    component_health_summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Agent Config Schemas =====
class AgentConfigBase(BaseModel):
    instance_id: str
    effective_config: str


class AgentConfigCreate(AgentConfigBase):
    version: int
    config_hash: str
    source: str = "SYNC_JOB"
    updated_by_user_id: Optional[int] = None


class AgentConfigUpdate(BaseModel):
    effective_config: str
    instance_id: str
    updated_by_user_id: Optional[int] = None


class AgentConfigResponse(AgentConfigBase):
    id: int
    version: int
    config_hash: str
    source: str
    updated_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Authentication Schemas =====
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    login: Optional[str] = None


class LoginRequest(BaseModel):
    login: str
    password: str


# ===== OpAMP Sync Schemas =====
class OpAMPAgentData(BaseModel):
    """Schema for agent data received from OpAMP server."""
    instanceId: str
    status: dict
    effectiveConfig: Optional[str] = None
    startedAt: Optional[str] = None


class SyncResponse(BaseModel):
    success: bool
    message: str
    agents_processed: int
    agents_updated: int
    configs_versioned: int
    errors: list[str] = []


# ===== Config Update Schemas =====
class ConfigUpdateRequest(BaseModel):
    config: str = Field(..., description="YAML configuration content")


class ConfigUpdateResponse(BaseModel):
    success: bool
    message: str
    instance_id: str
    version: int
    status_ready: bool = False
