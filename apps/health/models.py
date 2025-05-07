from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

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
        help_text="Total number of individual fish examined in this sampling event."
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
