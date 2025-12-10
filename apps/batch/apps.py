from django.apps import AppConfig


class BatchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.batch'
    verbose_name = 'Batch Management'

    def ready(self):
        """Import signal handlers when the app is ready."""
        import apps.batch.services.growth_service  # noqa
        import apps.batch.signals  # noqa - Register batch lifecycle signals
        
        # Register PlannedActivity completion signal for growth assimilation
        # This enables the backward flow: completed activities anchor daily states
        from apps.batch.signals import register_planning_signals
        register_planning_signals()