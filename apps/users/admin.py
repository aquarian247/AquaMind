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
    
    # Organize fields into logical sections
    fieldsets = (
        (_('Role & Access'), {
            'fields': ('geography', 'subsidiary', 'role')
        }),
        (_('Operator Location Assignments'), {
            'fields': ('allowed_areas', 'allowed_stations', 'allowed_containers'),
            'description': _('Assign specific areas, stations, or containers to operators. '
                           'Managers and Admins have access to all locations in their geography.'),
            'classes': ('collapse',),
        }),
        (_('Personal Information'), {
            'fields': ('full_name', 'phone', 'profile_picture', 'job_title', 'department')
        }),
        (_('Preferences'), {
            'fields': ('language_preference', 'date_format_preference'),
            'classes': ('collapse',),
        }),
    )
    
    # Horizontal filter for M2M fields (better UX than default select)
    filter_horizontal = ('allowed_areas', 'allowed_stations', 'allowed_containers')


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
    
    Provides a dedicated admin interface for managing user profiles with
    support for operator location assignments.
    """
    list_display = ('user', 'full_name', 'geography', 'subsidiary', 'role', 'location_count')
    list_filter = ('geography', 'subsidiary', 'role')
    search_fields = ('user__username', 'user__email', 'full_name')
    raw_id_fields = ('user',)
    
    fieldsets = (
        (_('User Account'), {
            'fields': ('user',)
        }),
        (_('Role & Access'), {
            'fields': ('geography', 'subsidiary', 'role')
        }),
        (_('Operator Location Assignments'), {
            'fields': ('allowed_areas', 'allowed_stations', 'allowed_containers'),
            'description': _('Assign specific areas, stations, or containers to operators. '
                           'Only relevant for users with OPERATOR role. '
                           'Managers and Admins have access to all locations in their geography.'),
        }),
        (_('Personal Information'), {
            'fields': ('full_name', 'phone', 'profile_picture', 'job_title', 'department')
        }),
        (_('Preferences'), {
            'fields': ('language_preference', 'date_format_preference'),
        }),
    )
    
    filter_horizontal = ('allowed_areas', 'allowed_stations', 'allowed_containers')
    
    def location_count(self, obj):
        """Display count of assigned locations."""
        areas = obj.allowed_areas.count()
        stations = obj.allowed_stations.count()
        containers = obj.allowed_containers.count()
        total = areas + stations + containers
        
        if total == 0:
            return '-'
        
        parts = []
        if areas:
            parts.append(f'{areas} areas')
        if stations:
            parts.append(f'{stations} stations')
        if containers:
            parts.append(f'{containers} containers')
        
        return ', '.join(parts)
    
    location_count.short_description = _('Location Assignments')