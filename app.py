import os
from flask import Flask
from config import config_map
from extensions import db, login_manager, bcrypt, csrf, oauth


def create_app(env: str = None) -> Flask:
    env = env or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_map.get(env, config_map["default"]))

    # ── Extensions ──────────────────────────────────────────
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    oauth.init_app(app)

    # ── OAuth Providers ──────────────────────────────────────
    # Google — needs GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET in .env
    oauth.register(
        name="google",
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    # Apple — needs APPLE_CLIENT_ID + APPLE_CLIENT_SECRET in .env
    oauth.register(
        name="apple",
        client_id=os.environ.get("APPLE_CLIENT_ID"),
        client_secret=os.environ.get("APPLE_CLIENT_SECRET"),
        authorize_url="https://appleid.apple.com/auth/authorize",
        access_token_url="https://appleid.apple.com/auth/token",
        jwks_uri="https://appleid.apple.com/auth/keys",
        client_kwargs={
            "scope": "name email",
            "response_mode": "form_post",
        },
    )

    # ── User loader ─────────────────────────────────────────
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from flask_login import current_user

    @app.context_processor
    def inject_current_user():
        return {"current_user": current_user}

    # ── Blueprints – Page Views ──────────────────────────────
    from routes.views import views
    app.register_blueprint(views)

    # ── Blueprints – REST API ────────────────────────────────
    from routes.api.auth      import auth_api
    from routes.api.products  import products_api
    from routes.api.cart      import cart_api
    from routes.api.favorites import favorites_api
    from routes.api.orders    import orders_api
    from routes.api.profile   import profile_api
    from routes.api.contact   import contact_api
    from routes.api.rewards   import rewards_api

    for bp in (
        auth_api, products_api, cart_api,
        favorites_api, orders_api, profile_api,
        contact_api, rewards_api,
    ):
        csrf.exempt(bp)
        app.register_blueprint(bp)

    # ── DB + seed ────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        _seed_if_empty()

    return app


def _seed_if_empty():
    from models import Product
    if Product.query.first():
        return
    from seed import run_seed
    run_seed()


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(debug=flask_app.config.get("DEBUG", False), port=5000)
