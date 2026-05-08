"""
routes/admin.py
Admin panel views — all routes require is_admin=True.
"""

from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, abort, request
from flask_login import login_required, current_user
from models import User, Product, Order, ContactMessage, PromoCode, OrderItem
from extensions import db
from sqlalchemy import func
from datetime import datetime, timezone, timedelta

admin = Blueprint("admin", __name__, url_prefix="/admin")


# ── Admin guard decorator ─────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ─────────────────────────────────────────────────
@admin.route("/")
@login_required
@admin_required
def dashboard():
    # Key metrics
    total_users    = User.query.count()
    total_products = Product.query.count()
    total_orders   = Order.query.count()
    total_revenue  = db.session.query(func.sum(Order.total_amount)).scalar() or 0.0

    # New this month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_month   = User.query.filter(User.created_at >= month_start).count()
    new_orders_month  = Order.query.filter(Order.created_at >= month_start).count()
    revenue_month     = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= month_start
    ).scalar() or 0.0

    # Unread messages
    unread_messages = ContactMessage.query.filter_by(is_read=False).count()

    # Recent orders (latest 8)
    recent_orders = (
        Order.query
        .order_by(Order.created_at.desc())
        .limit(8)
        .all()
    )

    # Order status breakdown
    status_counts = dict(
        db.session.query(Order.status, func.count(Order.id))
        .group_by(Order.status)
        .all()
    )

    # Revenue last 7 days (for mini chart data)
    chart_labels = []
    chart_data   = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        rev = db.session.query(func.sum(Order.total_amount)).filter(
            Order.created_at >= day_start,
            Order.created_at <= day_end
        ).scalar() or 0.0
        chart_labels.append(day.strftime("%d %b"))
        chart_data.append(round(rev, 2))

    # Top products by revenue
    top_products = (
        db.session.query(
            Product.name,
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
            func.sum(OrderItem.quantity).label("units_sold"),
        )
        .join(OrderItem, Product.id == OrderItem.product_id)
        .group_by(Product.id)
        .order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc())
        .limit(5)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        new_users_month=new_users_month,
        new_orders_month=new_orders_month,
        revenue_month=revenue_month,
        unread_messages=unread_messages,
        recent_orders=recent_orders,
        status_counts=status_counts,
        chart_labels=chart_labels,
        chart_data=chart_data,
        top_products=top_products,
    )


# ── Users Management ──────────────────────────────────────────
@admin.route("/users")
@login_required
@admin_required
def users():
    page     = request.args.get("page", 1, type=int)
    search   = request.args.get("q", "")
    per_page = 15

    query = User.query
    if search:
        query = query.filter(
            db.or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
            )
        )
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template("admin/users.html", pagination=pagination, search=search)


# ── Products Management ───────────────────────────────────────
@admin.route("/products")
@login_required
@admin_required
def products():
    page     = request.args.get("page", 1, type=int)
    search   = request.args.get("q", "")
    category = request.args.get("category", "")
    per_page = 15

    query = Product.query
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if category:
        query = query.filter_by(category=category)
    pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template(
        "admin/products.html",
        pagination=pagination,
        search=search,
        selected_category=category,
        categories=categories,
    )


# ── Orders Management ─────────────────────────────────────────
@admin.route("/orders")
@login_required
@admin_required
def orders():
    page     = request.args.get("page", 1, type=int)
    status   = request.args.get("status", "")
    per_page = 15

    query = Order.query
    if status:
        query = query.filter_by(status=status)
    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template(
        "admin/orders.html",
        pagination=pagination,
        selected_status=status,
        status_choices=Order.STATUS_CHOICES,
    )


# ── Messages Management ───────────────────────────────────────
@admin.route("/messages")
@login_required
@admin_required
def messages():
    page     = request.args.get("page", 1, type=int)
    unread   = request.args.get("unread", "")
    per_page = 15

    query = ContactMessage.query
    if unread == "1":
        query = query.filter_by(is_read=False)
    pagination = query.order_by(ContactMessage.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template("admin/messages.html", pagination=pagination, unread=unread)


# ── Promo Codes Management ────────────────────────────────────
@admin.route("/promos")
@login_required
@admin_required
def promos():
    promos_list = PromoCode.query.order_by(PromoCode.id.desc()).all()
    return render_template("admin/promos.html", promos=promos_list)
