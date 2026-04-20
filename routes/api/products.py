from flask import Blueprint, request, jsonify
from extensions import db
from models import Product

products_api = Blueprint("products_api", __name__, url_prefix="/api/products")

# BUG FIX #16: No cap on per_page — a client could send ?per_page=999999 and
# force the server to serialise the entire catalogue in one shot, causing a DoS.
MAX_PER_PAGE = 50


def _ok(data, status=200):
    return jsonify({"success": True, **data}), status


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


# ─── List all or search products ─────────────────────────────
@products_api.route("/", methods=["GET"])
def list_products():
    category = request.args.get("category")
    q        = request.args.get("q", "").strip()
    sort     = request.args.get("sort", "default")
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 12, type=int), MAX_PER_PAGE)

    query = Product.query.filter_by(is_active=True)

    if category:
        query = query.filter_by(category=category)

    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "rating":
        query = query.order_by(Product.rating.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return _ok({
        "products":     [p.to_dict() for p in pagination.items],
        "total":        pagination.total,
        "pages":        pagination.pages,
        "current_page": page,
    })


# ─── Single product ──────────────────────────────────────────
@products_api.route("/<int:product_id>", methods=["GET"])
def get_product(product_id):
    # BUG FIX #17: Product.query.get_or_404() uses the deprecated Query.get()
    # API which is removed in SQLAlchemy 2.x.  Use db.get_or_404() instead.
    product = db.get_or_404(Product, product_id)
    return _ok({"product": product.to_dict()})


# ─── Products by category ────────────────────────────────────
@products_api.route("/category/<string:category>", methods=["GET"])
def by_category(category):
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 12, type=int), MAX_PER_PAGE)

    pagination = (
        Product.query
        .filter_by(category=category, is_active=True)
        .order_by(Product.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return _ok({
        "category":     category,
        "products":     [p.to_dict() for p in pagination.items],
        "total":        pagination.total,
        "pages":        pagination.pages,
        "current_page": page,
    })


# ─── Search ──────────────────────────────────────────────────
@products_api.route("/search", methods=["GET"])
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return _err("Search query is required.", 400)

    results = (
        Product.query
        .filter(Product.is_active == True, Product.name.ilike(f"%{q}%"))
        .limit(20)
        .all()
    )
    return _ok({"query": q, "products": [p.to_dict() for p in results]})
