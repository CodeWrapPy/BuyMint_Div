import os

from flask import Flask

from config import config_map
from extensions import db, login_manager, bcrypt, csrf


def create_app(env: str = None) -> Flask:
    env = env or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_map.get(env, config_map["default"]))

    # ── Extensions ──────────────────────────────────────────
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # ── User loader ─────────────────────────────────────────
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        # BUG FIX #1: User.query.get() is deprecated in SQLAlchemy 2.x and
        # raises LegacyAPIWarning / may crash. Use db.session.get() instead.
        return db.session.get(User, int(user_id))

    # ── Inject current_user into ALL template contexts ───────
    # Flask-Login's current_user is available in normal templates
    # but NOT inside Jinja2 macros (they use an isolated scope).
    # A context_processor promotes it to a Jinja2 global, fixing that.
    from flask_login import current_user

    @app.context_processor
    def inject_current_user():
        return {"current_user": current_user}

    # ── Blueprints – Page Views ──────────────────────────────
    from routes.views import views

    app.register_blueprint(views)

    # ── Blueprints – REST API ────────────────────────────────
    from routes.api.auth import auth_api
    from routes.api.products import products_api
    from routes.api.cart import cart_api
    from routes.api.favorites import favorites_api
    from routes.api.orders import orders_api
    from routes.api.profile import profile_api
    from routes.api.contact import contact_api
    from routes.api.rewards import rewards_api

    for bp in (
        auth_api, products_api, cart_api,
        favorites_api, orders_api, profile_api,
        contact_api, rewards_api,
    ):
        # CSRF exempt for JSON API endpoints (using session auth instead)
        csrf.exempt(bp)
        app.register_blueprint(bp)

    # ── Create tables & seed ─────────────────────────────────
    with app.app_context():
        db.create_all()
        _seed_if_empty()

    return app


def _seed_if_empty():
    """Insert sample data only on a fresh database."""
    from models import Product

    if Product.query.first():
        return

    from seed import run_seed
    run_seed()


# ── Run ─────────────────────────────────────────────────────
if __name__ == "__main__":
    flask_app = create_app()
    # BUG FIX #2: debug=True was hardcoded, which means the app always ran in
    # debug mode even in production. Now it reads from the Flask config,
    # which is set by FLASK_ENV / config_map (DevelopmentConfig → DEBUG=True,
    # ProductionConfig → DEBUG=False).
    flask_app.run(debug=flask_app.config.get("DEBUG", False), port=5000)
