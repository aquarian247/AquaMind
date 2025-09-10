"""
Django admin configuration for the Broodstock Management app.

This module registers all broodstock models with the Django admin interface,
providing comprehensive management capabilities with history tracking support.
"""

from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from apps.broodstock.models import (
    MaintenanceTask, BroodstockFish, FishMovement, BreedingPlan,
    BreedingTraitPriority, BreedingPair, EggProduction, EggSupplier,
    ExternalEggBatch, BatchParentage
)


@admin.register(MaintenanceTask)
class MaintenanceTaskAdmin(SimpleHistoryAdmin):
    """Admin configuration for MaintenanceTask model."""
    
    list_display = [
        'container', 'task_type', 'scheduled_date', 'completed_date',
        'is_overdue_display', 'created_by'
    ]
    list_filter = ['task_type', 'completed_date', 'scheduled_date', 'container__area']
    search_fields = ['container__name', 'notes']
    date_hierarchy = 'scheduled_date'
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    fieldsets = (
        ('Task Information', {
            'fields': ('container', 'task_type', 'scheduled_date', 'completed_date')
        }),
        ('Details', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def is_overdue_display(self, obj):
        """Display overdue status with color coding."""
        if obj.is_overdue:
            return format_html('<span style="color: red;">Yes</span>')
        return format_html('<span style="color: green;">No</span>')
    is_overdue_display.short_description = 'Overdue'
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user on creation."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BroodstockFish)
class BroodstockFishAdmin(SimpleHistoryAdmin):
    """Admin configuration for BroodstockFish model with history tracking."""
    
    list_display = ['id', 'container', 'health_status', 'created_at']
    list_filter = ['health_status', 'container', 'created_at']
    search_fields = ['id', 'container__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('container', 'health_status')
        }),
        ('Traits', {
            'fields': ('traits',),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(FishMovement)
class FishMovementAdmin(SimpleHistoryAdmin):
    """Admin configuration for FishMovement model with history tracking."""
    
    list_display = [
        'fish', 'from_container', 'to_container', 'movement_date', 'moved_by'
    ]
    list_filter = ['movement_date', 'from_container', 'to_container']
    search_fields = ['fish__id', 'notes']
    date_hierarchy = 'movement_date'
    readonly_fields = ['created_at', 'updated_at', 'moved_by']
    
    fieldsets = (
        ('Movement Details', {
            'fields': ('fish', 'from_container', 'to_container', 'movement_date')
        }),
        ('Additional Information', {
            'fields': ('notes', 'moved_by')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        """Set moved_by to current user on creation."""
        if not change:
            obj.moved_by = request.user
        super().save_model(request, obj, form, change)


class BreedingTraitPriorityInline(admin.TabularInline):
    """Inline admin for breeding trait priorities."""
    model = BreedingTraitPriority
    extra = 1
    fields = ['trait_name', 'priority_weight']


@admin.register(BreedingPlan)
class BreedingPlanAdmin(SimpleHistoryAdmin):
    """Admin configuration for BreedingPlan model."""
    
    list_display = [
        'name', 'start_date', 'end_date', 'is_active_display', 'created_by'
    ]
    list_filter = ['start_date', 'end_date', 'created_by']
    search_fields = ['name', 'objectives', 'geneticist_notes', 'breeder_instructions']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    inlines = [BreedingTraitPriorityInline]
    
    fieldsets = (
        ('Plan Information', {
            'fields': ('name', 'start_date', 'end_date', 'objectives')
        }),
        ('Communication', {
            'fields': ('geneticist_notes', 'breeder_instructions'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def is_active_display(self, obj):
        """Display active status with color coding."""
        if obj.is_active:
            return format_html('<span style="color: green;">Active</span>')
        return format_html('<span style="color: gray;">Inactive</span>')
    is_active_display.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user on creation."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BreedingPair)
class BreedingPairAdmin(SimpleHistoryAdmin):
    """Admin configuration for BreedingPair model with history tracking."""
    
    list_display = [
        'id', 'plan', 'male_fish', 'female_fish', 'pairing_date', 'progeny_count'
    ]
    list_filter = ['plan', 'pairing_date']
    search_fields = ['male_fish__id', 'female_fish__id']
    date_hierarchy = 'pairing_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Breeding Information', {
            'fields': ('plan', 'male_fish', 'female_fish', 'pairing_date')
        }),
        ('Results', {
            'fields': ('progeny_count',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(EggSupplier)
class EggSupplierAdmin(SimpleHistoryAdmin):
    """Admin configuration for EggSupplier model."""
    
    list_display = ['name', 'created_at']
    search_fields = ['name', 'contact_details', 'certifications']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Supplier Information', {
            'fields': ('name', 'contact_details', 'certifications')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


class ExternalEggBatchInline(admin.StackedInline):
    """Inline admin for external egg batches."""
    model = ExternalEggBatch
    extra = 0
    fields = ['supplier', 'batch_number', 'provenance_data']


@admin.register(EggProduction)
class EggProductionAdmin(SimpleHistoryAdmin):
    """Admin configuration for EggProduction model with history tracking."""
    
    list_display = [
        'egg_batch_id', 'source_type', 'egg_count', 'production_date',
        'pair', 'destination_station'
    ]
    list_filter = ['source_type', 'production_date', 'destination_station']
    search_fields = ['egg_batch_id']
    date_hierarchy = 'production_date'
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ExternalEggBatchInline]
    
    fieldsets = (
        ('Egg Information', {
            'fields': ('egg_batch_id', 'egg_count', 'production_date', 'source_type')
        }),
        ('Source Details', {
            'fields': ('pair', 'destination_station')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_inline_instances(self, request, obj=None):
        """Only show external batch inline for external source type."""
        if obj and obj.source_type == 'external':
            return super().get_inline_instances(request, obj)
        return []


@admin.register(BatchParentage)
class BatchParentageAdmin(SimpleHistoryAdmin):
    """Admin configuration for BatchParentage model with history tracking."""
    
    list_display = [
        'batch', 'egg_production', 'assignment_date',
        'egg_source_type_display'
    ]
    list_filter = ['assignment_date', 'egg_production__source_type']
    search_fields = ['batch__batch_number', 'egg_production__egg_batch_id']
    date_hierarchy = 'assignment_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Parentage Information', {
            'fields': ('batch', 'egg_production', 'assignment_date')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def egg_source_type_display(self, obj):
        """Display the source type of the eggs."""
        return obj.egg_production.source_type
    egg_source_type_display.short_description = 'Egg Source Type'


# Register the ExternalEggBatch model with SimpleHistoryAdmin
@admin.register(ExternalEggBatch)
class ExternalEggBatchAdmin(SimpleHistoryAdmin):
    """Admin configuration for ExternalEggBatch model with history tracking."""

    list_display = ['supplier', 'batch_number', 'egg_production', 'created_at']
    list_filter = ['supplier', 'created_at']
    search_fields = ['batch_number', 'provenance_data']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Batch Information', {
            'fields': ('supplier', 'batch_number', 'egg_production')
        }),
        ('Provenance', {
            'fields': ('provenance_data',),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
