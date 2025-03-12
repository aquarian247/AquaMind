from django.apps import AppConfig


class OperationalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.operational'
    verbose_name = 'Operational Planning'
