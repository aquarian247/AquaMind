"""
Models for the Scenario Planning and Simulation module.

This module enables aquaculture managers to create, manage, and analyze
hypothetical scenarios for salmon farming operations using configurable
biological models (TGC, FCR, and mortality models).
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from simple_history.models import HistoricalRecords

User = get_user_model()


# Lifecycle stage choices for scenario planning
class LifecycleStageChoices(models.TextChoices):
    EGG = 'egg', 'Egg'
    ALEVIN = 'alevin', 'Alevin'
    FRY = 'fry', 'Fry'
    PARR = 'parr', 'Parr'
    SMOLT = 'smolt', 'Smolt'
    POST_SMOLT = 'post_smolt', 'Post-Smolt'
    HARVEST = 'harvest', 'Harvest'


class TemperatureProfile(models.Model):
    """
    Temperature profile for use in TGC (Thermal Growth Coefficient) models.
    
    Stores temperature data patterns that can be reused across multiple
    TGC models for different locations and release periods.
    """
    profile_id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Descriptive name (e.g., 'Faroe Islands Winter')"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Temperature Profile"
        verbose_name_plural = "Temperature Profiles"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class TemperatureReading(models.Model):
    """
    Individual temperature reading for a temperature profile.
    
    Stores daily temperature values that make up a complete temperature profile.
    """
    reading_id = models.BigAutoField(primary_key=True)
    profile = models.ForeignKey(
        TemperatureProfile,
        on_delete=models.CASCADE,
        related_name='readings'
    )
    reading_date = models.DateField(
        help_text="Date of the temperature reading"
    )
    temperature = models.FloatField(
        help_text="Temperature value in degrees Celsius (e.g., 12.5)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Temperature Reading"
        verbose_name_plural = "Temperature Readings"
        ordering = ['profile', 'reading_date']
        unique_together = ['profile', 'reading_date']
    
    def __str__(self):
        return f"{self.profile.name} - {self.reading_date}: {self.temperature}°C"


class TGCModel(models.Model):
    """
    Thermal Growth Coefficient (TGC) model for calculating daily growth.
    
    TGC models calculate daily growth increments based on temperature and time,
    critical for projecting salmon weight gain across lifecycle stages.
    Includes history tracking for reproducibility.
    """
    model_id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Model name (e.g., 'Scotland April TGC')"
    )
    location = models.CharField(
        max_length=255,
        help_text="Location (e.g., 'Scotland Site 1')"
    )
    release_period = models.CharField(
        max_length=255,
        help_text="Release timing (e.g., 'April')"
    )
    tgc_value = models.FloatField(
        help_text="TGC coefficient (e.g., 0.025)",
        validators=[MinValueValidator(0)]
    )
    exponent_n = models.FloatField(
        help_text="Temperature exponent (e.g., 0.33)",
        default=0.33
    )
    exponent_m = models.FloatField(
        help_text="Weight exponent (e.g., 0.66)",
        default=0.66
    )
    profile = models.ForeignKey(
        TemperatureProfile,
        on_delete=models.PROTECT,
        related_name='tgc_models'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # History tracking for regulatory compliance
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = "TGC Model"
        verbose_name_plural = "TGC Models"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.location})"


class FCRModel(models.Model):
    """
    Feed Conversion Ratio (FCR) model for estimating feed efficiency.
    
    FCR models define the ratio of feed consumed to weight gained per
    lifecycle stage. Includes history tracking for compliance.
    """
    model_id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Model name (e.g., 'Standard FCR')"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # History tracking for regulatory compliance
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = "FCR Model"
        verbose_name_plural = "FCR Models"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class FCRModelStage(models.Model):
    """
    Stage-specific FCR values for an FCR model.
    
    Links FCR values to specific lifecycle stages with duration information.
    """
    model = models.ForeignKey(
        FCRModel,
        on_delete=models.CASCADE,
        related_name='stages'
    )
    stage = models.ForeignKey(
        'batch.LifecycleStage',
        on_delete=models.PROTECT,
        related_name='fcr_stages'
    )
    fcr_value = models.FloatField(
        help_text="FCR for the stage (e.g., 1.2)",
        validators=[MinValueValidator(0)]
    )
    duration_days = models.IntegerField(
        help_text="Stage duration in days (e.g., 90)",
        validators=[MinValueValidator(1)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "FCR Model Stage"
        verbose_name_plural = "FCR Model Stages"
        ordering = ['model', 'stage']
        unique_together = ['model', 'stage']
    
    def __str__(self):
        return f"{self.model.name} - {self.stage.name}: {self.fcr_value}"


class MortalityModel(models.Model):
    """
    Mortality model for estimating population decline over time.
    
    Uses percentage-based rates applied daily or weekly.
    Includes history tracking for compliance.
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ]
    
    model_id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Model name (e.g., 'Low Mortality')"
    )
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        help_text="Rate application frequency"
    )
    rate = models.FloatField(
        help_text="Mortality rate percentage (e.g., 0.1)",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # History tracking for regulatory compliance
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = "Mortality Model"
        verbose_name_plural = "Mortality Models"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.rate}% {self.frequency})"


