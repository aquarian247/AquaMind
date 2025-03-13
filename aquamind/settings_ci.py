"""
CI-specific Django settings for AquaMind project.
This file extends the base settings and overrides database configuration for CI environments.
"""

from .settings import *  # noqa

# Override database settings for CI environment
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
