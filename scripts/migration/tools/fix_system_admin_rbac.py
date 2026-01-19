#!/usr/bin/env python3
# flake8: noqa
"""Restore system_admin RBAC access in migration DB."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
os.environ.setdefault("SKIP_CELERY_SIGNALS", "1")

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db

configure_migration_environment()

import django

django.setup()
assert_default_db_is_migration_db()

from django.contrib.auth import get_user_model

from apps.users.models import UserProfile, Role, Geography, Subsidiary


def main() -> int:
    User = get_user_model()
    user = User.objects.filter(username="system_admin").first()
    if not user:
        raise SystemExit("system_admin user not found")

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = Role.ADMIN
    profile.geography = Geography.ALL
    profile.subsidiary = Subsidiary.ALL
    profile.save()

    print(
        f"Updated system_admin profile: role={profile.role}, "
        f"geography={profile.geography}, subsidiary={profile.subsidiary}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
