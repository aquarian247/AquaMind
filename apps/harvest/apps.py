"""App configuration for the harvest domain."""

from django.apps import AppConfig


class HarvestConfig(AppConfig):
    """Default configuration for the harvest app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.harvest"
    verbose_name = "Harvest"
