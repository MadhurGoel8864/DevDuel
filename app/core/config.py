# app/core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = Field(default="GoPool")
    debug: bool = Field(default=False)
    env: str = Field(default="development")

    # CORS
    allowed_origins: str = Field(default="http://localhost:3000")

    @property
    def cors_origins(self) -> list[str]:
        """Parse pipe-separated origins from env: 'http://a.com|http://b.com'"""
        return [o.strip() for o in self.allowed_origins.split("|") if o.strip()]

    # Security
    secret_key: str
    access_token_expire_minutes: int = 30

    # JWT Configuration
    jwt_secret_key: str | None = Field(
        default=None
    )  # Falls back to secret_key if not set
    jwt_algorithm: str = Field(default="HS256")

    @property
    def effective_jwt_secret(self) -> str:
        """Return jwt_secret_key if set, otherwise fall back to secret_key."""
        return self.jwt_secret_key or self.secret_key

    # Timezone
    timezone: str = Field(default="Asia/Kolkata")

    # Database
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    OTP_EXPIRE_SECONDS: int = 300  # 5 minutes

    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # SMTP Email Configuration (Optional - required only if using email service)
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    email_from: str = Field(default="")

    # Google OAuth creds
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # ── Team Invite Settings ───────────────────────────────────────────────────
    INVITE_EXPIRE_SECONDS: int = 72 * 3600  # 72 hours — main invite TTL
    PENDING_JOIN_EXPIRE_SECONDS: int = 24 * 3600  # 24 hours — waiting for OTP verify

    # Frontend URLs embedded in invite emails
    FRONTEND_ACCEPT_INVITE_URL: str = "http://localhost:3000/invite/accept"
    FRONTEND_DECLINE_INVITE_URL: str = "http://localhost:3000/invite/decline"
    FRONTEND_REGISTER_INVITE_URL: str = "http://localhost:3000/register"

    class Config:
        env_file = ".env"


settings = Settings()