class Scenario(models.Model):
    """
    Scenario configuration for salmon farming projections.
    
    Combines TGC, FCR, and mortality models with initial conditions
    to simulate farming outcomes. Includes history tracking.
    """
    scenario_id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        max_length=255,
        help_text="Scenario name (e.g., 'Scotland April Sim')"
    )
    start_date = models.DateField(
        help_text="Simulation start date"
    )
    duration_days = models.IntegerField(
        help_text="Total simulation days (e.g., 900)",
        validators=[MinValueValidator(1)]
    )
    initial_count = models.IntegerField(
        help_text="Initial fish count (e.g., 10000)",
        validators=[MinValueValidator(1)]
    )
    genotype = models.CharField(
        max_length=255,
        help_text="Fish genotype (e.g., 'SalmoBreed')"
    )
    supplier = models.CharField(
        max_length=255,
        help_text="Fish supplier (e.g., 'AquaGen')"
    )
    initial_weight = models.FloatField(
        null=True,
        blank=True,
        help_text="Initial weight in grams (e.g., 50)",
        validators=[MinValueValidator(0)]
    )
    tgc_model = models.ForeignKey(
        TGCModel,
        on_delete=models.PROTECT,
        related_name='scenarios'
    )
    fcr_model = models.ForeignKey(
        FCRModel,
        on_delete=models.PROTECT,
        related_name='scenarios'
    )
    mortality_model = models.ForeignKey(
        MortalityModel,
        on_delete=models.PROTECT,
        related_name='scenarios'
    )
    batch = models.ForeignKey(
        'batch.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scenarios',
        help_text="Optional link to existing batch for real-data initialization"
    )
    biological_constraints = models.ForeignKey(
        'BiologicalConstraints',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Biological constraints to use for validation"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_scenarios'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # History tracking for regulatory compliance
    history = HistoricalRecords()
    
    class Meta:
        db_table = 'scenario'
        verbose_name = 'Scenario'
        verbose_name_plural = 'Scenarios'
        ordering = ['-created_at', 'name']
        indexes = [
            models.Index(fields=['start_date']),
            models.Index(fields=['created_by']),
        ]
    
    def clean(self):
        """Validate scenario configuration."""
        from django.core.exceptions import ValidationError
        
        # If biological constraints are set, use them for validation
        if self.biological_constraints and self.initial_weight:
            # Try to determine lifecycle stage from weight
            stage_constraints = self.biological_constraints.stage_constraints.all()
            valid_stage_found = False
            
            for constraint in stage_constraints:
                if constraint.min_weight_g <= self.initial_weight <= constraint.max_weight_g:
                    valid_stage_found = True
                    # Check freshwater limits if applicable
                    if (self.tgc_model and 'freshwater' in self.tgc_model.location.lower() and
                        constraint.max_freshwater_weight_g and 
                        self.initial_weight > constraint.max_freshwater_weight_g):
                        raise ValidationError({
                            'initial_weight': f'Initial weight {self.initial_weight}g exceeds freshwater limit '
                                            f'of {constraint.max_freshwater_weight_g}g for {constraint.get_lifecycle_stage_display()}'
                        })
                    break
            
            if not valid_stage_found:
                raise ValidationError({
                    'initial_weight': f'Initial weight {self.initial_weight}g does not match any lifecycle stage '
                                    f'in constraint set "{self.biological_constraints.name}"'
                })
        else:
            # Fallback to basic validation if no constraints set
            if self.initial_weight is not None and self.initial_weight < 0.1:
                raise ValidationError({
                    'initial_weight': 'Initial weight too low. Minimum is 0.1g (egg stage).'
                })
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ScenarioModelChange(models.Model):
    """
    Mid-scenario model changes for dynamic adjustments.
    
    Allows switching TGC, FCR, or mortality models during a scenario.
    Includes history tracking for change documentation.
    """
    change_id = models.BigAutoField(primary_key=True)
    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name='model_changes'
    )
    change_day = models.IntegerField(
        help_text="Day of change (e.g., 180). Day 1 is the first simulation day.",
        validators=[MinValueValidator(1)]
    )
    new_tgc_model = models.ForeignKey(
        TGCModel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='scenario_changes'
    )
    new_fcr_model = models.ForeignKey(
        FCRModel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='scenario_changes'
    )
    new_mortality_model = models.ForeignKey(
        MortalityModel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='scenario_changes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # History tracking for regulatory compliance
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = "Scenario Model Change"
        verbose_name_plural = "Scenario Model Changes"
        ordering = ['scenario', 'change_day']
    
    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def clean(self):
        """
        Validate scenario model change configuration.
        
        Ensures:
        1. At least one model is being changed
        2. Change day is valid (>= 1, as day 0 is before simulation starts)
        3. Change day doesn't exceed scenario duration
        """
        from django.core.exceptions import ValidationError

        errors = {}

        # Check that at least one model is being changed
        if not any([
            self.new_tgc_model,
            self.new_fcr_model,
            self.new_mortality_model
        ]):
            errors['__all__'] = (
                "At least one of new_tgc_model, new_fcr_model, or "
                "new_mortality_model must be specified for a model change."
            )

        # Validate change_day is at least 1 (day 0 is before sim starts)
        if self.change_day is not None and self.change_day < 1:
            errors['change_day'] = (
                "Change day must be at least 1. Day 1 is the first "
                "simulation day; day 0 is before the simulation starts."
            )

        # Validate change_day doesn't exceed scenario duration
        if self.scenario_id and self.change_day:
            try:
                scenario = self.scenario
                if self.change_day > scenario.duration_days:
                    errors['change_day'] = (
                        f"Change day {self.change_day} exceeds scenario "
                        f"duration of {scenario.duration_days} days"
                    )
            except Exception:
                pass  # Scenario not yet loaded

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.scenario.name} - Day {self.change_day} change"


