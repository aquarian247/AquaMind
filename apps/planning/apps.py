from django.apps import AppConfig


class PlanningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.planning'
    verbose_name = 'Operational Planning'
    
    def ready(self):
        import apps.planning.signals  # noqa






