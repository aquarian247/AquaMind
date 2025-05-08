from django.db import models
from django.db.models import Avg, StdDev, Min, Max, Count
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from django.core.exceptions import ValidationError

from apps.batch.models import Batch, BatchContainerAssignment
from apps.infrastructure.models import Container

User = get_user_model()


class JournalEntry(models.Model):
    """
    Model for recording health observations and actions related to fish batches
    or containers.
    """
    CATEGORY_CHOICES = (
        ('observation', 'Observation'),
        ('issue', 'Issue'),
        ('action', 'Action'),
        ('diagnosis', 'Diagnosis'),
        ('treatment', 'Treatment'),
        ('vaccination', 'Vaccination'),
        ('sample', 'Sample'),
    )
    SEVERITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )

    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name='journal_entries',
        help_text="The batch associated with this journal entry."
    )
    container = models.ForeignKey(
        Container, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='journal_entries',
        help_text="The specific container, if applicable."
    )
    user = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='journal_entries',
        help_text="User who created the entry."
    )
    entry_date = models.DateTimeField(default=timezone.now)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    severity = models.CharField(
        max_length=10, choices=SEVERITY_CHOICES, default='low', blank=True, null=True
    )
    description = models.TextField()
    resolution_status = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Journal Entries"
        ordering = ['-entry_date']

    def __str__(self):
        return (
            f"{self.get_category_display()} - "
            f"{self.entry_date.strftime('%Y-%m-%d')}"
        )


