"""Configuration settings for AI Workflow Control Plane."""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Environment: production, development, test
    environment: str = "development"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # Database settings
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ai_workflow"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # SSE settings
    heartbeat_interval: int = 30  # seconds
    max_connections: int = 1000

    # Worker heartbeat monitoring
    scheduler_heartbeat_path: str = "/tmp/hermes_scheduler_worker_heartbeat"
    retention_heartbeat_path: str = "/tmp/hermes_retention_worker_heartbeat"
    worker_heartbeat_stale_seconds: int = 120

    # Event generation
    event_generation_interval: int = 1  # seconds

    # Security
    encryption_key: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    service_tokens: str = ""  # comma-separated valid tokens for service accounts

    # CORS settings
    cors_origins: list = ["http://localhost:5173", "http://localhost:5174", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
