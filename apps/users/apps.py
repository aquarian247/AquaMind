from django.apps import AppConfig
from django.contrib.auth import get_user_model
from simple_history import register


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'User Management'

    def ready(self):
        """
        Import and register signals when the app is ready.

        This ensures that our signal handlers are connected when the app starts.
        Also registers the Django User model for history tracking.
        """
        import apps.users.signals

        # Register User model for history tracking
        register(get_user_model())
