from django.apps import AppConfig


class FinanceCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.finance_core"
    verbose_name = "Finance Core"

    def ready(self):
        import apps.finance_core.signals  # noqa
