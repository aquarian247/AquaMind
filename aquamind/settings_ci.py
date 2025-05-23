"""
CI-specific Django settings for AquaMind project.
This file extends the base settings and overrides database configuration for CI environments.
"""

from .settings import *  # noqa

# Override database settings for CI environment
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Use in-memory SQLite database for tests
    }
}

# Ensure TEST_RUNNER from main settings is not overriding CI database behavior if it implies PostgreSQL
# If TimescaleDBTestRunner specifically requires PostgreSQL, this might need further adjustment
# For now, let's assume standard Django testing with SQLite is the goal for CI.
# If the custom runner has specific logic for CI, it should respect these settings.
TIMESCALE_ENABLED = False

# Speed up tests by using a weaker password hasher in CI if appropriate
# PASSWORD_HASHERS = [
#     'django.contrib.auth.hashers.MD5PasswordHasher',
# ]
