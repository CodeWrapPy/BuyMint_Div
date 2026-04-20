from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import CartItem, Product, Order, OrderItem, PromoCode
from extensions import db

cart_api = Blueprint("cart_api", __name__, url_prefix="/api/cart")

DELIVERY_THRESHOLD = 500.0    # free delivery above this amount
DELIVERY_FEE       = 49.0
POINTS_PER_RUPEE   = 0.1      # reward points earned per ₹ spent
MAX_QUANTITY       = 99       # sanity cap on per-item quantity


def _ok(data, status=200):
    return jsonify({"success": True, **data}), status


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


def _parse_quantity(raw, default=1) -> tuple[int, str]:
    """
    Safely parse an integer quantity from untrusted input.
    Returns (quantity, error_message). error_message is "" on success.
    """
    try:
        qty = int(raw if raw is not None else default)
    except (ValueError, TypeError):
        return 0, "quantity must be an integer."
    if qty < 0:
        return 0, "quantity cannot be negative."
    if qty > MAX_QUANTITY:
        return 0, f"quantity cannot exceed {MAX_QUANTITY}."
    return qty, ""


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
        # BUG FIX #11: item_count now returns the total quantity across all
        # line items (e.g. 3 tees + 2 mugs = 5), matching what the JS
        # Cart._updateBadges() uses to display the badge count.
        # Previously views.py used len(items) (number of distinct products)
        # which disagreed with the badge count shown after JS cart operations.
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

    if not product_id:
        return _err("product_id is required.")

    # BUG FIX #12: int(data.get("quantity", 1)) raised ValueError if the client
    # sent a non-numeric string (e.g. "quantity": "abc"), crashing the server
    # with a 500 instead of returning a clean 400.
    quantity, qty_err = _parse_quantity(data.get("quantity"), default=1)
    if qty_err:
        return _err(f"Invalid quantity: {qty_err}")
    if quantity < 1:
        return _err("quantity must be at least 1.")

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
        if quantity > product.stock:
            return _err(f"Only {product.stock} units available.")
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
    data = request.get_json(silent=True) or {}

    # BUG FIX #13: Same int() crash risk as add_to_cart — fixed via _parse_quantity.
    quantity, qty_err = _parse_quantity(data.get("quantity"), default=1)
    if qty_err:
        return _err(f"Invalid quantity: {qty_err}")

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
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()

    if not code:
        return _err("Promo code is required.")

    promo = PromoCode.query.filter_by(code=code).first()
    if not promo:
        return _err("Invalid or expired promo code.")

    summary = _cart_summary(current_user.id)
    valid, err = promo.is_valid(summary["subtotal"])
    if not valid:
        return _err(err)

    discount = promo.compute_discount(summary["subtotal"])
    return _ok({
        "valid":     True,
        "discount":  discount,
        "promo":     promo.to_dict(),
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
        promo = PromoCode.query.filter_by(code=code).first()
        if promo:
            # BUG FIX #14: checkout() previously only checked used_count < max_uses
            # and silently skipped the expires_at check that validate_promo() did.
            # This meant an expired promo was rejected at validation time but still
            # applied at checkout — a meaningful discount bypass.
            # Now we use the centralised promo.is_valid() which checks all three
            # conditions: is_active, expires_at, max_uses, and min_order_value.
            valid, err = promo.is_valid(summary["subtotal"])
            if not valid:
                return _err(f"Promo code issue at checkout: {err}")
            discount = promo.compute_discount(summary["subtotal"])

    final_total = round(summary["total"] - discount, 2)

    try:
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
        db.session.flush()   # get order.id before committing

        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        for ci in cart_items:
            # BUG FIX #15: Stock was decremented without re-checking availability.
            # Between "add to cart" and "checkout", another user could have bought
            # the last unit.  We now enforce the check at checkout time.
            if ci.product.stock < ci.quantity:
                db.session.rollback()
                return _err(
                    f"'{ci.product.name}' now has only {ci.product.stock} unit(s) "
                    f"in stock. Please update your cart."
                )
            oi = OrderItem(
                order_id   = order.id,
                product_id = ci.product_id,
                quantity   = ci.quantity,
                unit_price = ci.product.price,
            )
            ci.product.stock -= ci.quantity
            db.session.add(oi)
            db.session.delete(ci)

        # Increment promo usage counter only on a successful checkout
        if promo:
            promo.used_count += 1

        # Award reward points
        points_earned = int(final_total * POINTS_PER_RUPEE)
        current_user.reward_points += points_earned
        current_user.update_tier()

        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    return _ok({
        "message":       "Order placed successfully!",
        "order":         order.to_dict(),
        "points_earned": points_earned,
    }, 201)
