from django.db import models
from django.contrib.auth import get_user_model

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
    )
    SEVERITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )

    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name='journal_entries',
        null=True, blank=True
    )
    container = models.ForeignKey(
        Container, on_delete=models.CASCADE, related_name='journal_entries',
        null=True, blank=True
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name='journal_entries',
        null=True
    )
    entry_date = models.DateTimeField(auto_now_add=True)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default='observation'
    )
    severity = models.CharField(
        max_length=10, choices=SEVERITY_CHOICES, default='low'
    )
    description = models.TextField()
    resolution_status = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Journal Entries"
        ordering = ['-entry_date']

    def __str__(self):
        return (
            f"{self.get_category_display()} - "
            f"{self.entry_date.strftime('%Y-%m-%d')}"
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class MortalityReason(models.Model):
    """
    Model for categorizing reasons for mortality events.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Mortality Reasons"

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
        return self.treatment_date + timedelta(
            days=self.withholding_period_days
        )


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
