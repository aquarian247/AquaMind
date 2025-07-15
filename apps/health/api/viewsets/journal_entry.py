"""
Journal entry viewsets for health monitoring.

This module defines viewsets for journal entry models, including
JournalEntry.
"""

from rest_framework import viewsets, permissions

from apps.health.models import JournalEntry
from apps.health.api.serializers import JournalEntrySerializer
from ..mixins import UserAssignmentMixin, OptimizedQuerysetMixin, StandardFilterMixin


class JournalEntryViewSet(UserAssignmentMixin, OptimizedQuerysetMixin, 
                         StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Journal Entries.
    
    Provides CRUD operations for journal entries, which track observations
    and notes about fish health.
    """
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # OptimizedQuerysetMixin configuration
    select_related_fields = ['batch', 'container', 'user']
    
    # StandardFilterMixin configuration
    filterset_fields = {
        'batch__id': ['exact'],
        'container__id': ['exact'],
        'entry_date': ['exact', 'gte', 'lte'],
        'category': ['exact'],
        'user__id': ['exact']
    }
    # Use the correct model field(s) that exist on JournalEntry.
    search_fields = ['description']
