# app/core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = Field(default="DevDual")
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

    # Database - use DB_URL (e.g. postgresql+asyncpg://user:password@host:port/dbname)
    DB_URL: str

    @property
    def database_url(self) -> str:
        """Alias for DB_URL for compatibility with database module."""
        return self.DB_URL

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    OTP_EXPIRE_SECONDS: int = 300  # 5 minutes
    REDIS_URL: str = "redis://localhost:6379/0"

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

    SQLALCHEMY_DATABASE_URL: str = Field(default="") 
    # ── Frontend Base URL ──────────────────────────────────────────────────────
    FRONTEND_BASE_URL: str = Field(default="http://localhost:5173")

    # ── Team Invite Settings ───────────────────────────────────────────────────
    INVITE_EXPIRE_SECONDS: int = 259200  # 3 days
    PENDING_JOIN_EXPIRE_SECONDS: int = 86400  # 1 day

    # Frontend URLs — derived from FRONTEND_BASE_URL, overridable individually in .env
    @property
    def FRONTEND_INVITE_URL(self) -> str:
        return f"{self.FRONTEND_BASE_URL}/teams/invite"

    @property
    def FRONTEND_REGISTER_INVITE_URL(self) -> str:
        return f"{self.FRONTEND_BASE_URL}/register"

    @property
    def FRONTEND_RESET_PASSWORD_URL(self) -> str:
        return f"{self.FRONTEND_BASE_URL}/reset-password"

    @property
    def FRONTEND_OAUTH_SUCCESS_URL(self) -> str:
        return f"{self.FRONTEND_BASE_URL}/auth/google/callback"

    # ── Judge0 Code Execution ───────────────────────────────────────────────
    JUDGE0_BASE_URL: str = Field(default="http://localhost:2358")
    JUDGE0_AUTH_TOKEN: str = Field(default="")
    JUDGE0_MAX_BATCH_SIZE: int = Field(default=20)
    JUDGE0_POLL_INTERVAL_MS: int = Field(default=1000)
    JUDGE0_POLL_MAX_ATTEMPTS: int = Field(default=30)

    # ── Google Cloud Storage (Test Cases) ─────────────────────────────────────
    GCS_BUCKET_NAME: str = Field(default="devduel-testcases-9876")
    GCS_SERVICE_ACCOUNT_KEY_PATH: str = Field(default="")  # Local: path to JSON key file
    GCS_SERVICE_ACCOUNT_KEY_JSON: str = Field(default="")   # Server: raw JSON key content
    GCS_PROJECT_ID: str = Field(default="")

    class Config:
        env_file = ".env"


settings = Settings()
