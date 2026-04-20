import re
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import db

auth_api = Blueprint("auth_api", __name__, url_prefix="/api/auth")

# Simple but effective email regex — rejects obvious non-emails while staying
# tolerant of international TLDs.  Full RFC-5322 parsing is overkill here.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _ok(data: dict, status: int = 200):
    return jsonify({"success": True, **data}), status


def _err(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


# ─── Register ────────────────────────────────────────────────
@auth_api.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or "").strip()
    email     = (data.get("email") or "").strip().lower()
    password  = data.get("password") or ""

    if not full_name:
        return _err("Full name is required.")
    if not email:
        return _err("Email is required.")
    # BUG FIX #9: No email format validation — any string (or empty string with
    # just spaces) was accepted and stored, breaking email-based lookups later.
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

    # BUG FIX #10: register() was calling login_user(user, remember=True),
    # hardcoding a persistent ("remember me") session for every new user,
    # regardless of whether they asked for one.  Changed to remember=False so
    # the session expires when the browser closes (standard, secure default).
    login_user(user, remember=False)
    return _ok({"message": "Account created successfully.", "user": user.to_dict()}, 201)


# ─── Login ───────────────────────────────────────────────────
@auth_api.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

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


# ─── Logout ──────────────────────────────────────────────────
@auth_api.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return _ok({"message": "Logged out successfully."})


# ─── Current User ────────────────────────────────────────────
@auth_api.route("/me", methods=["GET"])
@login_required
def me():
    return _ok({"user": current_user.to_dict()})
