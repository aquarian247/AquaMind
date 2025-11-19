"""Top-level package for the AquaMind Django project."""

# Import Celery app to ensure it's always imported when Django starts
# This makes @shared_task decorator work properly
from .celery import app as celery_app

__all__ = ('celery_app',)
