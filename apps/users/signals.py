from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler to automatically create a UserProfile when a User is created.
    
    This ensures all users have an associated profile without requiring
    explicit creation in views or serializers.
    
    Args:
        sender: The model class sending the signal (User)
        instance: The instance being saved (User instance)
        created: Whether this is a new instance or an update
        **kwargs: Additional signal arguments
    """
    if created and not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)


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
