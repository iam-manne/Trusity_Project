from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "order-processing-service"
    environment: str = "development"
    database_url: str | None = None
    db_host: str | None = None
    db_port: int = 5432
    db_name: str = "orders"
    db_username: str | None = None
    db_password: str | None = None
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=5, ge=0, le=50)
    recent_orders_limit: int = Field(default=100, ge=1, le=500)

    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if not all((self.db_host, self.db_username, self.db_password)):
            return "sqlite:///./orders.db"
        username = quote_plus(self.db_username or "")
        password = quote_plus(self.db_password or "")
        return (
            f"postgresql+psycopg://{username}:{password}@{self.db_host}:"
            f"{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
