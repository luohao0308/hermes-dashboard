"""Configuration settings for Hermès Bridge Service"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    # SSE settings
    heartbeat_interval: int = 30  # seconds
    max_connections: int = 1000
    
    # Event generation
    event_generation_interval: int = 1  # seconds
    
    # CORS settings
    cors_origins: list = ["http://localhost:5173", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
