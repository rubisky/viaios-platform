"""Configuration for Agent Service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Agent service settings loaded from environment variables."""

    app_name: str = "viaios-agent-service"
    app_version: str = "0.1.0"

    host: str = "0.0.0.0"
    port: int = 8091

    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/viaios"
    kafka_bootstrap_servers: str = "localhost:9092"
    redis_url: str = "redis://localhost:6379/0"
    llm_provider: str = "openai"

    llm_api_key: str = ""
    llm_model: str = "gpt-4o"

    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
