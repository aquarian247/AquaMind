from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    """
    Inline admin interface for UserProfile model.
    
    Allows editing profile data within the user admin page.
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'


# Extend the default UserAdmin to include the UserProfile inline
admin.site.unregister(User)
@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """
    Admin interface for the User model with UserProfile integration.
    
    Extends the default Django UserAdmin to include the profile data
    as an inline on the user admin page.
    """
    inlines = [UserProfileInline]


@admin.register(UserProfile)
class UserProfileAdmin(SimpleHistoryAdmin):
    """
    Admin interface for the UserProfile model.
    
    Provides a dedicated admin interface for managing user profiles.
    """
    list_display = ('user', 'full_name', 'geography', 'subsidiary', 'role')
    list_filter = ('geography', 'subsidiary', 'role')
    search_fields = ('user__username', 'user__email', 'full_name')
    raw_id_fields = ('user',)