"""
Django admin configuration for Scenario Planning models.

Provides comprehensive admin interface for managing scenario configurations,
biological models, and projections.
"""
from django.contrib import admin
from .models import (
    TemperatureProfile, TemperatureReading, TGCModel, FCRModel, 
    FCRModelStage, MortalityModel, Scenario, ScenarioModelChange,
    ScenarioProjection,
    # New biological constraint models
    BiologicalConstraints, StageConstraint,
    TGCModelStage, FCRModelStageOverride,
    MortalityModelStage
)


class TemperatureReadingInline(admin.TabularInline):
    """Inline admin for temperature readings within a profile."""
    model = TemperatureReading
    extra = 1
    fields = ('day_number', 'temperature')
    ordering = ['day_number']


@admin.register(TemperatureProfile)
class TemperatureProfileAdmin(admin.ModelAdmin):
    """Admin configuration for Temperature Profiles."""
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TemperatureReadingInline]
    
    fieldsets = (
        ('Profile Information', {
            'fields': ('name',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TGCModel)
class TGCModelAdmin(admin.ModelAdmin):
    """Admin configuration for TGC Models with history tracking."""
    list_display = ('name', 'location', 'release_period', 'tgc_value', 'profile')
    list_filter = ('location', 'release_period', 'profile')
    search_fields = ('name', 'location')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Model Information', {
            'fields': ('name', 'location', 'release_period', 'profile')
        }),
        ('TGC Parameters', {
            'fields': ('tgc_value', 'exponent_n', 'exponent_m'),
            'description': 'Growth calculation: TGC × Temperature^n × Weight^m'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class FCRModelStageInline(admin.TabularInline):
    """Inline admin for FCR stages within a model."""
    model = FCRModelStage
    extra = 1
    fields = ('stage', 'fcr_value', 'duration_days')
    autocomplete_fields = ['stage']


@admin.register(FCRModel)
class FCRModelAdmin(admin.ModelAdmin):
    """Admin configuration for FCR Models with history tracking."""
    list_display = ('name', 'get_stage_count', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [FCRModelStageInline]
    
    fieldsets = (
        ('Model Information', {
            'fields': ('name',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_stage_count(self, obj):
        """Display the number of lifecycle stages configured."""
        return obj.stages.count()
    get_stage_count.short_description = 'Stages Configured'


@admin.register(MortalityModel)
class MortalityModelAdmin(admin.ModelAdmin):
    """Admin configuration for Mortality Models with history tracking."""
    list_display = ('name', 'rate', 'frequency', 'created_at')
    list_filter = ('frequency',)
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Model Information', {
            'fields': ('name', 'frequency', 'rate'),
            'description': 'Mortality rate applied daily or weekly'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class ScenarioModelChangeInline(admin.TabularInline):
    """Inline admin for model changes within a scenario."""
    model = ScenarioModelChange
    extra = 0
    fields = ('change_day', 'new_tgc_model', 'new_fcr_model', 'new_mortality_model')
    autocomplete_fields = ['new_tgc_model', 'new_fcr_model', 'new_mortality_model']


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    """Admin configuration for Scenarios with history tracking."""
    list_display = ('name', 'start_date', 'duration_days', 'initial_count', 
                    'tgc_model', 'created_by', 'created_at')
    list_filter = ('start_date', 'tgc_model__location', 'created_by')
    search_fields = ('name', 'genotype', 'supplier')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['tgc_model', 'fcr_model', 'mortality_model', 'batch']
    inlines = [ScenarioModelChangeInline]
    
    fieldsets = (
        ('Scenario Configuration', {
            'fields': ('name', 'start_date', 'duration_days')
        }),
        ('Initial Conditions', {
            'fields': ('initial_count', 'initial_weight', 'genotype', 'supplier')
        }),
        ('Biological Models', {
            'fields': ('tgc_model', 'fcr_model', 'mortality_model')
        }),
        ('Data Source', {
            'fields': ('batch',),
            'description': 'Optional: Link to existing batch for real-data initialization'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Automatically set created_by on new scenarios."""
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ScenarioProjection)
class ScenarioProjectionAdmin(admin.ModelAdmin):
    """Admin configuration for Scenario Projections."""
    list_display = ('scenario', 'day_number', 'projection_date', 'average_weight', 
                    'population', 'biomass', 'current_stage')
    list_filter = ('scenario', 'current_stage', 'projection_date')
    search_fields = ('scenario__name',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'projection_date'
    
    # Limit editing as projections are typically calculated
    def has_add_permission(self, request):
        """Projections are calculated, not manually added."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Projections are read-only."""
        return False
    
    fieldsets = (
        ('Scenario', {
            'fields': ('scenario', 'projection_date', 'day_number')
        }),
        ('Fish Metrics', {
            'fields': ('average_weight', 'population', 'biomass', 'current_stage')
        }),
        ('Feed & Environment', {
            'fields': ('daily_feed', 'cumulative_feed', 'temperature')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# Register remaining models if needed
@admin.register(TemperatureReading)
class TemperatureReadingAdmin(admin.ModelAdmin):
    """Standalone admin for temperature readings."""
    list_display = ('profile', 'day_number', 'temperature')
    list_filter = ('profile',)
    ordering = ['profile', 'day_number']
    search_fields = ('profile__name',)


@admin.register(FCRModelStage)
class FCRModelStageAdmin(admin.ModelAdmin):
    """Standalone admin for FCR model stages."""
    list_display = ('model', 'stage', 'fcr_value', 'duration_days')
    list_filter = ('model', 'stage')
    search_fields = ('model__name', 'stage__name')
    autocomplete_fields = ['model', 'stage']


@admin.register(ScenarioModelChange)
class ScenarioModelChangeAdmin(admin.ModelAdmin):
    """Standalone admin for scenario model changes."""
    list_display = ('scenario', 'change_day', 'get_changes_summary')
    list_filter = ('scenario', 'change_day')
    search_fields = ('scenario__name',)
    autocomplete_fields = ['scenario', 'new_tgc_model', 'new_fcr_model', 'new_mortality_model']
    
    def get_changes_summary(self, obj):
        """Display a summary of what models are being changed."""
        changes = []
        if obj.new_tgc_model:
            changes.append('TGC')
        if obj.new_fcr_model:
            changes.append('FCR')
        if obj.new_mortality_model:
            changes.append('Mortality')
        return ', '.join(changes) if changes else 'No changes'
    get_changes_summary.short_description = 'Models Changed'


# New admin classes for biological constraints

class StageConstraintInline(admin.TabularInline):
    """Inline admin for stage constraints."""
    model = StageConstraint
    extra = 1
    fields = [
        'lifecycle_stage', 'min_weight_g', 'max_weight_g',
        'min_temperature_c', 'max_temperature_c',
        'typical_duration_days', 'max_freshwater_weight_g'
    ]


@admin.register(BiologicalConstraints)
class BiologicalConstraintsAdmin(admin.ModelAdmin):
    """Admin interface for biological constraint sets."""
    list_display = ['name', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [StageConstraintInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        """Auto-populate created_by field."""
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def has_change_permission(self, request, obj=None):
        """Only users with special permission can edit biological constraints."""
        return request.user.has_perm('scenario.can_manage_biological_constraints')
    
    def has_add_permission(self, request):
        """Only users with special permission can add biological constraints."""
        return request.user.has_perm('scenario.can_manage_biological_constraints')
    
    def has_delete_permission(self, request, obj=None):
        """Only users with special permission can delete biological constraints."""
        return request.user.has_perm('scenario.can_manage_biological_constraints')


class TGCModelStageInline(admin.TabularInline):
    """Inline admin for TGC stage overrides."""
    model = TGCModelStage
    extra = 0
    fields = ['lifecycle_stage', 'tgc_value', 'temperature_exponent', 'weight_exponent']


# Update the existing TGCModelAdmin to include stage overrides
admin.site.unregister(TGCModel)
@admin.register(TGCModel)
class TGCModelAdminEnhanced(admin.ModelAdmin):
    """Enhanced TGC Model admin with stage overrides."""
    list_display = ('name', 'location', 'release_period', 'tgc_value', 'profile', 'has_stage_overrides')
    list_filter = ('location', 'release_period', 'profile')
    search_fields = ('name', 'location')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TGCModelStageInline]
    
    fieldsets = (
        ('Model Information', {
            'fields': ('name', 'location', 'release_period', 'profile')
        }),
        ('TGC Parameters', {
            'fields': ('tgc_value', 'exponent_n', 'exponent_m'),
            'description': 'Base values - can be overridden per lifecycle stage below'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_stage_overrides(self, obj):
        """Check if model has stage-specific overrides."""
        return obj.stage_overrides.exists()
    has_stage_overrides.boolean = True
    has_stage_overrides.short_description = 'Stage Overrides'


class FCRModelStageOverrideInline(admin.TabularInline):
    """Inline admin for FCR weight-based overrides."""
    model = FCRModelStageOverride
    extra = 0
    fields = ['min_weight_g', 'max_weight_g', 'fcr_value']
    ordering = ['min_weight_g']


# Update the existing FCRModelStageAdmin to include weight overrides
admin.site.unregister(FCRModelStage)
@admin.register(FCRModelStage)
class FCRModelStageAdminEnhanced(admin.ModelAdmin):
    """Enhanced FCR Model Stage admin with weight overrides."""
    list_display = ('model', 'stage', 'fcr_value', 'duration_days', 'has_weight_overrides')
    list_filter = ('model', 'stage')
    search_fields = ('model__name', 'stage__name')
    autocomplete_fields = ['model', 'stage']
    inlines = [FCRModelStageOverrideInline]
    
    def has_weight_overrides(self, obj):
        """Check if stage has weight-based overrides."""
        return obj.overrides.exists()
    has_weight_overrides.boolean = True
    has_weight_overrides.short_description = 'Weight Overrides'


class MortalityModelStageInline(admin.TabularInline):
    """Inline admin for mortality stage overrides."""
    model = MortalityModelStage
    extra = 0
    fields = ['lifecycle_stage', 'daily_rate_percent', 'weekly_rate_percent']
    readonly_fields = ['weekly_rate_percent']  # Auto-calculated


# Update the existing MortalityModelAdmin to include stage overrides
admin.site.unregister(MortalityModel)
@admin.register(MortalityModel)
class MortalityModelAdminEnhanced(admin.ModelAdmin):
    """Enhanced Mortality Model admin with stage overrides."""
    list_display = ('name', 'rate', 'frequency', 'has_stage_overrides', 'created_at')
    list_filter = ('frequency',)
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MortalityModelStageInline]
    
    fieldsets = (
        ('Model Information', {
            'fields': ('name', 'frequency', 'rate'),
            'description': 'Base mortality rate - can be overridden per lifecycle stage below'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_stage_overrides(self, obj):
        """Check if model has stage-specific overrides."""
        return obj.stage_overrides.exists()
    has_stage_overrides.boolean = True
    has_stage_overrides.short_description = 'Stage Overrides'


# Update Scenario admin to show biological constraints
admin.site.unregister(Scenario)
@admin.register(Scenario)
class ScenarioAdminEnhanced(admin.ModelAdmin):
    """Enhanced Scenario admin with biological constraints."""
    list_display = ('name', 'start_date', 'duration_days', 'initial_count', 
                    'tgc_model', 'biological_constraints', 'created_by', 'created_at')
    list_filter = ('start_date', 'tgc_model__location', 'biological_constraints', 'created_by')
    search_fields = ('name', 'genotype', 'supplier')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['tgc_model', 'fcr_model', 'mortality_model', 'batch', 'biological_constraints']
    inlines = [ScenarioModelChangeInline]
    
    fieldsets = (
        ('Scenario Configuration', {
            'fields': ('name', 'start_date', 'duration_days')
        }),
        ('Initial Conditions', {
            'fields': ('initial_count', 'initial_weight', 'genotype', 'supplier')
        }),
        ('Biological Models', {
            'fields': ('tgc_model', 'fcr_model', 'mortality_model', 'biological_constraints'),
            'description': 'Select biological models and optional constraint set for validation'
        }),
        ('Data Source', {
            'fields': ('batch',),
            'description': 'Optional: Link to existing batch for real-data initialization'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Automatically set created_by on new scenarios."""
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
