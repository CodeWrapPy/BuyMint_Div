from flask import Blueprint, request, jsonify
from flask_login import current_user
from models import ContactMessage
from extensions import db

contact_api = Blueprint("contact_api", __name__, url_prefix="/api/contact")


def _ok(data, status=200):
    return jsonify({"success": True, **data}), status


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


@contact_api.route("/", methods=["POST"])
def send_message():
    data    = request.get_json(silent=True) or {}
    name    = (data.get("name") or "").strip()
    email   = (data.get("email") or "").strip().lower()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    if not name:
        return _err("Name is required.")
    if not email:
        return _err("Email is required.")
    if not message:
        return _err("Message is required.")

    msg = ContactMessage(
        user_id = current_user.id if current_user.is_authenticated else None,
        name    = name,
        email   = email,
        subject = subject,
        message = message,
    )
    db.session.add(msg)
    db.session.commit()

    return _ok({"message": "Your message has been sent. We'll get back to you soon!"}, 201)
