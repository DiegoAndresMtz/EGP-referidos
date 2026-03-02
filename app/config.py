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

    # WhatsApp (soporta "ultramsg" o "meta")
    WHATSAPP_ENABLED: bool = False
    WHATSAPP_PROVIDER: str = "ultramsg"   # "ultramsg" o "meta"

    # UltraMsg (ultramsg.com — solo escanear QR, sin aprobación de Meta)
    WHATSAPP_INSTANCE_ID: str = ""        # ID de instancia (ej: instance12345)
    WHATSAPP_INSTANCE_TOKEN: str = ""     # Token de la instancia

    # Meta WhatsApp Business Cloud API (requiere aprobación de Meta)
    WHATSAPP_META_TOKEN: str = ""         # Token de acceso permanente
    WHATSAPP_META_PHONE_ID: str = ""      # ID del número de teléfono

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
