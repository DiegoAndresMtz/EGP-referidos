from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./referidos.db"

    # JWT
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Admin seed
    ADMIN_EMAIL: str = "admin@egp.com"
    ADMIN_PASSWORD: str = "Admin123!"
    ADMIN_NAME: str = "Admin"
    ADMIN_LAST_NAME: str = "EGP"

    # App
    APP_NAME: str = "EGP Referidos"
    BASE_URL: str = "http://localhost:8000"

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "EGP Referidos <noreply@egp.com>"
    EMAILS_ENABLED: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