class ScenarioProjection(models.Model):
    """
    Daily projection data for a scenario.
    
    Stores calculated daily values for weight, population, biomass,
    and feed consumption. Consider TimescaleDB for large datasets.
    """
    projection_id = models.BigAutoField(primary_key=True)
    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name='projections'
    )
    projection_date = models.DateField(
        help_text="Projection date"
    )
    day_number = models.IntegerField(
        help_text="Day offset from start (e.g., 45)",
        validators=[MinValueValidator(0)]
    )
    average_weight = models.FloatField(
        help_text="Fish weight in grams (e.g., 250.5)",
        validators=[MinValueValidator(0)]
    )
    population = models.FloatField(
        help_text="Fish count (e.g., 9950.3)",
        validators=[MinValueValidator(0)]
    )
    biomass = models.FloatField(
        help_text="Biomass in kilograms (e.g., 2491.2)",
        validators=[MinValueValidator(0)]
    )
    daily_feed = models.FloatField(
        help_text="Daily feed in kilograms (e.g., 30.5)",
        validators=[MinValueValidator(0)]
    )
    cumulative_feed = models.FloatField(
        help_text="Total feed in kilograms (e.g., 1200.7)",
        validators=[MinValueValidator(0)]
    )
    temperature = models.FloatField(
        help_text="Temperature in Celsius (e.g., 12.8)"
    )
    current_stage = models.ForeignKey(
        'batch.LifecycleStage',
        on_delete=models.PROTECT,
        related_name='scenario_projections'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Scenario Projection"
        verbose_name_plural = "Scenario Projections"
        ordering = ['scenario', 'day_number']
        indexes = [
            models.Index(fields=['scenario', 'projection_date']),
            models.Index(fields=['scenario', 'day_number']),
        ]
    
    def __str__(self):
        return f"{self.scenario.name} - Day {self.day_number}: {self.average_weight:.1f}g"


# Biological Configuration Models
class BiologicalConstraints(models.Model):
    """Configurable biological constraints for lifecycle stages"""
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name for this constraint set (e.g., 'Bakkafrost Standard', 'Conservative')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this constraint set"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this constraint set is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_constraints'
    )
    
    class Meta:
        db_table = 'scenario_biological_constraints'
        verbose_name = "Biological Constraint Set"
        verbose_name_plural = "Biological Constraint Sets"
        permissions = [
            ("can_manage_biological_constraints", "Can manage biological constraints"),
        ]
    
    def __str__(self):
        return self.name


