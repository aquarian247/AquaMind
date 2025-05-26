from django.contrib import admin

from .models import (
    JournalEntry, MortalityReason, LiceCount, MortalityRecord, Treatment,
    VaccinationType, SampleType,
    HealthParameter,
    HealthSamplingEvent,
    IndividualFishObservation,
    FishParameterScore,
    HealthLabSample # BatchContainerAssignment will be imported separately
)
from apps.batch.models import BatchContainerAssignment # Correct import

from django import forms

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

class IndividualFishObservationInline(admin.TabularInline):
    model = IndividualFishObservation
    extra = 1
    fields = ('fish_identifier', 'length_cm', 'weight_g')
    # Potentially add FishParameterScoreInline here if desired

class FishParameterScoreInline(admin.TabularInline):
    model = FishParameterScore
    extra = 1
    fields = ('parameter', 'score')
    autocomplete_fields = ['parameter']

@admin.register(HealthSamplingEvent)
class HealthSamplingEventAdmin(admin.ModelAdmin):
    list_display = ('sampling_date', 'assignment', 'number_of_fish_sampled', 'calculated_sample_size', 'avg_weight_g', 'avg_length_cm', 'avg_k_factor', 'sampled_by')
    list_filter = ('sampling_date', 'assignment__batch', 'assignment__container')
    search_fields = ('assignment__batch__batch_number', 'assignment__container__name', 'notes')
    autocomplete_fields = ['assignment', 'sampled_by']
    inlines = [IndividualFishObservationInline]
    readonly_fields = (
        'avg_weight_g', 'avg_length_cm', 
        'min_weight_g', 'max_weight_g', 'min_length_cm', 'max_length_cm',
        'avg_k_factor', 'calculated_sample_size'
    )
    date_hierarchy = 'sampling_date'

    fieldsets = (
        (None, {
            'fields': ('assignment', 'sampling_date', 'number_of_fish_sampled', 'sampled_by', 'notes')
        }),
        ('Calculated Growth Metrics', {
            'fields': (
                'calculated_sample_size', 'avg_weight_g', 'std_dev_weight_g', 'min_weight_g', 'max_weight_g',
                'avg_length_cm', 'std_dev_length_cm', 'min_length_cm', 'max_length_cm',
                'avg_k_factor'
            ),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def save_model(self, request, obj, form, change):
        """Override to trigger metric calculation after saving the event and its inlines."""
        super().save_model(request, obj, form, change)  # Save the object and inlines first
        # After saving, the obj (HealthSamplingEvent) has an ID and related observations are committed.
        # Now, calculate and save the aggregate metrics.
        obj.calculate_aggregate_metrics() # This method now saves the instance

@admin.register(IndividualFishObservation)
class IndividualFishObservationAdmin(admin.ModelAdmin):
    list_display = ('sampling_event', 'fish_identifier', 'length_cm', 'weight_g')
    list_filter = (
        'sampling_event__sampling_date',
        'sampling_event__assignment__batch__batch_number',
        'sampling_event__assignment__container__name',
        'sampling_event__sampled_by__username'
    )
    search_fields = ('fish_identifier',)
    autocomplete_fields = ['sampling_event']
    inlines = [FishParameterScoreInline]

@admin.register(FishParameterScore)
class FishParameterScoreAdmin(admin.ModelAdmin):
    list_display = ('individual_fish_observation', 'parameter', 'score')
    list_filter = ('parameter', 'score', 'individual_fish_observation__sampling_event__sampling_date')
    search_fields = ('individual_fish_observation__fish_identifier', 'parameter__name')
    autocomplete_fields = ['individual_fish_observation', 'parameter']

from django.db.models import Q

class HealthLabSampleForm(forms.ModelForm):
    class Meta:
        model = HealthLabSample
        # fields = '__all__'
        exclude = () # 'recorded_by' is handled by readonly_fields and save_model # Exclude recorded_by as it's set by admin

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['batch_container_assignment'].widget = forms.Select()
        self.fields['batch_container_assignment'].label_from_instance = self.batch_container_assignment_label
        self.fields['sample_type'].widget = forms.Select()
        self.fields['sample_type'].queryset = SampleType.objects.all()

        # Dynamically filter batch_container_assignment based on sample_date
        # If instance and sample_date exist, filter initially
        # Otherwise, JavaScript will handle dynamic updates on sample_date change
        if self.instance and self.instance.pk and self.instance.sample_date:
            sample_date = self.instance.sample_date
            self.fields['batch_container_assignment'].queryset = BatchContainerAssignment.objects.filter(
                Q(assignment_date__lte=sample_date) &
                (Q(departure_date__gte=sample_date) | Q(departure_date__isnull=True))
            ).select_related('batch', 'container').order_by('-assignment_date', 'batch__batch_number')
        else:
            # For new forms, or if sample_date is not yet set, show all assignments initially.
            # The clean() method will validate the selection against the provided sample_date.
            # JavaScript will handle the dynamic filtering in the UI based on sample_date changes.
            self.fields['batch_container_assignment'].queryset = BatchContainerAssignment.objects.all().select_related('batch', 'container').order_by('-assignment_date', 'batch__batch_number')

    def batch_container_assignment_label(self, obj):
        batch_number = obj.batch.batch_number if obj.batch else 'N/A'
        container_name = obj.container.name if obj.container else 'N/A'
        return f"Batch: {batch_number} - Container: {container_name}"

    def clean(self):
        cleaned_data = super().clean()
        sample_date = cleaned_data.get('sample_date')
        date_sent_to_lab = cleaned_data.get('date_sent_to_lab')
        date_results_received = cleaned_data.get('date_results_received')

        if sample_date and date_sent_to_lab and sample_date > date_sent_to_lab:
            self.add_error('sample_date', "Sample date cannot be after the date sent to lab.")
        if date_sent_to_lab and date_results_received and date_results_received < date_sent_to_lab:
            self.add_error('date_results_received', "Date results received cannot be before the date sent to lab.")

        # Validate sample_date against batch_container_assignment active period
        assignment = cleaned_data.get('batch_container_assignment')
        if sample_date and assignment:
            if sample_date < assignment.assignment_date:
                self.add_error('sample_date', 
                                 f"Sample date ({sample_date}) cannot be before the assignment date ({assignment.assignment_date}).")
            if assignment.departure_date and sample_date > assignment.departure_date:
                self.add_error('sample_date', 
                                 f"Sample date ({sample_date}) cannot be after the assignment departure date ({assignment.departure_date}).")

        return cleaned_data

@admin.register(HealthLabSample)
class HealthLabSampleAdmin(admin.ModelAdmin):
    form = HealthLabSampleForm

    class Media:
        js = (
            'admin/js/vendor/jquery/jquery.min.js', # Django's jQuery
            'health/js/health_lab_sample_admin.js',  # Path to app-specific static JS
        )

    list_display = (
        'sample_date',
        'batch_container_assignment_info',
        'sample_type',
        'lab_reference_id',
        'date_results_received',
        'recorded_by',
        'created_at'
    )
    list_filter = ('sample_date', 'sample_type', 'date_results_received', 'recorded_by')
    search_fields = (
        'batch_container_assignment__batch__batch_number',
        'batch_container_assignment__container__name',
        'sample_type__name',
        'lab_reference_id',
        'findings_summary',
        'notes'
    )
    readonly_fields = ('recorded_by', 'created_at', 'updated_at') # recorded_by will be set in save_model

    fieldsets = (
        (None, {
            'fields': (
                'batch_container_assignment',
                'sample_type',
                'sample_date',
            )
        }),
        ('Lab Details', {
            'fields': (
                'date_sent_to_lab',
                'date_results_received',
                'lab_reference_id',
                'attachment'
            )
        }),
        ('Results', {
            'fields': ('findings_summary', 'quantitative_results', 'notes')
        }),
        ('Audit', {
            'fields': ('recorded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def batch_container_assignment_info(self, obj):
        if obj.batch_container_assignment:
            batch = obj.batch_container_assignment.batch
            container = obj.batch_container_assignment.container
            return f"Batch: {batch.batch_number if batch else 'N/A'} - Container: {container.name if container else 'N/A'}"
        return "N/A"
    batch_container_assignment_info.short_description = "Batch & Container"

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # if creating new object
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)
