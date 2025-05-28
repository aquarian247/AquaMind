"""
Vaccination models for health monitoring.

This module defines models related to vaccinations.
"""

from django.db import models


class VaccinationType(models.Model):
    """Model for defining types of vaccinations."""
    name = models.CharField(max_length=100, unique=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    dosage = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Vaccination Types"
        ordering = ['name']

    def __str__(self):
        """Return a string representation of the vaccination type."""
        return self.name
