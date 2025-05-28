from django.contrib import admin
from .models import (
    Batch,
    BatchContainerAssignment,
    BatchTransfer,
    GrowthSample,
    LifeCycleStage,
    MortalityEvent,
    Species,
)


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    """Admin interface for the Species model."""
    list_display = (
        'name',
        'scientific_name',
        'optimal_temperature_min',
        'optimal_temperature_max',
    )
    search_fields = ('name', 'scientific_name', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'scientific_name', 'description')
        }),
        ('Environmental Parameters', {
            'fields': (
                'optimal_temperature_min',
                'optimal_temperature_max',
                'optimal_oxygen_min',
                'optimal_ph_min',
                'optimal_ph_max',
            )
        }),
    )


@admin.register(LifeCycleStage)
class LifeCycleStageAdmin(admin.ModelAdmin):
    """Admin interface for the LifeCycleStage model."""
    list_display = (
        'name',
        'species',
        'order',
        'expected_weight_min_g',
        'expected_weight_max_g',
    )
    list_filter = ('species',)
    search_fields = ('name', 'description')
    ordering = ('species', 'order')


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    """Admin interface for the Batch model."""
    list_display = (
        'batch_number',
        'species',
        'lifecycle_stage',
        'batch_type',
        'calculated_population_count',
        'calculated_avg_weight_g',
        'calculated_biomass_kg',
        'status',
        'start_date',
    )
    list_filter = ('species', 'lifecycle_stage', 'status', 'batch_type')
    search_fields = ('batch_number', 'notes')
    date_hierarchy = 'start_date'
    readonly_fields = (
        'created_at',
        'updated_at',
        'calculated_population_count',
        'calculated_avg_weight_g',
        'calculated_biomass_kg',
    )
    fieldsets = (
        (None, {
            'fields': (
                'batch_number',
                'species',
                'lifecycle_stage',
                'batch_type',
                'status',
            )
        }),
        ('Calculated Population Details', {
            'fields': (
                'calculated_population_count',
                'calculated_biomass_kg',
                'calculated_avg_weight_g',
            )
        }),
        ('Timeline', {
            'fields': ('start_date', 'expected_end_date', 'actual_end_date')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )


@admin.register(BatchContainerAssignment)
class BatchContainerAssignmentAdmin(admin.ModelAdmin):
    """Admin interface for the BatchContainerAssignment model."""
    list_display = (
        'batch',
        'container',
        'assignment_date',
        'population_count',
        'avg_weight_g',
        'biomass_kg',
        'lifecycle_stage',
    )
    list_filter = (
        'assignment_date',
        'lifecycle_stage',
        'container__container_type__name',
    )
    search_fields = ('batch__batch_number', 'container__name', 'notes')
    date_hierarchy = 'assignment_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': (
                'batch',
                'container',
                'lifecycle_stage',
                'assignment_date',
            )
        }),
        ('Population Details', {
            'fields': ('population_count', 'avg_weight_g', 'biomass_kg')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )


@admin.register(BatchTransfer)
class BatchTransferAdmin(admin.ModelAdmin):
    """Admin interface for the BatchTransfer model."""
    list_display = (
        'source_batch',
        'transfer_type',
        'transfer_date',
        'transferred_count',
        'mortality_count',
    )
    list_filter = ('transfer_type', 'transfer_date')
    search_fields = (
        'source_batch__batch_number',
        'destination_batch__batch_number',
        'notes',
    )
    date_hierarchy = 'transfer_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': (
                'source_batch',
                'destination_batch',
                'transfer_type',
                'transfer_date',
            )
        }),
        ('Population Changes', {
            'fields': ('source_count', 'transferred_count', 'mortality_count')
        }),
        ('Biomass', {
            'fields': ('source_biomass_kg', 'transferred_biomass_kg')
        }),
        ('Lifecycle', {
            'fields': (
                'source_lifecycle_stage',
                'destination_lifecycle_stage',
            )
        }),
        ('Assignments', {
            'fields': ('source_assignment', 'destination_assignment')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )


@admin.register(MortalityEvent)
class MortalityEventAdmin(admin.ModelAdmin):
    """Admin interface for the MortalityEvent model."""
    list_display = ('batch', 'event_date', 'count', 'biomass_kg', 'cause')
    list_filter = ('cause', 'event_date')
    search_fields = ('batch__batch_number', 'description')
    date_hierarchy = 'event_date'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(GrowthSample)
class GrowthSampleAdmin(admin.ModelAdmin):
    """Admin interface for the GrowthSample model."""
    list_display = (
        'assignment',
        'sample_date',
        'sample_size',
        'avg_weight_g',
        'avg_length_cm',
        'condition_factor',
    )
    list_filter = (
        'sample_date',
        'assignment__container__name',
        'assignment__batch__batch_number',
    )
    search_fields = (
        'assignment__batch__batch_number',
        'assignment__id',
        'notes',
    )
    date_hierarchy = 'sample_date'
    readonly_fields = ('condition_factor', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('assignment', 'sample_date', 'sample_size')
        }),
        ('Measurements', {
            'fields': (
                'avg_weight_g',
                'avg_length_cm',
                'std_deviation_weight',
                'std_deviation_length',
                'min_weight_g',
                'max_weight_g',
                'condition_factor',
            )
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )
