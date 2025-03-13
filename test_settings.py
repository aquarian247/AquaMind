"""
Test-specific Django settings for AquaMind project.
Used for running tests in CI environments.
"""

import os
from aquamind.settings import *  # noqa

# Use test-specific URL configuration that explicitly includes API routes
ROOT_URLCONF = 'test_urls'

# Override database settings for CI environment
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'postgres'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'OPTIONS': {},  # Remove any TimescaleDB-specific options
    }
}

# Disable TimescaleDB features in tests
TIMESCALE_ENABLED = False

# Use faster password hasher in tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable logging during tests to reduce noise
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['null'],
            'level': 'CRITICAL',
        },
    },
}
