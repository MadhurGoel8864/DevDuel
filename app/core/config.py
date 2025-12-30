# app/core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = Field(default="GoPool")
    debug: bool = Field(default=False)
    env: str = Field(default="development")

    # Security
    secret_key: str
    access_token_expire_minutes: int = 30

    # Timezone
    timezone: str = Field(default="Asia/Kolkata")

    # Database
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
