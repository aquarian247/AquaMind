from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory'
    verbose_name = 'Feed and Inventory Management'
    
    def ready(self):
        """Import signal handlers when the app is ready."""
        import apps.inventory.signals  # noqa - Register FCR auto-calculation signals