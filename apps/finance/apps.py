"""App configuration for the finance domain."""

from django.apps import AppConfig


class FinanceConfig(AppConfig):
    """Default configuration for the finance app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.finance"
    verbose_name = "Finance"
