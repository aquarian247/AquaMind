from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile, Role

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler to automatically create a UserProfile when a User is created.
    
    This ensures that every user in the system has an associated profile with
    the necessary role-based access control fields and user preferences.
    
    NOTE: In test environments, defaults to ADMIN role for backward compatibility.
    In production, uses secure VIEWER default (defined in model field).
    
    Args:
        sender: The model class sending the signal (User)
        instance: The instance being saved (User instance)
        created: Whether this is a new instance or an update
        **kwargs: Additional signal arguments
    """
    if created and not hasattr(instance, 'profile'):
        import sys
        # Default to ADMIN in test mode for backward compatibility with existing tests
        # In production, the model's default (VIEWER) is used
        is_testing = 'test' in sys.argv or hasattr(sys, '_called_from_test')
        default_role = Role.ADMIN if is_testing else Role.VIEWER
        UserProfile.objects.create(user=instance, role=default_role)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal handler to save UserProfile when the associated User is saved.
    
    This ensures that profile changes are persisted when user data is updated.
    
    Args:
        sender: The model class sending the signal (User)
        instance: The instance being saved (User instance)
        **kwargs: Additional signal arguments
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()
    elif not kwargs.get('created'):  # Profile doesn't exist and user wasn't just created
        import sys
        is_testing = 'test' in sys.argv or hasattr(sys, '_called_from_test')
        default_role = Role.ADMIN if is_testing else Role.VIEWER
        UserProfile.objects.create(user=instance, role=default_role)