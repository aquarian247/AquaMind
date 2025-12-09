"""
Django admin configuration for the planning app.
"""
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import PlannedActivity, ActivityTemplate


@admin.register(PlannedActivity)
class PlannedActivityAdmin(SimpleHistoryAdmin):
    """Admin interface for PlannedActivity with history tracking."""
    
    list_display = [
        'id',
        'scenario',
        'batch',
        'activity_type',
        'due_date',
        'status',
        'created_by',
        'created_at',
    ]
    list_filter = [
        'activity_type',
        'status',
        'scenario',
        'created_at',
        'due_date'
    ]
    search_fields = [
        'batch__batch_number',
        'scenario__name',
        'notes'
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'completed_at',
        'is_overdue'
    ]
    autocomplete_fields = [
        'scenario',
        'batch',
        'container'
    ]
    
    fieldsets = (
        ('Core Information', {
            'fields': (
                'scenario',
                'batch',
                'activity_type',
                'due_date',
                'status'
            )
        }),
        ('Details', {
            'fields': (
                'container',
                'notes'
            )
        }),
        ('Integration', {
            'fields': (
                'transfer_workflow',
            )
        }),
        ('Audit Trail', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at',
                'completed_at',
                'completed_by',
                'is_overdue'
            )
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make transfer_workflow readonly after creation."""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj:  # Editing existing object
            readonly.append('transfer_workflow')
        return readonly


@admin.register(ActivityTemplate)
class ActivityTemplateAdmin(admin.ModelAdmin):
    """Admin interface for ActivityTemplate."""
    
    list_display = [
        'id',
        'name',
        'activity_type',
        'trigger_type',
        'is_active',
        'created_at',
    ]
    list_filter = [
        'activity_type',
        'trigger_type',
        'is_active',
        'created_at'
    ]
    search_fields = [
        'name',
        'description'
    ]
    readonly_fields = [
        'created_at',
        'updated_at'
    ]
    autocomplete_fields = [
        'target_lifecycle_stage'
    ]
    
    fieldsets = (
        ('Core Information', {
            'fields': (
                'name',
                'description',
                'activity_type',
                'is_active'
            )
        }),
        ('Trigger Configuration', {
            'fields': (
                'trigger_type',
                'day_offset',
                'weight_threshold_g',
                'target_lifecycle_stage'
            ),
            'description': 'Configure when this activity should be automatically generated'
        }),
        ('Template Content', {
            'fields': (
                'notes_template',
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at'
            )
        }),
    )






