"""Configuration management using pydantic-settings."""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Server configuration."""

    # App
    app_name: str = "Sniffly Server"
    debug: bool = False

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017/sniffly"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    jwt_secret: str = Field(default="dev-secret-key")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # Admin
    admin_username: str = "admin"
    admin_password: str = "admin"

    # CORS
    cors_origins: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
