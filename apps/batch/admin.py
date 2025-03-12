from django.contrib import admin
from .models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchTransfer,
    MortalityEvent,
    GrowthSample
)


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ('name', 'scientific_name', 'optimal_temperature_min', 'optimal_temperature_max')
    search_fields = ('name', 'scientific_name', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'scientific_name', 'description')
        }),
        ('Environmental Parameters', {
            'fields': (
                'optimal_temperature_min', 'optimal_temperature_max',
                'optimal_oxygen_min', 'optimal_ph_min', 'optimal_ph_max'
            )
        }),
    )


@admin.register(LifeCycleStage)
class LifeCycleStageAdmin(admin.ModelAdmin):
    list_display = ('name', 'species', 'order', 'expected_weight_min_g', 'expected_weight_max_g')
    list_filter = ('species',)
    search_fields = ('name', 'description')
    ordering = ('species', 'order')


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = (
        'batch_number', 'species', 'lifecycle_stage', 'container',
        'population_count', 'avg_weight_g', 'biomass_kg', 'status', 'start_date'
    )
    list_filter = ('species', 'lifecycle_stage', 'status', 'container')
    search_fields = ('batch_number', 'notes')
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('batch_number', 'species', 'lifecycle_stage', 'container', 'status')
        }),
        ('Population Details', {
            'fields': ('population_count', 'biomass_kg', 'avg_weight_g')
        }),
        ('Timeline', {
            'fields': ('start_date', 'expected_end_date', 'actual_end_date')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )


@admin.register(BatchTransfer)
class BatchTransferAdmin(admin.ModelAdmin):
    list_display = (
        'source_batch', 'transfer_type', 'transfer_date', 'source_container',
        'destination_container', 'transferred_count', 'mortality_count'
    )
    list_filter = ('transfer_type', 'transfer_date')
    search_fields = ('source_batch__batch_number', 'destination_batch__batch_number', 'notes')
    date_hierarchy = 'transfer_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('source_batch', 'destination_batch', 'transfer_type', 'transfer_date')
        }),
        ('Population Changes', {
            'fields': ('source_count', 'transferred_count', 'mortality_count')
        }),
        ('Biomass', {
            'fields': ('source_biomass_kg', 'transferred_biomass_kg')
        }),
        ('Lifecycle', {
            'fields': ('source_lifecycle_stage', 'destination_lifecycle_stage')
        }),
        ('Location', {
            'fields': ('source_container', 'destination_container')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )


@admin.register(MortalityEvent)
class MortalityEventAdmin(admin.ModelAdmin):
    list_display = ('batch', 'event_date', 'count', 'biomass_kg', 'cause')
    list_filter = ('cause', 'event_date')
    search_fields = ('batch__batch_number', 'description')
    date_hierarchy = 'event_date'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(GrowthSample)
class GrowthSampleAdmin(admin.ModelAdmin):
    list_display = (
        'batch', 'sample_date', 'sample_size', 'avg_weight_g',
        'avg_length_cm', 'condition_factor'
    )
    list_filter = ('sample_date',)
    search_fields = ('batch__batch_number', 'notes')
    date_hierarchy = 'sample_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('batch', 'sample_date', 'sample_size')
        }),
        ('Measurements', {
            'fields': (
                'avg_weight_g', 'avg_length_cm', 'std_deviation_weight',
                'std_deviation_length', 'min_weight_g', 'max_weight_g', 'condition_factor'
            )
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )
