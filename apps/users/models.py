from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver





# Organization structure choices for role-based access control
class Geography(models.TextChoices):
    """Geographic regions for role-based access control."""
    FAROE_ISLANDS = 'FO', _('Faroe Islands')
    SCOTLAND = 'SC', _('Scotland')
    ALL = 'ALL', _('All Geographies')

class Subsidiary(models.TextChoices):
    """Subsidiary divisions for role-based access control."""
    BROODSTOCK = 'BS', _('Broodstock')
    FRESHWATER = 'FW', _('Freshwater')
    FARMING = 'FM', _('Farming')
    LOGISTICS = 'LG', _('Logistics')
    ALL = 'ALL', _('All Subsidiaries')

class Role(models.TextChoices):
    """User roles for role-based access control."""
    ADMIN = 'ADMIN', _('Administrator')
    MANAGER = 'MGR', _('Manager')
    OPERATOR = 'OPR', _('Operator')
    VETERINARIAN = 'VET', _('Veterinarian')
    QA = 'QA', _('Quality Assurance')
    FINANCE = 'FIN', _('Finance')
    VIEWER = 'VIEW', _('Viewer')


class UserProfile(models.Model):
    """
    Extended profile information for users.
    
    Stores additional user information that is not essential to authentication
    but provides context for user preferences and settings. Also includes
    role-based access control fields moved from the custom User model.
    """
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    
    # Personal information
    full_name = models.CharField(_('full name'), max_length=150, blank=True)
    phone = models.CharField(_('phone number'), max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True
    )
    job_title = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    
    # Role-based access control fields
    geography = models.CharField(
        max_length=3,
        choices=Geography.choices,
        default=Geography.ALL,
        help_text='Geographic region access level'
    )
    
    subsidiary = models.CharField(
        max_length=3,
        choices=Subsidiary.choices,
        default=Subsidiary.ALL,
        help_text='Subsidiary access level'
    )
    
    role = models.CharField(
        max_length=5,
        choices=Role.choices,
        default=Role.VIEWER,
        help_text='User role and permission level'
    )
    
    # User preferences
    language_preference = models.CharField(
        max_length=5,
        choices=[('en', _('English')), ('fo', _('Faroese')), ('da', _('Danish'))],
        default='en'
    )
    
    date_format_preference = models.CharField(
        max_length=10,
        choices=[('DMY', _('DD/MM/YYYY')), ('MDY', _('MM/DD/YYYY')), ('YMD', _('YYYY-MM-DD'))],
        default='DMY'
    )
    
    # Date and metadata fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    def has_geography_access(self, geography):
        """Check if user has access to a specific geography."""
        return self.user.is_superuser or self.geography == Geography.ALL or self.geography == geography
    
    def has_subsidiary_access(self, subsidiary):
        """Check if user has access to a specific subsidiary."""
        return self.user.is_superuser or self.subsidiary == Subsidiary.ALL or self.subsidiary == subsidiary
    
    class Meta:
        verbose_name = _('user profile')
        verbose_name_plural = _('user profiles')


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler to automatically create a UserProfile when a User is created.
    
    This ensures that every user in the system has an associated profile with
    the necessary role-based access control fields and user preferences.
    
    Args:
        sender: The model class (User)
        instance: The actual user instance being saved
        created: Boolean flag indicating if this is a new user
        **kwargs: Additional keyword arguments
    """
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal handler to save a UserProfile when the associated User is saved.
    
    Ensures profile changes are persisted when user data is updated.
    
    Args:
        sender: The model class (User)
        instance: The actual user instance being saved
        **kwargs: Additional keyword arguments
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()