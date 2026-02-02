"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Funnel Analysis API
    funnel_api_base_url: str = "http://localhost:8080/api"
    funnel_api_timeout: int = 30

    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4o"

    # Database
    database_path: str = "./data/sessions.db"

    # Session Management
    session_ttl_hours: int = 24

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
