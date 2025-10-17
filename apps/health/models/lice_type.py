"""
Lice type lookup model for normalized lice tracking.

This module defines the LiceType model which provides a normalized lookup table
for tracking different lice species, genders, and development stages.
"""

from django.db import models
from simple_history.models import HistoricalRecords


class LiceType(models.Model):
    """
    Normalized lookup table for lice classification.

    Provides structured categorization of sea lice by species, gender,
    and development stage to support detailed regulatory reporting and
    integration with external systems like Tidal.

    Examples:
        - Lepeophtheirus salmonis, Female, Adult
        - Lepeophtheirus salmonis, Female, Pre-adult
        - Caligus elongatus, Male, Chalimus
    """

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('unknown', 'Unknown')
    ]

    species = models.CharField(
        max_length=100,
        help_text=(
            "Scientific name of the lice species "
            "(e.g., Lepeophtheirus salmonis, Caligus elongatus)."
        )
    )
    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        help_text="Gender classification of the lice."
    )
    development_stage = models.CharField(
        max_length=50,
        help_text=(
            "Development stage "
            "(e.g., copepodid, chalimus, pre-adult, adult)."
        )
    )
    description = models.TextField(
        blank=True,
        help_text=(
            "Additional description or notes about "
            "this lice type classification."
        )
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this lice type is currently tracked."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['species', 'gender', 'development_stage']]
        ordering = ['species', 'development_stage', 'gender']
        verbose_name = "Lice Type"
        verbose_name_plural = "Lice Types"
        indexes = [
            models.Index(fields=['species', 'development_stage']),
            models.Index(fields=['is_active']),
        ]

    history = HistoricalRecords()

    def __str__(self):
        """Return string representation of the lice type."""
        # Create short species name (e.g., "L. salmonis")
        species_parts = self.species.split()
        if len(species_parts) >= 2:
            short_species = (
                f"{species_parts[0][0]}. {species_parts[1]}"
            )
        else:
            short_species = self.species

        return (
            f"{short_species} - {self.gender.capitalize()} - "
            f"{self.development_stage.capitalize()}"
        )

    def clean(self):
        """Validate the lice type data."""
        from django.core.exceptions import ValidationError

        # Ensure species name is provided
        if not self.species or not self.species.strip():
            raise ValidationError({
                'species': 'Species name is required.'
            })

        # Ensure development stage is provided
        if not self.development_stage or not self.development_stage.strip():
            raise ValidationError({
                'development_stage': 'Development stage is required.'
            })

