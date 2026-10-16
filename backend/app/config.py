from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    database_url: str = "sqlite:///./scanner.db"
    debug: bool = False

    model_config = {"env_prefix": "", "extra": "ignore"}
