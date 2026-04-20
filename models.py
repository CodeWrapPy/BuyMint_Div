from datetime import datetime, timezone
from flask_login import UserMixin
from extensions import db, bcrypt


# BUG FIX #4: datetime.utcnow is deprecated in Python 3.12+ and raises
# DeprecationWarning. All default/onupdate callables now use
# lambda: datetime.now(timezone.utc) which returns a timezone-aware UTC datetime.
def _utcnow():
    return datetime.now(timezone.utc)


# Reward tier thresholds — single source of truth used by both
# update_tier() and any route that needs to know tier boundaries.
# BUG FIX #5: Magic numbers were scattered across models.py and rewards.py
# with no guarantee they'd stay in sync. Now defined once here.
TIER_THRESHOLDS = {
    "Seedling": 0,
    "Sprout":   500,
    "Grove":    2000,
    "Forest":   5000,
}


# ─────────────────────────────────────────────
# User
# ─────────────────────────────────────────────
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    full_name     = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    phone         = db.Column(db.String(20))
    address       = db.Column(db.Text)
    avatar_url    = db.Column(db.String(512))
    reward_points = db.Column(db.Integer, default=0)
    tier          = db.Column(db.String(20), default="Seedling")  # Seedling/Sprout/Grove/Forest
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=_utcnow)

    # Relationships
    cart_items = db.relationship("CartItem",       backref="user", lazy="dynamic", cascade="all, delete-orphan")
    favorites  = db.relationship("Favorite",       backref="user", lazy="dynamic", cascade="all, delete-orphan")
    orders     = db.relationship("Order",          backref="user", lazy="dynamic")
    messages   = db.relationship("ContactMessage", backref="user", lazy="dynamic")

    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    def update_tier(self):
        # Uses TIER_THRESHOLDS so thresholds stay in sync with rewards.py.
        pts = self.reward_points
        if pts >= TIER_THRESHOLDS["Forest"]:
            self.tier = "Forest"
        elif pts >= TIER_THRESHOLDS["Grove"]:
            self.tier = "Grove"
        elif pts >= TIER_THRESHOLDS["Sprout"]:
            self.tier = "Sprout"
        else:
            self.tier = "Seedling"

    def to_dict(self):
        return {
            "id":           self.id,
            "full_name":    self.full_name,
            "email":        self.email,
            "phone":        self.phone,
            "address":      self.address,
            "avatar_url":   self.avatar_url,
            "reward_points": self.reward_points,
            "tier":         self.tier,
            "created_at":   self.created_at.isoformat(),
        }

    def __repr__(self):
        return f"<User {self.email}>"


# ─────────────────────────────────────────────
# Product
# ─────────────────────────────────────────────
class Product(db.Model):
    __tablename__ = "products"

    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(200), nullable=False)
    description    = db.Column(db.Text)
    price          = db.Column(db.Float, nullable=False)
    original_price = db.Column(db.Float)   # for showing strikethrough price
    category       = db.Column(db.String(60), nullable=False, index=True)
    image_url      = db.Column(db.String(512))
    is_organic     = db.Column(db.Boolean, default=True)
    rating         = db.Column(db.Float, default=4.5)
    review_count   = db.Column(db.Integer, default=0)
    stock          = db.Column(db.Integer, default=100)
    is_active      = db.Column(db.Boolean, default=True)
    created_at     = db.Column(db.DateTime, default=_utcnow)

    cart_items  = db.relationship("CartItem",  backref="product", lazy="dynamic")
    favorites   = db.relationship("Favorite",  backref="product", lazy="dynamic")
    order_items = db.relationship("OrderItem", backref="product", lazy="dynamic")

    def to_dict(self):
        return {
            "id":             self.id,
            "name":           self.name,
            "description":    self.description,
            "price":          self.price,
            "original_price": self.original_price,
            "category":       self.category,
            "image_url":      self.image_url,
            "is_organic":     self.is_organic,
            "rating":         self.rating,
            "review_count":   self.review_count,
            "stock":          self.stock,
        }

    def __repr__(self):
        return f"<Product {self.name}>"


# ─────────────────────────────────────────────
# Cart Item
# ─────────────────────────────────────────────
class CartItem(db.Model):
    __tablename__ = "cart_items"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity   = db.Column(db.Integer, default=1, nullable=False)
    added_at   = db.Column(db.DateTime, default=_utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),
    )

    def to_dict(self):
        return {
            "id":         self.id,
            "product_id": self.product_id,
            "quantity":   self.quantity,
            "product":    self.product.to_dict(),
            "subtotal":   round(self.quantity * self.product.price, 2),
        }


