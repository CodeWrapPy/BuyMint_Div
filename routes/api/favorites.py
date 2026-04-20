from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import Favorite, Product
from extensions import db

favorites_api = Blueprint("favorites_api", __name__, url_prefix="/api/favorites")


def _ok(data, status=200):
    return jsonify({"success": True, **data}), status


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


@favorites_api.route("/", methods=["GET"])
@login_required
def get_favorites():
    favs = (
        Favorite.query
        .filter_by(user_id=current_user.id)
        .join(Product)
        .order_by(Favorite.saved_at.desc())
        .all()
    )
    return _ok({"favorites": [f.to_dict() for f in favs], "count": len(favs)})


@favorites_api.route("/", methods=["POST"])
@login_required
def add_favorite():
    data       = request.get_json(silent=True) or {}
    product_id = data.get("product_id")

    if not product_id:
        return _err("product_id is required.")

    product = Product.query.filter_by(id=product_id, is_active=True).first()
    if not product:
        return _err("Product not found.", 404)

    existing = Favorite.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()
    if existing:
        return _ok({"message": "Already in favorites.", "is_favorite": True})

    fav = Favorite(user_id=current_user.id, product_id=product_id)
    db.session.add(fav)
    db.session.commit()
    return _ok({"message": "Added to favorites.", "is_favorite": True}, 201)


@favorites_api.route("/<int:product_id>", methods=["DELETE"])
@login_required
def remove_favorite(product_id):
    fav = Favorite.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()
    if not fav:
        return _err("Not in favorites.", 404)
    db.session.delete(fav)
    db.session.commit()
    return _ok({"message": "Removed from favorites.", "is_favorite": False})


@favorites_api.route("/<int:product_id>/toggle", methods=["POST"])
@login_required
def toggle_favorite(product_id):
    fav = Favorite.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        return _ok({"message": "Removed from favorites.", "is_favorite": False})
    else:
        product = Product.query.filter_by(id=product_id, is_active=True).first()
        if not product:
            return _err("Product not found.", 404)
        db.session.add(Favorite(user_id=current_user.id, product_id=product_id))
        db.session.commit()
        return _ok({"message": "Added to favorites.", "is_favorite": True}, 201)
