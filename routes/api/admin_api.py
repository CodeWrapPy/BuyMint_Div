"""
routes/api/admin_api.py
REST API endpoints for admin CRUD operations.
"""

from functools import wraps
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, Product, Order, ContactMessage, PromoCode
from datetime import datetime, timezone

admin_api = Blueprint("admin_api", __name__, url_prefix="/api/admin")


def _ok(data=None, status=200):
    return jsonify({"success": True, **(data or {})}), status


def _err(msg, status=400):
    return jsonify({"success": False, "error": msg}), status


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return _err("Forbidden", 403)
        return f(*args, **kwargs)
    return decorated


# ── Users ─────────────────────────────────────────────────────
@admin_api.route("/users/<int:user_id>", methods=["PATCH"])
@login_required
@admin_required
def update_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return _err("User not found", 404)
    data = request.get_json(silent=True) or {}
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if "is_admin" in data:
        # Prevent removing own admin rights
        if user.id == current_user.id and not data["is_admin"]:
            return _err("Cannot remove your own admin privileges.")
        user.is_admin = bool(data["is_admin"])
    if "full_name" in data and data["full_name"].strip():
        user.full_name = data["full_name"].strip()
    db.session.commit()
    return _ok({"user": user.to_dict()})


@admin_api.route("/users/<int:user_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return _err("User not found", 404)
    if user.id == current_user.id:
        return _err("Cannot delete your own account.")
    db.session.delete(user)
    db.session.commit()
    return _ok({"message": "User deleted."})


# ── Products ──────────────────────────────────────────────────
@admin_api.route("/products", methods=["POST"])
@login_required
@admin_required
def create_product():
    data = request.get_json(silent=True) or {}
    required = ["name", "price", "category"]
    for field in required:
        if not data.get(field):
            return _err(f"'{field}' is required.")
    product = Product(
        name           = data["name"].strip(),
        description    = data.get("description", "").strip(),
        price          = float(data["price"]),
        original_price = float(data["original_price"]) if data.get("original_price") else None,
        category       = data["category"].strip(),
        image_url      = data.get("image_url", "").strip() or None,
        is_organic     = bool(data.get("is_organic", True)),
        stock          = int(data.get("stock", 100)),
        rating         = float(data.get("rating", 4.5)),
        is_active      = bool(data.get("is_active", True)),
    )
    db.session.add(product)
    db.session.commit()
    return _ok({"product": product.to_dict()}, 201)


@admin_api.route("/products/<int:product_id>", methods=["PATCH"])
@login_required
@admin_required
def update_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return _err("Product not found", 404)
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"].strip():
        product.name = data["name"].strip()
    if "description" in data:
        product.description = data["description"].strip()
    if "price" in data:
        product.price = float(data["price"])
    if "original_price" in data:
        product.original_price = float(data["original_price"]) if data["original_price"] else None
    if "category" in data:
        product.category = data["category"].strip()
    if "image_url" in data:
        product.image_url = data["image_url"].strip() or None
    if "is_organic" in data:
        product.is_organic = bool(data["is_organic"])
    if "stock" in data:
        product.stock = int(data["stock"])
    if "is_active" in data:
        product.is_active = bool(data["is_active"])
    if "rating" in data:
        product.rating = float(data["rating"])
    db.session.commit()
    return _ok({"product": product.to_dict()})


@admin_api.route("/products/<int:product_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return _err("Product not found", 404)
    db.session.delete(product)
    db.session.commit()
    return _ok({"message": "Product deleted."})


# ── Orders ────────────────────────────────────────────────────
@admin_api.route("/orders/<int:order_id>", methods=["PATCH"])
@login_required
@admin_required
def update_order(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return _err("Order not found", 404)
    data = request.get_json(silent=True) or {}
    if "status" in data:
        if data["status"] not in Order.STATUS_CHOICES:
            return _err(f"Invalid status. Choose from: {Order.STATUS_CHOICES}")
        order.status = data["status"]
    db.session.commit()
    return _ok({"order": order.to_dict()})


# ── Messages ──────────────────────────────────────────────────
@admin_api.route("/messages/<int:msg_id>/read", methods=["POST"])
@login_required
@admin_required
def mark_message_read(msg_id):
    msg = db.session.get(ContactMessage, msg_id)
    if not msg:
        return _err("Message not found", 404)
    msg.is_read = True
    db.session.commit()
    return _ok({"message": "Marked as read."})


@admin_api.route("/messages/<int:msg_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_message(msg_id):
    msg = db.session.get(ContactMessage, msg_id)
    if not msg:
        return _err("Message not found", 404)
    db.session.delete(msg)
    db.session.commit()
    return _ok({"message": "Message deleted."})


# ── Promo Codes ───────────────────────────────────────────────
@admin_api.route("/promos", methods=["POST"])
@login_required
@admin_required
def create_promo():
    data = request.get_json(silent=True) or {}
    if not data.get("code") or not data.get("discount_value"):
        return _err("'code' and 'discount_value' are required.")
    if PromoCode.query.filter_by(code=data["code"].upper()).first():
        return _err("A promo with this code already exists.")
    expires = None
    if data.get("expires_at"):
        try:
            expires = datetime.fromisoformat(data["expires_at"]).replace(tzinfo=timezone.utc)
        except ValueError:
            return _err("Invalid expires_at format. Use ISO 8601.")
    promo = PromoCode(
        code           = data["code"].upper().strip(),
        discount_type  = data.get("discount_type", "percent"),
        discount_value = float(data["discount_value"]),
        min_order_value= float(data.get("min_order_value", 0)),
        max_uses       = int(data.get("max_uses", 1000)),
        is_active      = bool(data.get("is_active", True)),
        expires_at     = expires,
    )
    db.session.add(promo)
    db.session.commit()
    return _ok({"promo": promo.to_dict()}, 201)


@admin_api.route("/promos/<int:promo_id>", methods=["PATCH"])
@login_required
@admin_required
def update_promo(promo_id):
    promo = db.session.get(PromoCode, promo_id)
    if not promo:
        return _err("Promo not found", 404)
    data = request.get_json(silent=True) or {}
    if "is_active" in data:
        promo.is_active = bool(data["is_active"])
    if "discount_value" in data:
        promo.discount_value = float(data["discount_value"])
    if "max_uses" in data:
        promo.max_uses = int(data["max_uses"])
    db.session.commit()
    return _ok({"promo": promo.to_dict()})


@admin_api.route("/promos/<int:promo_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_promo(promo_id):
    promo = db.session.get(PromoCode, promo_id)
    if not promo:
        return _err("Promo not found", 404)
    db.session.delete(promo)
    db.session.commit()
    return _ok({"message": "Promo code deleted."})


# ── Make first user admin utility ─────────────────────────────
@admin_api.route("/make-admin/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def make_admin(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return _err("User not found", 404)
    user.is_admin = True
    db.session.commit()
    return _ok({"message": f"{user.full_name} is now an admin."})