# ─────────────────────────────────────────────
# Favorite
# ─────────────────────────────────────────────
class Favorite(db.Model):
    __tablename__ = "favorites"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    saved_at   = db.Column(db.DateTime, default=_utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_fav_user_product"),
    )

    def to_dict(self):
        return {
            "id":       self.id,
            "product":  self.product.to_dict(),
            "saved_at": self.saved_at.isoformat(),
        }


# ─────────────────────────────────────────────
# Order + OrderItem
# ─────────────────────────────────────────────
class Order(db.Model):
    __tablename__ = "orders"

    STATUS_CHOICES = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    total_amount     = db.Column(db.Float, nullable=False)
    discount_amount  = db.Column(db.Float, default=0.0)
    delivery_fee     = db.Column(db.Float, default=0.0)
    status           = db.Column(db.String(20), default="pending")
    shipping_address = db.Column(db.Text)
    promo_code       = db.Column(db.String(30))
    created_at       = db.Column(db.DateTime, default=_utcnow)
    # BUG FIX #6: onupdate=datetime.utcnow → _utcnow (timezone-aware, not deprecated).
    updated_at       = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    items = db.relationship("OrderItem", backref="order", lazy="joined", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id":               self.id,
            "total_amount":     self.total_amount,
            "discount_amount":  self.discount_amount,
            "delivery_fee":     self.delivery_fee,
            "status":           self.status,
            "shipping_address": self.shipping_address,
            "promo_code":       self.promo_code,
            "created_at":       self.created_at.isoformat(),
            "items":            [i.to_dict() for i in self.items],
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity   = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)   # snapshot at purchase time

    def to_dict(self):
        return {
            "id":         self.id,
            "product_id": self.product_id,
            "product":    self.product.to_dict() if self.product else {},
            "quantity":   self.quantity,
            "unit_price": self.unit_price,
            "subtotal":   round(self.quantity * self.unit_price, 2),
        }


# ─────────────────────────────────────────────
# Contact Message
# ─────────────────────────────────────────────
class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)   # nullable for guests
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(254), nullable=False)
    subject    = db.Column(db.String(200))
    message    = db.Column(db.Text, nullable=False)
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "subject":    self.subject,
            "message":    self.message,
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────────
# Promo Code
# ─────────────────────────────────────────────
class PromoCode(db.Model):
    __tablename__ = "promo_codes"

    id             = db.Column(db.Integer, primary_key=True)
    code           = db.Column(db.String(30), unique=True, nullable=False, index=True)
    discount_type  = db.Column(db.String(10), default="percent")   # percent | fixed
    discount_value = db.Column(db.Float, nullable=False)
    min_order_value = db.Column(db.Float, default=0.0)
    max_uses       = db.Column(db.Integer, default=1000)
    used_count     = db.Column(db.Integer, default=0)
    is_active      = db.Column(db.Boolean, default=True)
    expires_at     = db.Column(db.DateTime, nullable=True)

    def is_valid(self, subtotal: float) -> tuple[bool, str]:
        """
        Centralised validity check used by both validate_promo and checkout.
        Returns (is_valid, error_message). error_message is "" when valid.
        BUG FIX #7: Previously, checkout didn't recheck expires_at or max_uses,
        so an expired/exhausted promo still applied a discount at checkout.
        """
        from datetime import datetime, timezone
        if not self.is_active:
            return False, "Invalid or expired promo code."
        if self.expires_at and self.expires_at < datetime.now(timezone.utc):
            return False, "This promo code has expired."
        if self.used_count >= self.max_uses:
            return False, "This promo code has reached its usage limit."
        if subtotal < self.min_order_value:
            return False, f"Minimum order of ₹{self.min_order_value:.0f} required for this code."
        return True, ""

    def compute_discount(self, subtotal: float) -> float:
        if self.discount_type == "percent":
            return round(subtotal * self.discount_value / 100, 2)
        return round(min(self.discount_value, subtotal), 2)

    def to_dict(self):
        return {
            "code":           self.code,
            "discount_type":  self.discount_type,
            "discount_value": self.discount_value,
        }
