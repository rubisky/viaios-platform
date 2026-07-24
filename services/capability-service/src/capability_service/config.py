"""Configuration for Capability Service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Capability service settings loaded from environment variables."""

    app_name: str = "viaios-capability-service"
    app_version: str = "0.1.0"

    host: str = "0.0.0.0"
    port: int = 8092

    database_url: str = "postgresql://user:password@localhost:5432/viaios"
    milvus_uri: str = "http://localhost:19530"
    model_registry_url: str = "http://localhost:8085"

    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
