#!/usr/bin/env python
"""
CI Test Token Generator

This script creates a test user and generates an authentication token for use in CI environments,
particularly for Schemathesis API contract testing that requires authenticated requests.

Usage:
    python scripts/ci/create_test_token.py [--settings=aquamind.settings_ci]

The script will print only the token key to stdout, allowing it to be captured in CI:
    TOKEN=$(python scripts/ci/create_test_token.py)

Environment:
    - Requires Django settings with DRF and Token authentication enabled
    - Default settings module: aquamind.settings_ci
"""

import os
import sys
import django
from django.conf import settings
from pathlib import Path


def setup_django():
    """Set up Django environment."""
    # ------------------------------------------------------------------
    # Ensure the project root is on PYTHONPATH so `import aquamind` works
    # scripts/ci/create_test_token.py -> ../../  == project root
    # ------------------------------------------------------------------
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Allow settings module to be specified as argument
    settings_module = 'aquamind.settings_ci'
    for arg in sys.argv[1:]:
        if arg.startswith('--settings='):
            settings_module = arg.split('=', 1)[1]
    
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
    django.setup()


def create_test_user_and_token():
    """Create a test user and generate an authentication token."""
    from django.contrib.auth.models import User
    from rest_framework.authtoken.models import Token
    
    # CI test user credentials
    username = "schemathesis_ci"
    password = "testpass123"
    
    # Get or create the test user
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": "ci@example.com",
            "is_active": True
        }
    )
    
    # Always reset password to ensure it's correct
    user.set_password(password)
    user.save()
    
    # Get or create token
    token, _ = Token.objects.get_or_create(user=user)
    
    # Print only the token key (for capture in CI)
    print(token.key)


if __name__ == "__main__":
    setup_django()
    create_test_user_and_token()
