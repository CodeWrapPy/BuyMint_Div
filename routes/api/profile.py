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

    # BUG FIX #18: The old implementation only updated a field when the new value
    # was truthy, meaning users could never blank out their phone number or address
    # once set (sending "" silently did nothing).
    #
    # Fix: use a sentinel approach — only skip the key entirely if it is absent
    # from the JSON body (i.e. the caller didn't mention it at all).  An
    # explicitly supplied empty string IS a valid "please clear this field".
    #
    # full_name is the exception: we never allow it to be cleared to "" because
    # it is a non-nullable DB column and a required display name.

    if "full_name" in data:
        full_name = (data["full_name"] or "").strip()
        if not full_name:
            return _err("Full name cannot be empty.")
        current_user.full_name = full_name

    if "phone" in data:
        current_user.phone = (data["phone"] or "").strip() or None

    if "address" in data:
        current_user.address = (data["address"] or "").strip() or None

    if "avatar_url" in data:
        current_user.avatar_url = (data["avatar_url"] or "").strip() or None

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
    if old_password == new_password:
        return _err("New password must be different from the current password.")

    current_user.set_password(new_password)
    db.session.commit()
    return _ok({"message": "Password changed successfully."})
