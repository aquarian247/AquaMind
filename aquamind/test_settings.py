"""
Test settings for AquaMind project.

This module contains Django settings specifically for test environments.
It inherits from the main settings but uses SQLite instead of PostgreSQL/TimescaleDB
to enable faster and easier testing without requiring a fully functional TimescaleDB setup.
This configuration is for unit testing only - TimescaleDB features should be tested manually.
"""

from .settings import *  # noqa

# Use SQLite for testing instead of PostgreSQL with TimescaleDB
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
    }
}

# Disable TimescaleDB for testing
USE_TIMESCALEDB = False

# Use our custom test runner that avoids TimescaleDB operations
TEST_RUNNER = 'apps.core.test_runner.TimescaleDBTestRunner'
