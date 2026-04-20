"""
seed.py – Populate a fresh BuyMint database with sample data.
Run standalone:  python seed.py
Or called automatically by app.py on first boot.
"""
from extensions import db
from models import Product, PromoCode


PRODUCTS = [
    # ── Clothing ───────────────────────────────────────────
    {"name": "Organic Cotton Tee",        "category": "clothing",   "price": 799,  "original_price": 999,  "description": "Soft, breathable 100% GOTS-certified organic cotton t-shirt.", "rating": 4.7, "stock": 80, "image_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400"},
    {"name": "Hemp Linen Trousers",       "category": "clothing",   "price": 1499, "original_price": 1899, "description": "Lightweight hemp-linen blend trousers for everyday wear.", "rating": 4.5, "stock": 45, "image_url": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400"},
    {"name": "Bamboo Yoga Leggings",      "category": "clothing",   "price": 1199, "original_price": None, "description": "Ultra-soft bamboo fabric with 4-way stretch.", "rating": 4.8, "stock": 60, "image_url": "https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=400"},
    {"name": "Recycled Denim Jacket",     "category": "clothing",   "price": 2499, "original_price": 2999, "description": "Classic jacket crafted from 100% recycled denim.", "rating": 4.6, "stock": 30, "image_url": "https://images.unsplash.com/photo-1551537482-f2075a1d41f2?w=400"},
    {"name": "Tencel Floral Dress",       "category": "clothing",   "price": 1799, "original_price": None, "description": "Breathable Tencel midi dress with botanical print.", "rating": 4.7, "stock": 50, "image_url": "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=400"},
    {"name": "Organic Merino Hoodie",     "category": "clothing",   "price": 2199, "original_price": 2599, "description": "Warm, itch-free merino wool hoodie for cooler days.", "rating": 4.9, "stock": 25, "image_url": "https://images.unsplash.com/photo-1556821840-3a63f15732ce?w=400"},

    # ── Beauty ────────────────────────────────────────────
    {"name": "Rose Hip Face Oil",         "category": "beauty",     "price": 649,  "original_price": 849,  "description": "Cold-pressed rosehip seed oil for radiant skin.", "rating": 4.8, "stock": 120, "image_url": "https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?w=400"},
    {"name": "Charcoal Clay Mask",        "category": "beauty",     "price": 449,  "original_price": None, "description": "Detoxifying activated charcoal & kaolin clay mask.", "rating": 4.6, "stock": 90, "image_url": "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=400"},
    {"name": "Shea Butter Body Lotion",   "category": "beauty",     "price": 399,  "original_price": 499,  "description": "Rich, creamy body lotion with unrefined shea butter.", "rating": 4.7, "stock": 150, "image_url": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=400"},
    {"name": "Neem Herbal Shampoo",       "category": "beauty",     "price": 349,  "original_price": None, "description": "Sulfate-free neem & bhringraj shampoo for healthy scalp.", "rating": 4.5, "stock": 100, "image_url": "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=400"},
    {"name": "Argan Oil Serum",           "category": "beauty",     "price": 799,  "original_price": 999,  "description": "Lightweight argan oil serum for frizz-free, shiny hair.", "rating": 4.8, "stock": 70, "image_url": "https://images.unsplash.com/photo-1619451334792-150fd785ee74?w=400"},
    {"name": "Bamboo Charcoal Toothbrush","category": "beauty",     "price": 199,  "original_price": None, "description": "Biodegradable bamboo handle with charcoal-infused bristles.", "rating": 4.4, "stock": 200, "image_url": "https://images.unsplash.com/photo-1607613009820-a29f7bb81c04?w=400"},

    # ── Sports ────────────────────────────────────────────
    {"name": "Cork Yoga Mat",             "category": "sports",     "price": 1999, "original_price": 2499, "description": "Natural cork & rubber yoga mat with anti-slip surface.", "rating": 4.9, "stock": 40, "image_url": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=400"},
    {"name": "Recycled PET Water Bottle", "category": "sports",     "price": 599,  "original_price": None, "description": "BPA-free 750ml bottle made from recycled plastic.", "rating": 4.6, "stock": 160, "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400"},
    {"name": "Organic Cotton Gym Towel",  "category": "sports",     "price": 449,  "original_price": 549,  "description": "Quick-dry organic cotton gym & yoga towel.", "rating": 4.5, "stock": 110, "image_url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400"},
    {"name": "Natural Rubber Jump Rope",  "category": "sports",     "price": 349,  "original_price": None, "description": "Speed jump rope with natural rubber handles.", "rating": 4.4, "stock": 80, "image_url": "https://images.unsplash.com/photo-1591384640699-9a85bd036da2?w=400"},
    {"name": "Bamboo Tennis Racket",      "category": "sports",     "price": 3499, "original_price": 3999, "description": "Lightweight, high-flex bamboo composite tennis racket.", "rating": 4.7, "stock": 20, "image_url": "https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?w=400"},
    {"name": "Hemp Resistance Bands Set", "category": "sports",     "price": 699,  "original_price": 849,  "description": "Set of 5 natural latex-free hemp resistance bands.", "rating": 4.8, "stock": 95, "image_url": "https://images.unsplash.com/photo-1598289431512-b97b0917affc?w=400"},

    # ── Dining ────────────────────────────────────────────
    {"name": "Cold-Pressed Olive Oil",    "category": "dining",     "price": 899,  "original_price": 1099, "description": "Extra virgin, single-origin cold-pressed olive oil (500ml).", "rating": 4.9, "stock": 60, "image_url": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400"},
    {"name": "Raw Wildflower Honey",      "category": "dining",     "price": 549,  "original_price": None, "description": "Unfiltered, unheated raw wildflower honey (350g).", "rating": 4.8, "stock": 85, "image_url": "https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=400"},
    {"name": "Organic Matcha Powder",     "category": "dining",     "price": 699,  "original_price": 799,  "description": "Ceremonial-grade organic matcha from Uji, Japan (50g).", "rating": 4.7, "stock": 70, "image_url": "https://images.unsplash.com/photo-1536256263959-770b48d82b0a?w=400"},
    {"name": "Sprouted Brown Rice",       "category": "dining",     "price": 299,  "original_price": None, "description": "Pre-sprouted organic brown rice for better nutrition (1kg).", "rating": 4.5, "stock": 120, "image_url": "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400"},
    {"name": "Dark Chocolate 85%",        "category": "dining",     "price": 349,  "original_price": 449,  "description": "Bean-to-bar single-origin 85% dark chocolate (80g).", "rating": 4.8, "stock": 100, "image_url": "https://images.unsplash.com/photo-1606312619070-d48b5c7a77d4?w=400"},
    {"name": "Herbal Detox Tea Blend",    "category": "dining",     "price": 399,  "original_price": None, "description": "14-herb organic detox blend — loose leaf (100g).", "rating": 4.6, "stock": 90, "image_url": "https://images.unsplash.com/photo-1563822249366-3efb23b8e0c9?w=400"},

    # ── Stationery ───────────────────────────────────────
    {"name": "Recycled Kraft Notebook",   "category": "stationery", "price": 299,  "original_price": 349,  "description": "A5 lined notebook with 100% recycled kraft cover (200 pages).", "rating": 4.7, "stock": 130, "image_url": "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=400"},
    {"name": "Seed Paper Gift Cards",     "category": "stationery", "price": 149,  "original_price": None, "description": "Pack of 10 plantable seed paper greeting cards.", "rating": 4.9, "stock": 200, "image_url": "https://images.unsplash.com/photo-1616628188524-b8d37d33b430?w=400"},
    {"name": "Bamboo Ballpoint Pens",     "category": "stationery", "price": 199,  "original_price": 249,  "description": "Set of 5 smooth-writing pens with bamboo barrels.", "rating": 4.5, "stock": 180, "image_url": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=400"},
    {"name": "Stone Paper Sketchbook",    "category": "stationery", "price": 499,  "original_price": None, "description": "Waterproof, tear-resistant stone paper sketchbook (A4).", "rating": 4.8, "stock": 55, "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400"},
    {"name": "Soy Ink Highlighter Set",   "category": "stationery", "price": 249,  "original_price": 299,  "description": "6 vivid soy-based ink highlighters in pastel tones.", "rating": 4.6, "stock": 140, "image_url": "https://images.unsplash.com/photo-1513201099705-a9746072f043?w=400"},
    {"name": "Cork Board Planner Kit",    "category": "stationery", "price": 799,  "original_price": 999,  "description": "Desk-size cork board with monthly planner pad & pushpins.", "rating": 4.7, "stock": 45, "image_url": "https://images.unsplash.com/photo-1506784365847-bbad939e9501?w=400"},
]

PROMOS = [
    {"code": "MINT20",     "discount_type": "percent", "discount_value": 20, "min_order_value": 500,  "max_uses": 1000},
    {"code": "FREESHIP",   "discount_type": "fixed",   "discount_value": 49, "min_order_value": 300,  "max_uses": 500},
    {"code": "ORGANIC10",  "discount_type": "percent", "discount_value": 10, "min_order_value": 0,    "max_uses": 9999},
    {"code": "NEWLEAF15",  "discount_type": "percent", "discount_value": 15, "min_order_value": 800,  "max_uses": 200},
    {"code": "FLAT100",    "discount_type": "fixed",   "discount_value": 100,"min_order_value": 1000, "max_uses": 300},
]


def run_seed():
    for p in PRODUCTS:
        product = Product(
            name           = p["name"],
            category       = p["category"],
            price          = p["price"],
            original_price = p.get("original_price"),
            description    = p["description"],
            rating         = p.get("rating", 4.5),
            stock          = p.get("stock", 100),
            image_url      = p.get("image_url"),
            is_organic     = True,
            is_active      = True,
        )
        db.session.add(product)

    for pr in PROMOS:
        promo = PromoCode(
            code            = pr["code"],
            discount_type   = pr["discount_type"],
            discount_value  = pr["discount_value"],
            min_order_value = pr["min_order_value"],
            max_uses        = pr["max_uses"],
            is_active       = True,
        )
        db.session.add(promo)

    db.session.commit()
    print(f"✅  Seeded {len(PRODUCTS)} products and {len(PROMOS)} promo codes.")


if __name__ == "__main__":
    from app import create_app
    with create_app().app_context():
        run_seed()
