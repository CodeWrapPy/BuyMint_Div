from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db

profile_api = Blueprint("profile_api", __name__, url_prefix="/api/profile")


def _ok(data, status=200):
    return jsonify({"success": True, **data}), status


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


@profile_api.route("/", methods=["GET"])
@login_required
def get_profile():
    return _ok({"user": current_user.to_dict()})


@profile_api.route("/", methods=["PUT"])
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or "").strip()
    phone     = (data.get("phone") or "").strip()
    address   = (data.get("address") or "").strip()
    avatar    = (data.get("avatar_url") or "").strip()

    if full_name:
        current_user.full_name = full_name
    if phone:
        current_user.phone = phone
    if address:
        current_user.address = address
    if avatar:
        current_user.avatar_url = avatar

    db.session.commit()
    return _ok({"message": "Profile updated.", "user": current_user.to_dict()})


@profile_api.route("/change-password", methods=["POST"])
@login_required
def change_password():
    data         = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""

    if not current_user.check_password(old_password):
        return _err("Current password is incorrect.")
    if len(new_password) < 6:
        return _err("New password must be at least 6 characters.")

    current_user.set_password(new_password)
    db.session.commit()
    return _ok({"message": "Password changed successfully."})
