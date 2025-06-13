"""
Broodstock app configuration.
"""

from django.apps import AppConfig


class BroodstockConfig(AppConfig):
    """Configuration for the Broodstock Management app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.broodstock'
    verbose_name = 'Broodstock Management'
    
    def ready(self):
        """Import signal handlers when the app is ready."""
        # Import signals here if needed in the future
        pass
