"""
Test-specific Django settings for AquaMind project.
Used for running tests in CI environments.
"""

import os
from aquamind.settings import *  # noqa

# Use test-specific URL configuration that explicitly includes API routes
ROOT_URLCONF = 'test_urls'

# Allow testserver host in test environment
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# Override database settings for local/CI environment
# Configure for TimescaleDB container
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # Use environment variables or default values from docker-compose
        'NAME': os.getenv('POSTGRES_DB', 'postgres'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        # Use the correct password for the TimescaleDB container
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'aquapass12345'),  
        # Use localhost for CI, container name for dev
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'OPTIONS': {},  # Remove any TimescaleDB-specific options
        'CONN_MAX_AGE': 0,  # Force new connections to test connectivity
        'TEST': {
            'NAME': 'test_aquamind',
        },
    }
}

# Disable TimescaleDB features in tests
TIMESCALE_ENABLED = False

# Use faster password hasher in tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Override REST Framework settings for testing
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        # Use a more permissive setting for tests
        'rest_framework.permissions.AllowAny',
    ],
}

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
