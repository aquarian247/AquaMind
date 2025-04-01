"""
PostgreSQL test settings for AquaMind project.

This module contains Django settings specifically for test environments using PostgreSQL.
It inherits from the main settings and uses PostgreSQL with TimescaleDB
to enable proper testing of TimescaleDB-specific features.
"""

from .settings import *  # noqa

# Use the same PostgreSQL settings but with a test database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aquamind_test_db',
        'USER': 'postgres',
        'PASSWORD': 'adminpass1234',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'options': '-c search_path=public'
        }
    }
}

# Enable TimescaleDB for testing
USE_TIMESCALEDB = True

# Use our custom test runner
TEST_RUNNER = 'apps.core.test_runner.TimescaleDBTestRunner'
