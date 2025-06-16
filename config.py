import os
from dotenv import load_dotenv

load_dotenv(override=True)

class BaseConfig:
    """
    Configuración base para todos los entornos.
    """
    SECRET_KEY = os.getenv("SECRET_KEY", "cambia_esto")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://usuario:clave@localhost:5432/chatgpt_db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ALLOWED_MODELS = os.getenv(
        "ALLOWED_MODELS",
        "chatgpt-4o-latest,o4-mini,gpt-4o-mini-2024-07-18"
    ).split(",")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Configuración para correo electrónico
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 25))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "False").lower() in ("true", "1", "t")
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False").lower() in ("true", "1", "t")

class DevelopmentConfig(BaseConfig):
    DEBUG = True

class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")

class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig
}
