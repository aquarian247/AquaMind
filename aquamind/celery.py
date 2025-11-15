"""
Celery configuration for AquaMind.

This module configures Celery for asynchronous task processing in AquaMind.
Used primarily for:
- Batch growth assimilation recomputation (Phase 4)
- Background data processing jobs
- Scheduled tasks (via Celery Beat, future)

Setup:
    1. Start Redis: redis-server (default port 6379)
    2. Start Celery worker: celery -A aquamind worker -l info
    3. Monitor tasks: celery -A aquamind inspect active

For development:
    - Broker URL can be configured via CELERY_BROKER_URL env var
    - Result backend via CELERY_RESULT_BACKEND env var
    - Defaults to localhost:6379 if not set

Production considerations:
    - Use Redis Sentinel or clustering for HA
    - Configure task time limits
    - Set up monitoring (Flower, Datadog, etc.)
    - Use multiple workers for horizontal scaling
"""
import os
from celery import Celery

# Set default Django settings module for 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

app = Celery('aquamind')

# Load configuration from Django settings with CELERY_ namespace
# This means all Celery config must be prefixed with CELERY_ in settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps (looks for tasks.py in each app)
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Debug task for testing Celery setup.
    
    Usage:
        from aquamind.celery import debug_task
        debug_task.delay()
    """
    print(f'Request: {self.request!r}')