class HealthParameter(models.Model):
    """Defines quantifiable health parameters measured in observations."""
    name = models.CharField(max_length=100, unique=True,
                          help_text="Name of the health parameter (e.g., Gill Health).")
    description_score_1 = models.TextField(help_text="Description for score 1 (Best/Excellent).")
    description_score_2 = models.TextField(help_text="Description for score 2 (Good).")
    description_score_3 = models.TextField(help_text="Description for score 3 (Fair/Moderate).")
    description_score_4 = models.TextField(help_text="Description for score 4 (Poor/Severe).")
    description_score_5 = models.TextField(help_text="Description for score 5 (Worst/Critical).", default="")
    is_active = models.BooleanField(default=True, help_text="Is this parameter currently in use?")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class HealthSamplingEvent(models.Model):
    """Parent event for a health sampling session, linked to a BatchContainerAssignment."""
    assignment = models.ForeignKey(
        BatchContainerAssignment, 
        on_delete=models.CASCADE, 
        related_name='health_sampling_events',
        help_text="The specific batch and container assignment being sampled."
    )
    sampling_date = models.DateField(default=timezone.now)
    number_of_fish_sampled = models.PositiveIntegerField(
        help_text="Target or initially declared number of individual fish to be examined in this sampling event."
    )
    # New fields for calculated aggregates
    avg_weight_g = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
        help_text="Calculated average weight of sampled fish in grams."
    )
    avg_length_cm = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Calculated average length of sampled fish in centimeters."
    )
    std_dev_weight_g = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
        help_text="Calculated standard deviation of weight for sampled fish."
    )
    std_dev_length_cm = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Calculated standard deviation of length for sampled fish."
    )
    min_weight_g = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
        help_text="Minimum weight recorded in this sample."
    )
    max_weight_g = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
        help_text="Maximum weight recorded in this sample."
    )
    min_length_cm = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Minimum length recorded in this sample."
    )
    max_length_cm = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Maximum length recorded in this sample."
    )
    avg_k_factor = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Calculated average K-factor for fish with both weight and length."
    )
    calculated_sample_size = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Actual number of fish with weight measurements in this sample."
    )

    sampled_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='health_sampling_events_conducted',
        help_text="User who conducted the sampling."
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sampling_date', '-created_at']
        verbose_name = "Health Sampling Event"
        verbose_name_plural = "Health Sampling Events"

    def __str__(self):
        return f"Health Sample - {self.assignment} - {self.sampling_date}"

    def calculate_aggregate_metrics(self):
        """Calculates and updates aggregate metrics from individual fish observations."""
        observations = self.individual_fish_observations.all()

        # Filter out observations where weight_g is None for weight-based calculations
        weight_observations = observations.exclude(weight_g__isnull=True)
        num_weight_observations = weight_observations.count()

        if num_weight_observations > 0:
            if num_weight_observations == 1:
                # Only one observation, StdDev is None or undefined for sample
                weight_aggregates = weight_observations.aggregate(
                    avg_weight=Avg('weight_g'),
                    min_weight=Min('weight_g'),
                    max_weight=Max('weight_g')
                )
                self.avg_weight_g = weight_aggregates['avg_weight']
                self.std_dev_weight_g = None  # StdDev is None for a single sample point
                self.min_weight_g = weight_aggregates['min_weight']
                self.max_weight_g = weight_aggregates['max_weight']
            else:  # num_weight_observations > 1
                weight_aggregates = weight_observations.aggregate(
                    avg_weight=Avg('weight_g'),
                    std_dev_weight=StdDev('weight_g', sample=True),
                    min_weight=Min('weight_g'),
                    max_weight=Max('weight_g')
                )
                self.avg_weight_g = weight_aggregates['avg_weight']
                self.std_dev_weight_g = weight_aggregates.get('std_dev_weight') # .get() is safer
                self.min_weight_g = weight_aggregates['min_weight']
                self.max_weight_g = weight_aggregates['max_weight']
        else:
            self.avg_weight_g = None
            self.std_dev_weight_g = None
            self.min_weight_g = None
            self.max_weight_g = None

        # Filter out observations where length_cm is None for length-based calculations
        length_observations = observations.exclude(length_cm__isnull=True)
        num_length_observations = length_observations.count()

        if num_length_observations > 0:
            if num_length_observations == 1:
                # Only one observation, StdDev is None or undefined for sample
                length_aggregates = length_observations.aggregate(
                    avg_length=Avg('length_cm'),
                    min_length=Min('length_cm'),
                    max_length=Max('length_cm')
                )
                self.avg_length_cm = length_aggregates['avg_length']
                self.std_dev_length_cm = None # StdDev is None for a single sample point
                self.min_length_cm = length_aggregates['min_length']
                self.max_length_cm = length_aggregates['max_length']
            else: # num_length_observations > 1
                length_aggregates = length_observations.aggregate(
                    avg_length=Avg('length_cm'),
                    std_dev_length=StdDev('length_cm', sample=True),
                    min_length=Min('length_cm'),
                    max_length=Max('length_cm')
                )
                self.avg_length_cm = length_aggregates['avg_length']
                self.std_dev_length_cm = length_aggregates.get('std_dev_length') # .get() is safer
                self.min_length_cm = length_aggregates['min_length']
                self.max_length_cm = length_aggregates['max_length']
        else:
            self.avg_length_cm = None
            self.std_dev_length_cm = None
            self.min_length_cm = None
            self.max_length_cm = None

        # K-Factor Calculation & calculated_sample_size definition
        # K = (weight_g / (length_cm^3)) * 100
        # Only include observations with both weight and length, and length > 0
        k_factor_observations = observations.exclude(weight_g__isnull=True).exclude(length_cm__isnull=True).exclude(length_cm=0)
        self.calculated_sample_size = k_factor_observations.count() # Now based on K-factor valid observations
        
        total_k_factor = Decimal('0.0') # Initialize as Decimal
        # count_k_factor_observations is effectively self.calculated_sample_size now
        if self.calculated_sample_size > 0:
            for obs in k_factor_observations:
                # Redundant check as exclude(length_cm=0) should handle it, but safe
                if obs.length_cm > 0: 
                    # Ensure weight_g and length_cm are treated as Decimals
                    k_factor = (obs.weight_g / (obs.length_cm**3)) * Decimal('100.0')
                    total_k_factor += k_factor
            self.avg_k_factor = total_k_factor / Decimal(self.calculated_sample_size)
        else:
            self.avg_k_factor = None

        self.save()


