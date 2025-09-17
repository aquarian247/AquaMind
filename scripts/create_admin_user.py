#!/usr/bin/env python
"""
Admin User Creation Script

This script creates an admin user for testing the AquaMind system.

Usage:
    python manage.py shell < scripts/create_admin_user.py

The script will create a user with:
- Username: admin
- Email: admin@aquamind.test
- Password: admin123
- Superuser privileges
"""

import os
import django
import sys
from django.contrib.auth import get_user_model

# Initialize Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
django.setup()

User = get_user_model()

def create_admin_user():
    """Create admin user for testing"""

    admin_username = "admin"
    admin_email = "admin@aquamind.test"
    admin_password = "admin123"

    print("Creating admin user...")
    print(f"Username: {admin_username}")
    print(f"Email: {admin_email}")
    print(f"Password: {admin_password}")
    print()

    # Check if user already exists
    if User.objects.filter(username=admin_username).exists():
        print(f"⚠️  User '{admin_username}' already exists!")
        return

    # Create the admin user
    try:
        user = User.objects.create_superuser(
            username=admin_username,
            email=admin_email,
            password=admin_password
        )
        print("✅ Admin user created successfully!")
        print(f"   User ID: {user.id}")
        print(f"   Superuser: {user.is_superuser}")
        print(f"   Staff: {user.is_staff}")
        print()
        print("🔐 You can now log in with:")
        print(f"   Username: {admin_username}")
        print(f"   Password: {admin_password}")

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")

if __name__ == "__main__":
    create_admin_user()
