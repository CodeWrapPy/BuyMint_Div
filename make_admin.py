"""
make_admin.py  — Run once to grant admin rights to a user.

Usage:
    python make_admin.py                  # makes the FIRST registered user admin
    python make_admin.py user@example.com # makes a specific user admin
"""

import sys
from app import create_app
from extensions import db
from models import User

app = create_app()

with app.app_context():
    email = sys.argv[1] if len(sys.argv) > 1 else None

    if email:
        user = User.query.filter_by(email=email.strip().lower()).first()
        if not user:
            print(f"❌  No user found with email: {email}")
            sys.exit(1)
    else:
        user = User.query.order_by(User.id.asc()).first()
        if not user:
            print("❌  No users in the database. Run the app first to create an account.")
            sys.exit(1)

    user.is_admin = True
    db.session.commit()
    print(f"✅  {user.full_name} ({user.email}) is now an admin.")
    print(f"    Visit /admin to access the Admin Panel.")
