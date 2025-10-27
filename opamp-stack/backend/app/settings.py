"""Application settings configuration using Pydantic."""

import os
from typing import Optional, List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_env: str = Field(default="dev", description="Application environment")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Database
    db_url: str = Field(
        default="sqlite:///data/app.db",
        description="Database URL"
    )
    
    # Authentication
    admin_user: str = Field(default="admin", description="Bootstrap admin username")
    admin_pass: str = Field(default="admin123", description="Bootstrap admin password")
    jwt_secret: str = Field(
        default="your-super-secret-jwt-key-change-in-production",
        description="JWT secret key"
    )
    jwt_expires_min: int = Field(default=1440, description="JWT expiration in minutes")
    
    # OpAMP Server
    opamp_base_url: str = Field(
        default="http://opamp-server:4321",
        description="OpAMP server base URL"
    )
    opamp_timeout: int = Field(default=30, description="OpAMP client timeout in seconds")
    opamp_retry_attempts: int = Field(default=3, description="Number of retry attempts")
    
    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Allowed CORS origins (comma-separated)"
    )
    
    # Rate Limiting
    rate_limit_per_min: int = Field(default=100, description="Rate limit per minute per IP")
    
    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    
    # OpenTelemetry
    otlp_endpoint: Optional[str] = Field(default=None, description="OTLP endpoint URL")
    otlp_headers: Optional[str] = Field(default=None, description="OTLP headers")
    
    # Job Processing
    max_concurrent_jobs: int = Field(default=50, description="Maximum concurrent jobs")
    job_timeout_seconds: int = Field(default=300, description="Job timeout in seconds")
    
    # Polling
    agent_poll_interval: int = Field(default=30, description="Agent polling interval in seconds")
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        if not self.cors_origins.strip():
            return []
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]
    
    @field_validator('debug', mode='before')
    @classmethod
    def parse_debug(cls, v):
        """Parse debug flag from environment."""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return v
    
    @field_validator('db_url')
    @classmethod
    def validate_db_url(cls, v):
        """Ensure database URL is properly formatted."""
        if v.startswith('sqlite:///') and not v.startswith('sqlite:////'):
            # Make relative paths absolute for SQLite
            if not v.startswith('sqlite:///data/') and not os.path.isabs(v.replace('sqlite:///', '')):
                return f"sqlite:///data/{v.replace('sqlite:///', '')}"
        return v
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()