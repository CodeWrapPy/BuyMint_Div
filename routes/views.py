from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Product, Order, CartItem, Favorite
from extensions import db

views = Blueprint("views", __name__)


# ─── Public Pages ────────────────────────────────────────────
@views.route("/")
def index():
    """Landing page (pre-login showcase)."""
    featured_products = Product.query.filter_by(is_active=True).limit(6).all()
    return render_template("home.html", products=featured_products)


@views.route("/home")
@login_required
def home():
    """Authenticated home / dashboard."""
    featured = Product.query.filter_by(is_active=True).limit(8).all()
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    return render_template("home2.html", products=featured, cart_count=cart_count)


@views.route("/about")
def about():
    return render_template("aboutus.html")


@views.route("/faq")
def faq():
    return render_template("faq.html")


@views.route("/terms")
def terms():
    return render_template("term.html")


@views.route("/contact")
def contact():
    return render_template("contact.html")


# ─── Auth Pages ──────────────────────────────────────────────
@views.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("views.home"))
    return render_template("login.html")


@views.route("/signup")
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("views.home"))
    return render_template("signup.html")


# ─── Protected Pages ─────────────────────────────────────────
@views.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)


@views.route("/cart")
@login_required
def cart():
    items = (
        CartItem.query
        .filter_by(user_id=current_user.id)
        .join(Product)
        .all()
    )
    subtotal = sum(i.quantity * i.product.price for i in items)
    cart_count = len(items)
    return render_template("cart.html", items=items, subtotal=subtotal, cart_count=cart_count)


@views.route("/favorites")
@login_required
def favorites():
    favs = (
        Favorite.query
        .filter_by(user_id=current_user.id)
        .join(Product)
        .all()
    )
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    return render_template("fav.html", favorites=favs, cart_count=cart_count)


@views.route("/order-history")
@login_required
def order_history():
    orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    return render_template("orderhistory.html", orders=orders, cart_count=cart_count)


@views.route("/rewards")
@login_required
def rewards():
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    return render_template("reward.html", user=current_user, cart_count=cart_count)


# ─── Category Pages ──────────────────────────────────────────
def _category_page(category_slug: str, template: str):
    page     = request.args.get("page", 1, type=int)
    per_page = 12
    sort     = request.args.get("sort", "default")

    query = Product.query.filter_by(category=category_slug, is_active=True)

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "rating":
        query = query.order_by(Product.rating.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count() if current_user.is_authenticated else 0

    # Collect favorite product IDs for the current user
    fav_ids = set()
    if current_user.is_authenticated:
        fav_ids = {
            f.product_id
            for f in Favorite.query.filter_by(user_id=current_user.id).all()
        }

    return render_template(
        template,
        products=pagination.items,
        pagination=pagination,
        sort=sort,
        cart_count=cart_count,
        fav_ids=fav_ids,
    )


@views.route("/categories/clothing")
def clothing():
    return _category_page("clothing", "categories/clothing.html")


@views.route("/categories/beauty")
def beauty():
    return _category_page("beauty", "categories/beauty.html")


@views.route("/categories/sports")
def sports():
    return _category_page("sports", "categories/sports.html")


@views.route("/categories/dining")
def dining():
    return _category_page("dining", "categories/dining.html")


@views.route("/categories/stationery")
def stationery():
    return _category_page("stationery", "categories/stationery.html")
