"""
Base filter classes for batch app.

These provide common filtering functionality that can be shared across viewsets.
"""
import django_filters as filters
from django_filters import rest_framework as rest_filters


class BatchBaseFilter(rest_filters.FilterSet):
    """
    Base filter class for batch-related models.

    Provides common filtering patterns used across batch viewsets.
    """

    class Meta:
        fields = []
