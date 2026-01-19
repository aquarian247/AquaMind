"""Safety helpers for migration scripts.

All migration scripts must write ONLY to the dedicated migration database
(`aquamind_db_migr_dev`). The development database (`aquamind_db`) is reserved
for day-to-day work.

This module enforces that by:
1) Forcing Django's *default* database settings (via env vars) to point at the
   Postgres target in migration_config.json (defaults to aquamind_db_migr_dev).
2) Providing a runtime assertion to fail fast if the default DB is not the
   migration DB.
"""

from __future__ import annotations

import os

from scripts.migration.config import get_postgres_config


def configure_migration_environment(*, config_key: str = "aquamind") -> str:
    """Force Django default DB env vars to point at the migration Postgres DB.

    Returns the expected DB name.
    """
    pg = get_postgres_config(config_key)

    # Force the *default* database settings used by aquamind/settings.py
    os.environ["DB_ENGINE"] = "django.db.backends.postgresql"
    os.environ["DB_NAME"] = pg.database
    os.environ["DB_USER"] = pg.user
    os.environ["DB_PASSWORD"] = pg.password
    os.environ["DB_HOST"] = pg.host
    os.environ["DB_PORT"] = str(pg.port)

    # Helpful marker for logs / debugging.
    os.environ.setdefault("AQUAMIND_MIGRATION_MODE", "1")

    return pg.database


def assert_default_db_is_migration_db(*, expected_db_name: str | None = None) -> None:
    """Fail fast if Django's default DB is not the migration database."""
    from django.db import connections

    expected = expected_db_name or get_postgres_config("aquamind").database
    actual = connections["default"].settings_dict.get("NAME")

    if actual != expected:
        raise RuntimeError(
            "Unsafe database target for migration scripts. "
            f"Expected default DB '{expected}' but got '{actual}'. "
            "Refusing to proceed."
        )