class IndividualFishObservation(models.Model):
    """Records metrics for an individual fish observed during a HealthSamplingEvent."""
    sampling_event = models.ForeignKey(
        HealthSamplingEvent, 
        on_delete=models.CASCADE, 
        related_name='individual_fish_observations'
    )
    fish_identifier = models.PositiveIntegerField(
        help_text="Sequential identifier for the fish within this sampling event (e.g., 1, 2, 3...)."
    )
    length_cm = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Length of the fish in centimeters."
    )
    weight_g = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
        help_text="Weight of the fish in grams."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('sampling_event', 'fish_identifier')
        ordering = ['sampling_event', 'fish_identifier']
        verbose_name = "Individual Fish Observation"
        verbose_name_plural = "Individual Fish Observations"

    def __str__(self):
        return f"Fish #{self.fish_identifier} (Event: {self.sampling_event_id})"


class FishParameterScore(models.Model):
    """Stores a specific health parameter score for an IndividualFishObservation."""
    individual_fish_observation = models.ForeignKey(
        IndividualFishObservation, 
        on_delete=models.CASCADE, 
        related_name='parameter_scores'
    )
    parameter = models.ForeignKey(
        HealthParameter, 
        on_delete=models.PROTECT, # Protect HealthParameters from being deleted if scored
        related_name='fish_scores'
    )
    score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Score from 1 (Best) to 5 (Worst) for the health parameter."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('individual_fish_observation', 'parameter')
        ordering = ['individual_fish_observation', 'parameter']
        verbose_name = "Fish Parameter Score"
        verbose_name_plural = "Fish Parameter Scores"

    def __str__(self):
        return f"{self.individual_fish_observation} - {self.parameter.name}: {self.score}"


class MortalityReason(models.Model):
    """
    Model for categorizing reasons for mortality events.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Mortality Reasons"
        ordering = ['name']

    def __str__(self):
        return self.name


class MortalityRecord(models.Model):
    """
    Model for recording mortality events with counts and reasons.
    """
    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name='mortality_records'
    )
    container = models.ForeignKey(
        Container, on_delete=models.CASCADE, related_name='mortality_records',
        null=True, blank=True
    )
    event_date = models.DateTimeField(auto_now_add=True)
    count = models.PositiveIntegerField()
    reason = models.ForeignKey(
        MortalityReason, on_delete=models.SET_NULL,
        related_name='mortality_records', null=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Mortality Records"
        ordering = ['-event_date']

    def __str__(self):
        return (
            f"Mortality of {self.count} on "
            f"{self.event_date.strftime('%Y-%m-%d')}"
        )


class LiceCount(models.Model):
    """
    Model for recording sea lice counts by life stage for health monitoring.
    """
    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name='lice_counts'
    )
    container = models.ForeignKey(
        Container, on_delete=models.CASCADE, related_name='lice_counts',
        null=True, blank=True
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name='lice_counts',
        null=True
    )
    count_date = models.DateTimeField(auto_now_add=True)
    adult_female_count = models.PositiveIntegerField(default=0)
    adult_male_count = models.PositiveIntegerField(default=0)
    juvenile_count = models.PositiveIntegerField(default=0)
    fish_sampled = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Lice Counts"
        ordering = ['-count_date']

    def __str__(self):
        total = self.adult_female_count + self.adult_male_count
        total += self.juvenile_count
        return (
            f"Lice Count: {total} on "
            f"{self.count_date.strftime('%Y-%m-%d')}"
        )

    @property
    def average_per_fish(self):
        total = self.adult_female_count + self.adult_male_count
        total += self.juvenile_count
        return (
            round(total / self.fish_sampled, 2)
            if self.fish_sampled > 0
            else 0
        )


class VaccinationType(models.Model):
    """
    Model for defining types of vaccinations used in fish health management.
    """
    name = models.CharField(max_length=100, unique=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    dosage = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Vaccination Types"
        ordering = ['name']

    def __str__(self):
        return self.name


class Treatment(models.Model):
    """
    Model for recording treatments applied to batches or containers, including
    vaccinations.
    """
    TREATMENT_TYPE_CHOICES = (
        ('medication', 'Medication'),
        ('vaccination', 'Vaccination'),
        ('delicing', 'Delicing'),
        ('other', 'Other'),
    )

    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name='treatments'
    )
    container = models.ForeignKey(
        Container, on_delete=models.CASCADE, related_name='treatments',
        null=True, blank=True
    )
    batch_assignment = models.ForeignKey(
        BatchContainerAssignment, on_delete=models.CASCADE,
        related_name='treatments', null=True, blank=True
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name='treatments',
        null=True
    )
    treatment_date = models.DateTimeField(auto_now_add=True)
    treatment_type = models.CharField(
        max_length=20, choices=TREATMENT_TYPE_CHOICES, default='medication'
    )
    vaccination_type = models.ForeignKey(
        VaccinationType, on_delete=models.SET_NULL,
        related_name='treatments', null=True, blank=True
    )
    description = models.TextField()
    dosage = models.CharField(max_length=100, blank=True)
    duration_days = models.PositiveIntegerField(default=0)
    withholding_period_days = models.PositiveIntegerField(
        default=0,
        help_text="Days before fish can be harvested after treatment."
    )
    outcome = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Treatments"
        ordering = ['-treatment_date']

    def __str__(self):
        return (
            f"{self.get_treatment_type_display()} on "
            f"{self.treatment_date.strftime('%Y-%m-%d')}"
        )

    @property
    def withholding_end_date(self):
        from datetime import timedelta
        # Calculate the end date by adding the withholding period
        end_datetime = self.treatment_date + timedelta(
            days=self.withholding_period_days
        )
        # Return the date part only, not the full datetime
        return end_datetime.date()


class SampleType(models.Model):
    """
    Model for defining types of samples taken for health or quality monitoring.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Sample Types"

    def __str__(self):
        return self.name


