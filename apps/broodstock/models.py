"""
Models for the Broodstock Management app.

This module contains models for managing broodstock containers, fish populations,
breeding operations, egg production/acquisition, and batch traceability.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.infrastructure.models import Container, FreshwaterStation
from apps.batch.models import Batch

User = get_user_model()


class MaintenanceTask(models.Model):
    """
    Tracks maintenance tasks for broodstock containers.
    
    Manages scheduled and completed maintenance activities such as cleaning,
    repairs, inspections, and equipment upgrades for broodstock containers.
    """
    
    TASK_TYPE_CHOICES = [
        ('cleaning', 'Cleaning'),
        ('repair', 'Repair'),
        ('inspection', 'Inspection'),
        ('upgrade', 'Equipment Upgrade'),
    ]
    
    container = models.ForeignKey(
        Container,
        on_delete=models.CASCADE,
        related_name='maintenance_tasks',
        help_text="Container requiring maintenance"
    )
    task_type = models.CharField(
        max_length=50,
        choices=TASK_TYPE_CHOICES,
        help_text="Type of maintenance task"
    )
    scheduled_date = models.DateTimeField(
        help_text="Planned execution date"
    )
    completed_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual completion date"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional details about the task"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_maintenance_tasks'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_date']
        verbose_name = "Maintenance Task"
        verbose_name_plural = "Maintenance Tasks"
    
    def __str__(self):
        return f"{self.get_task_type_display()} - {self.container.name} ({self.scheduled_date.date()})"
    
    @property
    def is_overdue(self):
        """Check if the task is overdue."""
        if self.completed_date:
            return False
        return timezone.now() > self.scheduled_date


class BroodstockFish(models.Model):
    """
    Represents individual broodstock fish.
    
    Tracks individual fish within broodstock containers, including their
    traits, health status, and breeding history.
    """
    
    HEALTH_STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('monitored', 'Monitored'),
        ('sick', 'Sick'),
        ('deceased', 'Deceased'),
    ]
    
    container = models.ForeignKey(
        Container,
        on_delete=models.PROTECT,
        related_name='broodstock_fish',
        help_text="Current container housing the fish"
    )
    traits = models.JSONField(
        default=dict,
        blank=True,
        help_text="Basic traits (e.g., growth_rate, size)"
    )
    health_status = models.CharField(
        max_length=20,
        choices=HEALTH_STATUS_CHOICES,
        default='healthy',
        help_text="Current health status"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add history tracking
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = "Broodstock Fish"
        verbose_name_plural = "Broodstock Fish"
    
    def __str__(self):
        return f"Fish #{self.id} in {self.container.name}"


class FishMovement(models.Model):
    """
    Records movements of broodstock fish between containers.
    
    Maintains a complete audit trail of fish transfers, including source
    and destination containers, movement dates, and responsible users.
    """
    
    fish = models.ForeignKey(
        BroodstockFish,
        on_delete=models.CASCADE,
        related_name='movements'
    )
    from_container = models.ForeignKey(
        Container,
        on_delete=models.PROTECT,
        related_name='fish_movements_from'
    )
    to_container = models.ForeignKey(
        Container,
        on_delete=models.PROTECT,
        related_name='fish_movements_to'
    )
    movement_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time of movement",
        db_index=True
    )
    moved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='fish_movements'
    )
    notes = models.TextField(
        blank=True,
        help_text="Details about the movement"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add history tracking
    history = HistoricalRecords()
    
    class Meta:
        ordering = ['-movement_date']
        verbose_name = "Fish Movement"
        verbose_name_plural = "Fish Movements"
    
    def __str__(self):
        return f"Fish #{self.fish.id}: {self.from_container.name} → {self.to_container.name}"
    
    def save(self, *args, **kwargs):
        """Update fish container on movement."""
        if not self.pk:  # New movement
            self.fish.container = self.to_container
            self.fish.save()
        super().save(*args, **kwargs)


class BreedingPlan(models.Model):
    """
    Defines breeding strategies and objectives.
    
    Manages breeding plans with specific timeframes and objectives for
    optimizing egg production and genetic traits.
    """
    
    name = models.CharField(
        max_length=100,
        help_text="Plan name (e.g., 'Winter 2023 Breeding')"
    )
    start_date = models.DateTimeField(
        help_text="Plan start date"
    )
    end_date = models.DateTimeField(
        help_text="Plan end date"
    )
    objectives = models.TextField(
        blank=True,
        help_text="Plan objectives and goals"
    )
    geneticist_notes = models.TextField(
        blank=True,
        help_text="Technical notes from geneticist about breeding priorities and trait selection"
    )
    breeder_instructions = models.TextField(
        blank=True,
        help_text="Clear instructions for breeders on execution of the breeding plan"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='breeding_plans'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = "Breeding Plan"
        verbose_name_plural = "Breeding Plans"
    
    def __str__(self):
        return self.name
    
    @property
    def is_active(self):
        """Check if the plan is currently active."""
        now = timezone.now()
        return self.start_date <= now <= self.end_date


class BreedingTraitPriority(models.Model):
    """
    Defines trait priorities for breeding plans.
    
    Specifies which traits to prioritize and their relative weights
    for breeding pair selection.
    """
    
    TRAIT_CHOICES = [
        ('growth_rate', 'Growth Rate'),
        ('disease_resistance', 'Disease Resistance'),
        ('size', 'Size'),
        ('fertility', 'Fertility'),
    ]
    
    plan = models.ForeignKey(
        BreedingPlan,
        on_delete=models.CASCADE,
        related_name='trait_priorities'
    )
    trait_name = models.CharField(
        max_length=50,
        choices=TRAIT_CHOICES,
        help_text="Trait to prioritize"
    )
    priority_weight = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Weight from 0 to 1 (e.g., 0.7)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['plan', 'trait_name']
        ordering = ['-priority_weight']
        verbose_name = "Breeding Trait Priority"
        verbose_name_plural = "Breeding Trait Priorities"
    
    def __str__(self):
        return f"{self.plan.name} - {self.get_trait_name_display()}: {self.priority_weight}"


class BreedingPair(models.Model):
    """
    Represents breeding pair assignments.
    
    Links male and female broodstock fish for breeding, tracking pairing
    dates and offspring production.
    """
    
    plan = models.ForeignKey(
        BreedingPlan,
        on_delete=models.CASCADE,
        related_name='breeding_pairs'
    )
    male_fish = models.ForeignKey(
        BroodstockFish,
        on_delete=models.PROTECT,
        related_name='breeding_pairs_as_male'
    )
    female_fish = models.ForeignKey(
        BroodstockFish,
        on_delete=models.PROTECT,
        related_name='breeding_pairs_as_female'
    )
    pairing_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date of pairing"
    )
    progeny_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of offspring produced"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add history tracking
    history = HistoricalRecords()
    
    class Meta:
        unique_together = ['plan', 'male_fish', 'female_fish']
        ordering = ['-pairing_date']
        verbose_name = "Breeding Pair"
        verbose_name_plural = "Breeding Pairs"
    
    def __str__(self):
        return f"Pair: Male #{self.male_fish.id} × Female #{self.female_fish.id}"


class EggProduction(models.Model):
    """
    Tracks egg production from internal breeding or external acquisition.
    
    Central model for all egg batches, whether produced internally from
    breeding pairs or acquired from external suppliers.
    """
    
    SOURCE_TYPE_CHOICES = [
        ('internal', 'Internal'),
        ('external', 'External'),
    ]
    
    pair = models.ForeignKey(
        BreedingPair,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='egg_productions',
        help_text="Breeding pair (null for external eggs)"
    )
    egg_batch_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique egg batch identifier"
    )
    egg_count = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Number of eggs"
    )
    production_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date produced or acquired"
    )
    destination_station = models.ForeignKey(
        FreshwaterStation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='egg_productions',
        help_text="Destination freshwater station"
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        help_text="Internal or external source"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add history tracking
    history = HistoricalRecords()
    
    class Meta:
        ordering = ['-production_date']
        verbose_name = "Egg Production"
        verbose_name_plural = "Egg Productions"
    
    def __str__(self):
        return f"{self.egg_batch_id} - {self.egg_count} eggs ({self.source_type})"
    
    def clean(self):
        """Validate that internal eggs have a breeding pair."""
        from django.core.exceptions import ValidationError
        if self.source_type == 'internal' and not self.pair:
            raise ValidationError("Internal egg production must have a breeding pair.")
        if self.source_type == 'external' and self.pair:
            raise ValidationError("External egg production cannot have a breeding pair.")


class EggSupplier(models.Model):
    """
    Represents external egg suppliers.
    
    Maintains information about third-party suppliers providing eggs
    for aquaculture operations.
    """
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Supplier name"
    )
    contact_details = models.TextField(
        help_text="Contact information (phone, email, address)"
    )
    certifications = models.TextField(
        blank=True,
        help_text="Certifications and quality standards"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Egg Supplier"
        verbose_name_plural = "Egg Suppliers"
    
    def __str__(self):
        return self.name


class ExternalEggBatch(models.Model):
    """
    Tracks external egg acquisitions.
    
    Records details about egg batches acquired from external suppliers,
    including batch numbers and provenance data.
    """
    
    egg_production = models.OneToOneField(
        EggProduction,
        on_delete=models.CASCADE,
        related_name='external_batch',
        help_text="Link to egg production record"
    )
    supplier = models.ForeignKey(
        EggSupplier,
        on_delete=models.PROTECT,
        related_name='egg_batches'
    )
    batch_number = models.CharField(
        max_length=50,
        help_text="Supplier's batch ID"
    )
    provenance_data = models.TextField(
        blank=True,
        help_text="Source farm and transport details"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "External Egg Batch"
        verbose_name_plural = "External Egg Batches"
    
    def __str__(self):
        return f"{self.supplier.name} - {self.batch_number}"


class BatchParentage(models.Model):
    """
    Links egg batches to production batches.
    
    Provides traceability from eggs (internal or external) to fish batches,
    supporting regulatory compliance and quality tracking.
    """
    
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='parentage'
    )
    egg_production = models.ForeignKey(
        EggProduction,
        on_delete=models.PROTECT,
        related_name='batch_assignments'
    )
    assignment_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date eggs assigned to batch"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add history tracking
    history = HistoricalRecords()
    
    class Meta:
        unique_together = ['batch', 'egg_production']
        ordering = ['-assignment_date']
        verbose_name = "Batch Parentage"
        verbose_name_plural = "Batch Parentages"
    
    def __str__(self):
        return f"Batch {self.batch.batch_number} ← {self.egg_production.egg_batch_id}"
