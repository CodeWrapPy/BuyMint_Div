import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "buymint-dev-secret-key-2024")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///buymint.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    DEBUG = True
    # BUG FIX #3: FLASK_ENV = "development" was set here as a Flask config key,
    # but FLASK_ENV is an OS-level environment variable consumed by the Flask CLI
    # — it is NOT a Flask app config attribute and has zero effect when set here.
    # Removed. Set FLASK_ENV=development in your .env file instead.


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    @classmethod
    def init_app(cls, app):
        # Enforce a real secret key in production — refuse to start with the
        # insecure default, which would allow session forgery.
        if app.config["SECRET_KEY"] == "buymint-dev-secret-key-2024":
            raise RuntimeError(
                "SECRET_KEY is set to the insecure development default. "
                "Set a strong SECRET_KEY in your .env before deploying."
            )


config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
