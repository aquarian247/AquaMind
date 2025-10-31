from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import (
    Batch,
    BatchContainerAssignment,
    BatchTransferWorkflow,
    TransferAction,
    GrowthSample,
    IndividualGrowthObservation,
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
class BatchAdmin(SimpleHistoryAdmin):
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
class BatchContainerAssignmentAdmin(SimpleHistoryAdmin):
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


@admin.register(MortalityEvent)
class MortalityEventAdmin(SimpleHistoryAdmin):
    """Admin interface for the MortalityEvent model."""
    list_display = ('batch', 'event_date', 'count', 'biomass_kg', 'cause')
    list_filter = ('cause', 'event_date')
    search_fields = ('batch__batch_number', 'description')
    date_hierarchy = 'event_date'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(GrowthSample)
class GrowthSampleAdmin(SimpleHistoryAdmin):
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


@admin.register(IndividualGrowthObservation)
class IndividualGrowthObservationAdmin(SimpleHistoryAdmin):
    """Admin interface for the IndividualGrowthObservation model."""
    list_display = (
        'growth_sample',
        'fish_identifier',
        'weight_g',
        'length_cm',
        'get_k_factor',
    )
    list_filter = (
        'growth_sample__sample_date',
        'growth_sample__assignment__batch__batch_number',
    )
    search_fields = (
        'fish_identifier',
        'growth_sample__assignment__batch__batch_number',
    )
    readonly_fields = ('created_at', 'updated_at', 'get_k_factor')
    
    def get_k_factor(self, obj):
        """Calculate and display K-factor for the individual fish."""
        if obj.weight_g and obj.length_cm and obj.length_cm > 0:
            k_factor = (obj.weight_g / (obj.length_cm ** 3)) * 100
            return f"{k_factor:.2f}"
        return None
    get_k_factor.short_description = 'K-Factor'


class TransferActionInline(admin.TabularInline):
    """Inline admin for TransferAction."""
    model = TransferAction
    extra = 0
    fields = (
        'action_number',
        'source_assignment',
        'dest_assignment',
        'transferred_count',
        'status',
        'planned_date',
        'actual_execution_date',
    )
    readonly_fields = ('actual_execution_date',)
    ordering = ['action_number']


@admin.register(BatchTransferWorkflow)
class BatchTransferWorkflowAdmin(SimpleHistoryAdmin):
    """Admin interface for the BatchTransferWorkflow model."""
    list_display = (
        'workflow_number',
        'batch',
        'workflow_type',
        'status',
        'completion_percentage',
        'planned_start_date',
        'actual_start_date',
        'is_intercompany',
    )
    list_filter = (
        'status',
        'workflow_type',
        'is_intercompany',
        'planned_start_date',
    )
    search_fields = (
        'workflow_number',
        'batch__batch_number',
        'notes',
    )
    date_hierarchy = 'planned_start_date'
    readonly_fields = (
        'actual_start_date',
        'actual_completion_date',
        'total_source_count',
        'total_transferred_count',
        'total_mortality_count',
        'total_biomass_kg',
        'total_actions_planned',
        'actions_completed',
        'completion_percentage',
        'created_at',
        'updated_at',
    )
    inlines = [TransferActionInline]
    fieldsets = (
        (None, {
            'fields': (
                'workflow_number',
                'batch',
                'workflow_type',
                'status',
            )
        }),
        ('Lifecycle Context', {
            'fields': (
                'source_lifecycle_stage',
                'dest_lifecycle_stage',
            )
        }),
        ('Timeline', {
            'fields': (
                'planned_start_date',
                'planned_completion_date',
                'actual_start_date',
                'actual_completion_date',
            )
        }),
        ('Progress Tracking', {
            'fields': (
                'total_actions_planned',
                'actions_completed',
                'completion_percentage',
            )
        }),
        ('Summary Metrics', {
            'fields': (
                'total_source_count',
                'total_transferred_count',
                'total_mortality_count',
                'total_biomass_kg',
            )
        }),
        ('Finance Integration', {
            'fields': (
                'is_intercompany',
                'source_subsidiary',
                'dest_subsidiary',
                'finance_transaction',
            )
        }),
        ('Audit & Notes', {
            'fields': (
                'initiated_by',
                'completed_by',
                'notes',
                'cancellation_reason',
                'created_at',
                'updated_at',
            )
        }),
    )


@admin.register(TransferAction)
class TransferActionAdmin(SimpleHistoryAdmin):
    """Admin interface for the TransferAction model."""
    list_display = (
        'workflow',
        'action_number',
        'source_assignment',
        'dest_assignment',
        'transferred_count',
        'status',
        'planned_date',
        'actual_execution_date',
    )
    list_filter = (
        'status',
        'transfer_method',
        'planned_date',
        'actual_execution_date',
    )
    search_fields = (
        'workflow__workflow_number',
        'notes',
    )
    date_hierarchy = 'actual_execution_date'
    readonly_fields = (
        'actual_execution_date',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        (None, {
            'fields': (
                'workflow',
                'action_number',
                'status',
            )
        }),
        ('Source & Destination', {
            'fields': (
                'source_assignment',
                'dest_assignment',
            )
        }),
        ('Transfer Details', {
            'fields': (
                'source_population_before',
                'transferred_count',
                'mortality_during_transfer',
                'transferred_biomass_kg',
                'transfer_method',
            )
        }),
        ('Timeline', {
            'fields': (
                'planned_date',
                'actual_execution_date',
                'execution_duration_minutes',
            )
        }),
        ('Environmental Conditions', {
            'fields': (
                'water_temp_c',
                'oxygen_level',
            )
        }),
        ('Execution', {
            'fields': (
                'executed_by',
                'notes',
                'created_at',
                'updated_at',
            )
        }),
    )
