from django.apps import AppConfig


class BatchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.batch'
    verbose_name = 'Batch Management'

    def ready(self):
        """Import signal handlers when the app is ready."""
        import apps.batch.services.growth_service  # noqa
        import apps.batch.signals  # noqa - Register batch lifecycle signals
