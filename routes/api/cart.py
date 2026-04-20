from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import CartItem, Product, Order, OrderItem, PromoCode
from extensions import db
from datetime import datetime

cart_api = Blueprint("cart_api", __name__, url_prefix="/api/cart")

DELIVERY_THRESHOLD = 500.0   # free delivery above this amount
DELIVERY_FEE       = 49.0
POINTS_PER_RUPEE   = 0.1     # reward points earned per ₹ spent


def _ok(data, status=200):
    return jsonify({"success": True, **data}), status


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


def _cart_summary(user_id: int) -> dict:
    items = (
        CartItem.query
        .filter_by(user_id=user_id)
        .join(Product)
        .all()
    )
    subtotal     = sum(i.quantity * i.product.price for i in items)
    delivery_fee = 0.0 if subtotal >= DELIVERY_THRESHOLD else DELIVERY_FEE
    total        = subtotal + delivery_fee

    return {
        "items":        [i.to_dict() for i in items],
        "item_count":   sum(i.quantity for i in items),
        "subtotal":     round(subtotal, 2),
        "delivery_fee": delivery_fee,
        "total":        round(total, 2),
    }


# ─── Get cart ────────────────────────────────────────────────
@cart_api.route("/", methods=["GET"])
@login_required
def get_cart():
    return _ok(_cart_summary(current_user.id))


# ─── Add / increment item ────────────────────────────────────
@cart_api.route("/", methods=["POST"])
@login_required
def add_to_cart():
    data       = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity   = int(data.get("quantity", 1))

    if not product_id:
        return _err("product_id is required.")

    product = Product.query.filter_by(id=product_id, is_active=True).first()
    if not product:
        return _err("Product not found.", 404)
    if product.stock < 1:
        return _err("Product is out of stock.")

    item = CartItem.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()

    if item:
        new_qty = item.quantity + quantity
        if new_qty > product.stock:
            return _err(f"Only {product.stock} units available.")
        item.quantity = new_qty
    else:
        item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity,
        )
        db.session.add(item)

    db.session.commit()
    return _ok({"message": "Added to cart.", "cart": _cart_summary(current_user.id)}, 201)


# ─── Update item quantity ────────────────────────────────────
@cart_api.route("/<int:item_id>", methods=["PUT"])
@login_required
def update_cart_item(item_id):
    data     = request.get_json(silent=True) or {}
    quantity = int(data.get("quantity", 1))

    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        return _err("Cart item not found.", 404)

    if quantity < 1:
        db.session.delete(item)
    else:
        if quantity > item.product.stock:
            return _err(f"Only {item.product.stock} units available.")
        item.quantity = quantity

    db.session.commit()
    return _ok({"message": "Cart updated.", "cart": _cart_summary(current_user.id)})


# ─── Remove item ─────────────────────────────────────────────
@cart_api.route("/<int:item_id>", methods=["DELETE"])
@login_required
def remove_cart_item(item_id):
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        return _err("Cart item not found.", 404)
    db.session.delete(item)
    db.session.commit()
    return _ok({"message": "Item removed.", "cart": _cart_summary(current_user.id)})


# ─── Clear entire cart ───────────────────────────────────────
@cart_api.route("/", methods=["DELETE"])
@login_required
def clear_cart():
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return _ok({"message": "Cart cleared."})


# ─── Validate promo code ─────────────────────────────────────
@cart_api.route("/promo", methods=["POST"])
@login_required
def validate_promo():
    data  = request.get_json(silent=True) or {}
    code  = (data.get("code") or "").strip().upper()

    if not code:
        return _err("Promo code is required.")

    promo = PromoCode.query.filter_by(code=code, is_active=True).first()
    if not promo:
        return _err("Invalid or expired promo code.")
    if promo.expires_at and promo.expires_at < datetime.utcnow():
        return _err("This promo code has expired.")
    if promo.used_count >= promo.max_uses:
        return _err("This promo code has reached its usage limit.")

    summary = _cart_summary(current_user.id)
    if summary["subtotal"] < promo.min_order_value:
        return _err(f"Minimum order of ₹{promo.min_order_value:.0f} required for this code.")

    if promo.discount_type == "percent":
        discount = round(summary["subtotal"] * promo.discount_value / 100, 2)
    else:
        discount = min(promo.discount_value, summary["subtotal"])

    return _ok({
        "valid":    True,
        "discount": discount,
        "promo":    promo.to_dict(),
        "new_total": round(summary["total"] - discount, 2),
    })


# ─── Checkout ────────────────────────────────────────────────
@cart_api.route("/checkout", methods=["POST"])
@login_required
def checkout():
    data    = request.get_json(silent=True) or {}
    address = (data.get("shipping_address") or "").strip()
    code    = (data.get("promo_code") or "").strip().upper()

    if not address:
        return _err("Shipping address is required.")

    summary = _cart_summary(current_user.id)
    if not summary["items"]:
        return _err("Your cart is empty.")

    discount = 0.0
    promo    = None
    if code:
        promo = PromoCode.query.filter_by(code=code, is_active=True).first()
        if promo and promo.used_count < promo.max_uses:
            if promo.discount_type == "percent":
                discount = round(summary["subtotal"] * promo.discount_value / 100, 2)
            else:
                discount = min(promo.discount_value, summary["subtotal"])
            promo.used_count += 1

    final_total = round(summary["total"] - discount, 2)

    order = Order(
        user_id          = current_user.id,
        total_amount     = final_total,
        discount_amount  = discount,
        delivery_fee     = summary["delivery_fee"],
        shipping_address = address,
        promo_code       = code or None,
        status           = "confirmed",
    )
    db.session.add(order)
    db.session.flush()   # get order.id before commit

    for ci in CartItem.query.filter_by(user_id=current_user.id).all():
        oi = OrderItem(
            order_id   = order.id,
            product_id = ci.product_id,
            quantity   = ci.quantity,
            unit_price = ci.product.price,
        )
        # Decrement stock
        ci.product.stock = max(0, ci.product.stock - ci.quantity)
        db.session.add(oi)
        db.session.delete(ci)

    # Award reward points
    points_earned = int(final_total * POINTS_PER_RUPEE)
    current_user.reward_points += points_earned
    current_user.update_tier()

    db.session.commit()
    return _ok({
        "message":       "Order placed successfully!",
        "order":         order.to_dict(),
        "points_earned": points_earned,
    }, 201)