class HealthLabSample(models.Model):
    """
    Represents a lab sample taken from a batch in a specific container
    at a specific point in time, and its results.
    """
    batch_container_assignment = models.ForeignKey(
        BatchContainerAssignment,
        on_delete=models.PROTECT, # Protect if results are linked
        related_name='lab_samples',
        help_text="The specific batch-container assignment active when the sample was taken."
    )
    sample_type = models.ForeignKey(
        SampleType, # Changed from HealthSampleType to match existing model
        on_delete=models.PROTECT,
        related_name='lab_samples',
        help_text="Type of sample taken (e.g., skin mucus, water sample)."
    )
    sample_date = models.DateField(
        help_text="Date the sample was physically taken. Crucial for historical linkage."
    )
    date_sent_to_lab = models.DateField(
        null=True, blank=True,
        help_text="Date the sample was sent to the laboratory."
    )
    date_results_received = models.DateField(
        null=True, blank=True,
        help_text="Date the results were received from the laboratory."
    )
    lab_reference_id = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="External reference ID from the laboratory."
    )
    findings_summary = models.TextField(
        null=True, blank=True,
        help_text="Qualitative summary of the lab findings."
    )
    quantitative_results = models.JSONField(
        null=True, blank=True,
        help_text="Structured quantitative results (e.g., {'param': 'value', 'unit': 'cfu/ml'})."
    )
    attachment = models.FileField(
        upload_to='health/lab_samples/%Y/%m/',
        null=True, blank=True,
        help_text="File attachment for the lab report (e.g., PDF)."
    )
    notes = models.TextField(
        null=True, blank=True,
        help_text="Additional notes or comments by the veterinarian."
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True, # User might be deactivated
        related_name='recorded_lab_samples',
        help_text="User who recorded this lab sample result."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sample_date', '-created_at']
        verbose_name = "Health Lab Sample"
        verbose_name_plural = "Health Lab Samples"

    def __str__(self):
        identifier = self.lab_reference_id if self.lab_reference_id else str(self.pk)
        if self.batch_container_assignment and \
           self.batch_container_assignment.batch and \
           self.batch_container_assignment.container:
            return (f"Sample {identifier} for Batch {self.batch_container_assignment.batch.batch_number} "
                    f"in Container {self.batch_container_assignment.container.name} on {self.sample_date}")
        return f"Sample {identifier} on {self.sample_date} (assignment details missing)"

    def clean(self):
        super().clean()
        if self.sample_date and self.date_sent_to_lab and self.sample_date > self.date_sent_to_lab:
            raise ValidationError({'sample_date': "Sample date cannot be after the date sent to lab."})
        if self.date_sent_to_lab and self.date_results_received and self.date_results_received < self.date_sent_to_lab:
            raise ValidationError({'date_results_received': "Date results received cannot be before the date sent to lab."})

    def get_attachment_upload_path(instance, filename):
        """Generate file path for new attachments."""
