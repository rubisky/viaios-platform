"""Configuration for Knowledge Service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Knowledge service settings loaded from environment variables."""

    app_name: str = "viaios-knowledge-service"
    app_version: str = "0.1.0"

    host: str = "0.0.0.0"
    port: int = 8093

    postgres_url: str = "postgresql://user:password@localhost:5432/viaios"
    milvus_uri: str = "http://localhost:19530"
    neo4j_uri: str = "bolt://localhost:7687"
    llm_provider: str = "openai"

    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
