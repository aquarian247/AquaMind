from django.contrib import admin

from .models import (
    JournalEntry, MortalityReason, LiceCount, MortalityRecord, Treatment,
    VaccinationType, SampleType,
    HealthParameter, HealthObservation # Added new models
)

# Inline Admin for Health Observations within Journal Entry
class HealthObservationInline(admin.TabularInline):
    model = HealthObservation
    extra = 1 # Show 1 extra blank forms by default
    fields = ('parameter', 'score')
    autocomplete_fields = ['parameter'] # Use autocomplete for parameter selection

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_date', 'batch', 'container', 'category', 'severity', 'user', 'resolution_status', 'created_at')
    list_filter = ('category', 'severity', 'entry_date', 'batch', 'container', 'resolution_status')
    search_fields = ('description', 'resolution_notes', 'batch__batch_name', 'container__name', 'user__username')
    autocomplete_fields = ['batch', 'container']
    readonly_fields = ('user', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('batch', 'container', 'user', 'entry_date', 'category', 'severity', 'description')
        }),
        ('Resolution', {
            'fields': ('resolution_status', 'resolution_notes'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [HealthObservationInline] # Added inline

@admin.register(MortalityReason)
class MortalityReasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('reason', 'description')

@admin.register(LiceCount)
class LiceCountAdmin(admin.ModelAdmin):
    list_display = ('batch', 'container', 'count_date', 'average_per_fish', 'notes')
    list_filter = ('count_date',)
    search_fields = ('notes', 'batch__batch_number', 'container__name')
    autocomplete_fields = ['batch', 'container', 'user']

@admin.register(MortalityRecord)
class MortalityRecordAdmin(admin.ModelAdmin):
    list_display = ('batch', 'container', 'event_date', 'count', 'reason', 'notes')
    list_filter = ('event_date', 'reason')
    search_fields = ('notes', 'batch__batch_number', 'container__name', 'reason__reason')
    autocomplete_fields = ['batch', 'container', 'reason']

@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ('batch', 'container', 'treatment_date', 'treatment_type', 'description', 'dosage', 'outcome')
    list_filter = ('treatment_date', 'treatment_type')
    search_fields = ('treatment_type', 'description', 'dosage', 'outcome', 'batch__batch_number', 'container__name')
    autocomplete_fields = ['batch', 'container', 'vaccination_type']

@admin.register(VaccinationType)
class VaccinationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

@admin.register(SampleType)
class SampleTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

# Register HealthParameter
@admin.register(HealthParameter)
class HealthParameterAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description_score_1', 'description_score_2', 'description_score_3', 'description_score_4', 'description_score_5') 
    fieldsets = (
        (None, {
            'fields': ('name', 'is_active')
        }),
        ('Score Descriptions (1=Good, 5=Bad)', {
            'fields': ('description_score_1', 'description_score_2', 'description_score_3', 'description_score_4', 'description_score_5') 
        }),
    )
