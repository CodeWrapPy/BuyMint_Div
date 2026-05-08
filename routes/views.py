from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Product, Order, CartItem, Favorite, ContactMessage
from extensions import db
from sqlalchemy import func
from datetime import datetime, timezone, timedelta

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


@views.route("/dashboard")
@login_required
def dashboard():
    """User personal dashboard — stats, orders, activity."""
    # Cart & favorites counts
    cart_count  = CartItem.query.filter_by(user_id=current_user.id).count()
    fav_count   = Favorite.query.filter_by(user_id=current_user.id).count()

    # Orders overview
    all_orders      = Order.query.filter_by(user_id=current_user.id).all()
    total_orders    = len(all_orders)
    total_spent     = sum(o.total_amount for o in all_orders)
    pending_orders  = sum(1 for o in all_orders if o.status in ("pending", "confirmed", "processing", "shipped"))

    # Recent orders (last 5)
    recent_orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )

    # Spending last 6 months for chart
    now = datetime.now(timezone.utc)
    chart_labels = []
    chart_data   = []
    for i in range(5, -1, -1):
        month = now - timedelta(days=30 * i)
        m_start = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i == 0:
            m_end = now
        else:
            next_m = (m_start.replace(month=m_start.month % 12 + 1) if m_start.month < 12
                      else m_start.replace(year=m_start.year + 1, month=1))
            m_end = next_m - timedelta(seconds=1)
        spent = db.session.query(func.sum(Order.total_amount)).filter(
            Order.user_id == current_user.id,
            Order.created_at >= m_start,
            Order.created_at <= m_end,
        ).scalar() or 0.0
        chart_labels.append(month.strftime("%b"))
        chart_data.append(round(spent, 2))

    # Tier progress
    from models import TIER_THRESHOLDS
    tier_order  = ["Seedling", "Sprout", "Grove", "Forest"]
    curr_tier   = current_user.tier
    curr_idx    = tier_order.index(curr_tier)
    curr_thresh = TIER_THRESHOLDS[curr_tier]
    next_tier   = tier_order[curr_idx + 1] if curr_idx < len(tier_order) - 1 else None
    next_thresh = TIER_THRESHOLDS[next_tier] if next_tier else None
    if next_thresh:
        pts_in_tier = current_user.reward_points - curr_thresh
        pts_needed  = next_thresh - curr_thresh
        pts_to_next_tier = next_thresh - current_user.reward_points
        tier_pct    = min(100, int(pts_in_tier / pts_needed * 100))
    else:
        tier_pct   = 100
        pts_needed = 0
        pts_to_next_tier = 0

    return render_template(
        "dashboard.html",
        cart_count=cart_count,
        fav_count=fav_count,
        total_orders=total_orders,
        total_spent=total_spent,
        pending_orders=pending_orders,
        recent_orders=recent_orders,
        chart_labels=chart_labels,
        chart_data=chart_data,
        next_tier=next_tier,
        next_thresh=next_thresh,
        tier_pct=tier_pct,
        pts_needed=pts_needed,
        pts_to_next_tier=pts_to_next_tier,
    )


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
