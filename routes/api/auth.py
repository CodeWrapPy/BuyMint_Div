"""
routes/api/auth.py

Email/password auth + Google OAuth + Apple Sign In.

─── Google setup (5 min, free) ───────────────────────────────
1. https://console.cloud.google.com → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID  (Web Application)
3. Authorised redirect URI: http://localhost:5000/api/auth/google/callback
4. Add to .env:
     GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
     GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxx

─── Apple setup (requires Apple Developer account $99/yr) ────
1. developer.apple.com → Identifiers → register App ID (enable Sign In with Apple)
2. Identifiers → register Service ID (set Return URL to your callback URL)
3. Keys → create key (enable Sign In with Apple, download .p8 file)
4. Add to .env:
     APPLE_CLIENT_ID=com.yourdomain.buymint          ← your Service ID
     APPLE_TEAM_ID=XXXXXXXXXX
     APPLE_KEY_ID=XXXXXXXXXX
     APPLE_PRIVATE_KEY_PATH=/path/to/AuthKey_XXXXXX.p8
"""

import json
import os
import re
import secrets
import time

from flask import Blueprint, request, jsonify, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db, oauth, bcrypt
from models import User

auth_api = Blueprint("auth_api", __name__, url_prefix="/api/auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ─── Shared helpers ───────────────────────────────────────────
def _ok(data: dict, status: int = 200):
    return jsonify({"success": True, **data}), status


def _err(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


def _find_or_create_oauth_user(email: str, full_name: str, provider: str) -> User:
    """
    Find an existing user by email or create a new passwordless one.
    Email is the canonical identity — a user who already registered with
    password can also log in via OAuth on the same account.
    """
    email = email.strip().lower()
    user  = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            full_name     = full_name or email.split("@")[0].replace(".", " ").title(),
            email         = email,
            password_hash = bcrypt.generate_password_hash(secrets.token_hex(32)).decode(),
        )
        db.session.add(user)
        db.session.commit()
        print(f"[OAuth:{provider}] New user created — {email}")
    else:
        print(f"[OAuth:{provider}] Existing user logged in — {email}")
    return user


def _build_apple_secret() -> str | None:
    """
    Apple requires a signed ES256 JWT as its client_secret.
    Generated fresh each time (Apple allows max 6-month expiry).
    Returns None if env vars are missing.
    """
    team_id  = os.environ.get("APPLE_TEAM_ID", "").strip()
    key_id   = os.environ.get("APPLE_KEY_ID", "").strip()
    key_path = os.environ.get("APPLE_PRIVATE_KEY_PATH", "").strip()
    client   = os.environ.get("APPLE_CLIENT_ID", "").strip()

    if not all([team_id, key_id, key_path, client]):
        return None

    try:
        import jwt as pyjwt          # pip install PyJWT[crypto]
        with open(key_path) as fh:
            private_key = fh.read()

        now = int(time.time())
        return pyjwt.encode(
            {"iss": team_id, "iat": now, "exp": now + 86400 * 180,
             "aud": "https://appleid.apple.com", "sub": client},
            private_key,
            algorithm="ES256",
            headers={"kid": key_id},
        )
    except Exception as exc:
        print(f"[Apple] client_secret build failed: {exc}")
        return None


# ─── Email / Password ─────────────────────────────────────────
@auth_api.route("/register", methods=["POST"])
def register():
    data      = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email     = (data.get("email") or "").strip().lower()
    password  = data.get("password") or ""

    if not full_name:
        return _err("Full name is required.")
    if not _EMAIL_RE.match(email):
        return _err("Please enter a valid email address.")
    if len(password) < 6:
        return _err("Password must be at least 6 characters.")
    if User.query.filter_by(email=email).first():
        return _err("An account with this email already exists.")

    user = User(full_name=full_name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user, remember=False)
    return _ok({"message": "Account created successfully.", "user": user.to_dict()}, 201)


@auth_api.route("/login", methods=["POST"])
def login():
    data     = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    remember = bool(data.get("remember", False))

    if not email or not password:
        return _err("Email and password are required.")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return _err("Invalid email or password.")
    if not user.is_active:
        return _err("This account has been deactivated.")

    login_user(user, remember=remember)
    return _ok({"message": "Logged in successfully.", "user": user.to_dict()})


@auth_api.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return _ok({"message": "Logged out successfully."})


@auth_api.route("/me", methods=["GET"])
@login_required
def me():
    return _ok({"user": current_user.to_dict()})


# ─── Google OAuth ─────────────────────────────────────────────
@auth_api.route("/google/login")
def google_login():
    if not os.environ.get("GOOGLE_CLIENT_ID"):
        # Redirect back with a readable error flag so login.html can show a toast
        return redirect(url_for("views.login") + "?oauth_error=google_not_configured")

    redirect_uri = url_for("auth_api.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_api.route("/google/callback")
def google_callback():
    try:
        token     = oauth.google.authorize_access_token()
        user_info = token.get("userinfo") or oauth.google.userinfo()
        email     = (user_info.get("email") or "").strip()
        full_name = user_info.get("name") or user_info.get("given_name") or ""

        if not email:
            return redirect(url_for("views.login") + "?oauth_error=google_no_email")

        user = _find_or_create_oauth_user(email, full_name, "Google")
        login_user(user, remember=True)
        return redirect(url_for("views.home"))

    except Exception as exc:
        print(f"[Google OAuth] error: {exc}")
        return redirect(url_for("views.login") + "?oauth_error=google_failed")


# ─── Apple Sign In ────────────────────────────────────────────
@auth_api.route("/apple/login")
def apple_login():
    if not os.environ.get("APPLE_CLIENT_ID"):
        return redirect(url_for("views.login") + "?oauth_error=apple_not_configured")

    secret = _build_apple_secret()
    if secret:
        oauth.apple.client_secret = secret

    redirect_uri = url_for("auth_api.apple_callback", _external=True)
    return oauth.apple.authorize_redirect(redirect_uri)


@auth_api.route("/apple/callback", methods=["GET", "POST"])
def apple_callback():
    """
    Apple always uses response_mode=form_post, so this must accept POST.
    The user's name is only sent on the very first login — we cache it in
    the session so subsequent logins keep the correct display name.
    """
    try:
        # Apple sends name as JSON-encoded form field on first auth only
        raw       = request.form.get("user", "{}")
        apple_obj = json.loads(raw) if raw else {}
        name_obj  = apple_obj.get("name", {})
        full_name = " ".join(filter(None, [
            name_obj.get("firstName", ""),
            name_obj.get("lastName", ""),
        ])).strip()

        secret = _build_apple_secret()
        if secret:
            oauth.apple.client_secret = secret

        token  = oauth.apple.authorize_access_token()
        claims = oauth.apple.parse_id_token(token, nonce=None)
        email  = (claims.get("email") or "").strip()

        if not email:
            return redirect(url_for("views.login") + "?oauth_error=apple_no_email")

        # Use cached name from session if Apple didn't send one this time
        cache_key = f"apple_name_{email}"
        if full_name:
            session[cache_key] = full_name
        else:
            full_name = session.get(cache_key, "")

        user = _find_or_create_oauth_user(email, full_name, "Apple")

        # Update name if we just learned it for the first time
        if full_name and (not user.full_name or user.full_name == email.split("@")[0].title()):
            user.full_name = full_name
            db.session.commit()

        login_user(user, remember=True)
        return redirect(url_for("views.home"))

    except Exception as exc:
        print(f"[Apple Sign In] error: {exc}")
        return redirect(url_for("views.login") + "?oauth_error=apple_failed")
