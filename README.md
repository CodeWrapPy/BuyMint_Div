# 🌿 BuyMint — Flask Backend

A full-stack Flask web application for BuyMint, an organic marketplace. Built with Flask, SQLAlchemy (SQLite), Flask-Login, and Flask-Bcrypt.

---

## 📁 Project Structure

```
buymint/
├── app.py                    ← App factory + entry point
├── config.py                 ← Dev / Prod config classes
├── extensions.py             ← Shared Flask extensions (db, login, bcrypt, csrf)
├── models.py                 ← All SQLAlchemy models
├── seed.py                   ← Seed script (runs automatically on first boot)
├── requirements.txt
├── .env.example              ← Copy to .env and edit
│
├── routes/
│   ├── views.py              ← Page-rendering Blueprints (HTML responses)
│   └── api/
│       ├── auth.py           ← POST /api/auth/register|login|logout, GET /api/auth/me
│       ├── products.py       ← GET /api/products/, /api/products/<id>, /api/products/search
│       ├── cart.py           ← GET/POST/PUT/DELETE /api/cart/, /api/cart/promo, /api/cart/checkout
│       ├── favorites.py      ← GET/POST/DELETE /api/favorites/, /api/favorites/<id>/toggle
│       ├── orders.py         ← GET /api/orders/, /api/orders/<id>
│       ├── profile.py        ← GET/PUT /api/profile/, POST /api/profile/change-password
│       ├── contact.py        ← POST /api/contact/
│       └── rewards.py        ← GET /api/rewards/
│
├── templates/
│   ├── macros.html           ← Shared Jinja2 macros (nav, footer, head, etc.)
│   ├── home.html             ← Public landing page
│   ├── home2.html            ← Authenticated dashboard
│   ├── login.html
│   ├── signup.html
│   ├── cart.html
│   ├── fav.html
│   ├── profile.html
│   ├── orderhistory.html
│   ├── reward.html
│   ├── contact.html
│   ├── aboutus.html
│   ├── faq.html
│   ├── term.html
│   ├── category_base.html    ← Shared product grid template
│   └── categories/
│       ├── clothing.html
│       ├── beauty.html
│       ├── sports.html
│       ├── dining.html
│       └── stationery.html
│
└── static/
    └── js/
        └── buymint.js        ← Shared client JS (Cart, Auth, Favorites, Toast, Forms)
```

---

## ⚙️ Setup & Run

### 1. Clone & navigate
```bash
cd buymint
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env — at minimum change SECRET_KEY
```

### 5. Run the app
```bash
python app.py
```

Open **http://localhost:5000** in your browser.

> **First run:** The database is created automatically (`instance/buymint.db`) and seeded with 30 sample products across 5 categories and 5 promo codes.

---

## 🗄️ Database Models

| Model | Table | Description |
|---|---|---|
| `User` | `users` | Accounts with hashed passwords, rewards tier |
| `Product` | `products` | 30 seeded organic products across 5 categories |
| `CartItem` | `cart_items` | Per-user cart items (quantity, product ref) |
| `Favorite` | `favorites` | Saved products per user |
| `Order` | `orders` | Placed orders with status, discount, delivery |
| `OrderItem` | `order_items` | Line items per order (price snapshot) |
| `ContactMessage` | `contact_messages` | Messages sent via contact form |
| `PromoCode` | `promo_codes` | Discount codes (percent or fixed) |

---

## 🔌 API Reference

All API endpoints return JSON: `{ "success": true, ...data }` or `{ "success": false, "error": "..." }`.
Session-based authentication — log in first.

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | `{ full_name, email, password }` |
| POST | `/api/auth/login` | `{ email, password, remember }` |
| POST | `/api/auth/logout` | Clears session |
| GET  | `/api/auth/me` | Returns current user info |

### Products
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/products/` | List all (supports `?category=&q=&sort=&page=`) |
| GET | `/api/products/<id>` | Single product |
| GET | `/api/products/search?q=` | Search by name |
| GET | `/api/products/category/<slug>` | Products by category |

### Cart
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/cart/` | Full cart with totals |
| POST | `/api/cart/` | `{ product_id, quantity }` |
| PUT | `/api/cart/<item_id>` | `{ quantity }` |
| DELETE | `/api/cart/<item_id>` | Remove one item |
| DELETE | `/api/cart/` | Clear entire cart |
| POST | `/api/cart/promo` | `{ code }` — validate promo |
| POST | `/api/cart/checkout` | `{ shipping_address, promo_code }` |

### Favorites
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/favorites/` | All favourites |
| POST | `/api/favorites/` | `{ product_id }` |
| DELETE | `/api/favorites/<product_id>` | Remove |
| POST | `/api/favorites/<product_id>/toggle` | Toggle |

### Orders
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/orders/` | All user orders |
| GET | `/api/orders/<id>` | Single order |

### Profile
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/profile/` | Get profile |
| PUT | `/api/profile/` | `{ full_name, phone, address }` |
| POST | `/api/profile/change-password` | `{ old_password, new_password }` |

### Other
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/contact/` | `{ name, email, subject, message }` |
| GET  | `/api/rewards/` | Points, tier, progress |

---

## 🎟️ Sample Promo Codes

| Code | Discount | Min. Order |
|---|---|---|
| `MINT20` | 20% off | ₹500 |
| `FREESHIP` | Free delivery (₹49 off) | ₹300 |
| `ORGANIC10` | 10% off | No minimum |
| `NEWLEAF15` | 15% off | ₹800 |
| `FLAT100` | ₹100 off | ₹1000 |

---

## 🧑‍💻 Development Tips

- The SQLite database lives at `instance/buymint.db`. Delete it to reseed from scratch.
- Toggle `FLASK_DEBUG=True` in `.env` for hot-reload and the Werkzeug debugger.
- All API endpoints are CSRF-exempt (they use Flask-Login session cookies — no token needed from JS).
- `buymint.js` exposes `Cart`, `Favorites`, `Auth`, `Toast` globals for use on any page.
