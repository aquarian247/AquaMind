from django.apps import AppConfig


class HealthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.health'
    
    def ready(self):
        """Import signal handlers when the app is ready."""
        import apps.health.signals  # noqa - Register growth assimilation signals