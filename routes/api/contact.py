"""
routes/api/contact.py

Saves every enquiry to the database AND sends an SMS to the owner's
phone via Twilio (if credentials are configured in .env).

Required .env variables for SMS:
    TWILIO_ACCOUNT_SID  – your Twilio Account SID
    TWILIO_AUTH_TOKEN   – your Twilio Auth Token
    TWILIO_FROM_NUMBER  – the Twilio phone number to send FROM  e.g. +12015551234
    OWNER_PHONE_NUMBER  – the owner's phone number to receive SMS  e.g. +919876543210

If any of those four variables are missing, the contact form still works
normally — the enquiry is saved to the DB — and a warning is printed to
the console instead of crashing the server.
"""

import os
import textwrap

from flask import Blueprint, request, jsonify
from flask_login import current_user
from models import ContactMessage
from extensions import db

contact_api = Blueprint("contact_api", __name__, url_prefix="/api/contact")


def _ok(data, status=200):
    return jsonify({"success": True, **data}), status


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


def _send_sms(name: str, email: str, subject: str, message: str) -> None:
    """
    Fire an SMS to the owner via Twilio.
    All errors are caught and logged — SMS failure must never block the
    user from submitting a contact form.
    """
    sid   = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    from_ = os.environ.get("TWILIO_FROM_NUMBER", "").strip()
    to    = os.environ.get("OWNER_PHONE_NUMBER", "").strip()

    if not all([sid, token, from_, to]):
        print(
            "[BuyMint] SMS not sent — Twilio credentials missing. "
            "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
            "TWILIO_FROM_NUMBER and OWNER_PHONE_NUMBER in .env"
        )
        return

    try:
        from twilio.rest import Client  # imported lazily so missing package gives a clear error

        # Twilio SMS body max is 1600 chars. We trim the message to keep it
        # readable on a phone screen (~160 chars per SMS segment).
        snippet = textwrap.shorten(message, width=200, placeholder="…")

        body = (
            f"📬 New BuyMint Enquiry\n"
            f"From : {name} <{email}>\n"
            f"Topic: {subject or '(no subject)'}\n"
            f"Msg  : {snippet}"
        )

        client = Client(sid, token)
        sent   = client.messages.create(body=body, from_=from_, to=to)
        print(f"[BuyMint] SMS sent — SID: {sent.sid}")

    except ImportError:
        print(
            "[BuyMint] twilio package not installed. "
            "Run: pip install twilio --break-system-packages"
        )
    except Exception as exc:
        # Log but do NOT re-raise — the DB save already succeeded.
        print(f"[BuyMint] SMS delivery failed: {exc}")


@contact_api.route("/", methods=["POST"])
def send_message():
    data    = request.get_json(silent=True) or {}
    name    = (data.get("name")    or "").strip()
    email   = (data.get("email")   or "").strip().lower()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    if not name:
        return _err("Name is required.")
    if not email:
        return _err("Email is required.")
    if not message:
        return _err("Message is required.")

    # 1. Always save to DB first — this is the source of truth.
    msg = ContactMessage(
        user_id = current_user.id if current_user.is_authenticated else None,
        name    = name,
        email   = email,
        subject = subject,
        message = message,
    )
    db.session.add(msg)
    db.session.commit()

    # 2. Best-effort SMS notification to the owner.
    _send_sms(name, email, subject, message)

    return _ok({"message": "Your message has been sent. We'll get back to you soon!"}, 201)
