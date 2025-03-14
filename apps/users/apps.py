from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'User Management'
    
    def ready(self):
        """
        Import and register signals when the app is ready.
        
        This ensures that our signal handlers are connected when the app starts.
        """
        import apps.users.signals
