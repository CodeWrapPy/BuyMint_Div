from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import Order

orders_api = Blueprint("orders_api", __name__, url_prefix="/api/orders")


def _ok(data, status=200):
    return jsonify({"success": True, **data}), status


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


@orders_api.route("/", methods=["GET"])
@login_required
def list_orders():
    orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return _ok({"orders": [o.to_dict() for o in orders], "count": len(orders)})


@orders_api.route("/<int:order_id>", methods=["GET"])
@login_required
def get_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
    if not order:
        return _err("Order not found.", 404)
    return _ok({"order": order.to_dict()})
