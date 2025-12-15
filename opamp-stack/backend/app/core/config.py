"""
Application configuration using Pydantic Settings.
Loads configuration from environment variables.
"""
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str
    
    # OpAMP Server
    OPAMP_SERVER_URL: str
    OPAMP_SYNC_INTERVAL_SECONDS: int = 60
    
    # Performance Settings
    OPAMP_SYNC_BATCH_SIZE: int = 100  # Number of agents to process in parallel
    OPAMP_SYNC_MAX_WORKERS: int = 10   # Max concurrent batches
    OPAMP_DB_BULK_SIZE: int = 500      # Bulk insert/update size
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "OpAMP Backend API"
    DEBUG: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_SYNC_OPERATIONS: bool = True  # Enable/disable sync operation logs
    LOG_HTTP_REQUESTS: bool = False  # Enable/disable HTTP request logs (httpx)
    
    # Agent Sync Strategy
    USE_HOSTNAME_AS_SYNC_KEY: bool = False  # Use host_name instead of instance_id for agent identification
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
