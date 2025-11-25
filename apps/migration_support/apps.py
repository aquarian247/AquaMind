from django.apps import AppConfig


class MigrationSupportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.migration_support'
    verbose_name = 'Migration Support'