class StageConstraint(models.Model):
    """Stage-specific biological constraints"""
    constraint_set = models.ForeignKey(
        BiologicalConstraints,
        on_delete=models.CASCADE,
        related_name='stage_constraints'
    )
    lifecycle_stage = models.CharField(
        max_length=20,
        choices=LifecycleStageChoices.choices
    )
    min_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Minimum weight for this stage in grams"
    )
    max_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Maximum weight for this stage in grams"
    )
    min_temperature_c = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum optimal temperature for this stage"
    )
    max_temperature_c = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum optimal temperature for this stage"
    )
    typical_duration_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Typical duration in this stage (days)"
    )
    max_freshwater_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum weight allowed in freshwater for this stage"
    )
    
    class Meta:
        db_table = 'scenario_stage_constraint'
        unique_together = ['constraint_set', 'lifecycle_stage']
    
    def __str__(self):
        return f"{self.constraint_set.name} - {self.get_lifecycle_stage_display()}"

    # ---------------------------------------------------------------------
    # Validation
    # ---------------------------------------------------------------------
    def clean(self):
        """
        Ensure that the numeric range fields are logically correct.

        1. min_weight_g must be less than max_weight_g
        2. If temperature bounds are provided, min_temperature_c must be
           less than max_temperature_c
        """
        from django.core.exceptions import ValidationError

        errors = {}

        # Weight range validation
        if (
            self.min_weight_g is not None
            and self.max_weight_g is not None
            and self.min_weight_g >= self.max_weight_g
        ):
            errors["min_weight_g"] = (
                "min_weight_g must be less than max_weight_g."
            )

        # Temperature range validation (only if both provided)
        if (
            self.min_temperature_c is not None
            and self.max_temperature_c is not None
            and self.min_temperature_c >= self.max_temperature_c
        ):
            errors["min_temperature_c"] = (
                "min_temperature_c must be less than max_temperature_c."
            )

        if errors:
            raise ValidationError(errors)


# Stage-specific parameter models
class TGCModelStage(models.Model):
    """Stage-specific TGC values"""
    tgc_model = models.ForeignKey(
        TGCModel,
        on_delete=models.CASCADE,
        related_name='stage_overrides'
    )
    lifecycle_stage = models.CharField(
        max_length=20,
        choices=LifecycleStageChoices.choices
    )
    tgc_value = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        help_text="TGC value for this specific stage"
    )
    temperature_exponent = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.0,
        help_text="Temperature exponent (n) for this stage"
    )
    weight_exponent = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.333,
        help_text="Weight exponent (m) for this stage"
    )
    
    class Meta:
        db_table = 'scenario_tgc_model_stage'
        unique_together = ['tgc_model', 'lifecycle_stage']
    
    def __str__(self):
        return f"{self.tgc_model.name} - {self.get_lifecycle_stage_display()}"


class FCRModelStageOverride(models.Model):
    """Additional stage-specific FCR overrides"""
    fcr_stage = models.ForeignKey(
        FCRModelStage,
        on_delete=models.CASCADE,
        related_name='overrides'
    )
    min_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Minimum weight for this FCR value"
    )
    max_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Maximum weight for this FCR value"
    )
    fcr_value = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        help_text="FCR value for this weight range"
    )
    
    class Meta:
        db_table = 'scenario_fcr_model_stage_override'
        ordering = ['min_weight_g']
    
    def __str__(self):
        return f"{self.fcr_stage} ({self.min_weight_g}g-{self.max_weight_g}g): {self.fcr_value}"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def clean(self):
        """
        Ensure the minimum weight bound is less than the maximum weight bound.
        """
        from django.core.exceptions import ValidationError

        if (
            self.min_weight_g is not None
            and self.max_weight_g is not None
            and self.min_weight_g >= self.max_weight_g
        ):
            raise ValidationError(
                {
                    "min_weight_g": "min_weight_g must be less than max_weight_g."
                }
            )


class MortalityModelStage(models.Model):
    """Stage-specific mortality rates"""
    mortality_model = models.ForeignKey(
        MortalityModel,
        on_delete=models.CASCADE,
        related_name='stage_overrides'
    )
    lifecycle_stage = models.CharField(
        max_length=20,
        choices=LifecycleStageChoices.choices
    )
    daily_rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        help_text="Daily mortality rate as percentage for this stage"
    )
    weekly_rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Weekly mortality rate as percentage (calculated if not provided)"
    )
    
    class Meta:
        db_table = 'scenario_mortality_model_stage'
        unique_together = ['mortality_model', 'lifecycle_stage']
    
    def save(self, *args, **kwargs):
        # Calculate weekly rate if not provided
        if self.daily_rate_percent and not self.weekly_rate_percent:
            daily_survival = 1 - (self.daily_rate_percent / 100)
            weekly_survival = daily_survival ** 7
            self.weekly_rate_percent = (1 - weekly_survival) * 100
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.mortality_model.name} - {self.get_lifecycle_stage_display()}"



