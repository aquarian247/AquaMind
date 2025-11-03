"""
Journal entry viewsets for health monitoring.

This module defines viewsets for journal entry models, including
JournalEntry.
"""

from rest_framework import viewsets, permissions

from apps.health.models import JournalEntry
from apps.health.api.serializers import JournalEntrySerializer
from apps.health.api.permissions import IsHealthContributor
from aquamind.api.mixins import RBACFilterMixin
from aquamind.utils.history_mixins import HistoryReasonMixin
from ..mixins import UserAssignmentMixin, OptimizedQuerysetMixin, StandardFilterMixin


class JournalEntryViewSet(RBACFilterMixin, HistoryReasonMixin, UserAssignmentMixin, 
                         OptimizedQuerysetMixin, StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Journal Entries.
    
    Provides CRUD operations for journal entries, which track observations
    and notes about fish health. Access is restricted to Veterinarians, QA
    personnel, and Administrators.
    
    RBAC Enforcement:
    - Permission: IsHealthContributor (VET/QA/Admin only)
    - Geographic Filtering: Users only see entries for batches in their geography
    - Object-level Validation: Prevents creating/updating entries outside user's scope
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated, IsHealthContributor]
    
    # RBAC configuration - filter by geography through batch
    # JournalEntry has batch_id and optionally container_id
    # We need to filter through the batch's container assignments to get geography
    geography_filter_fields = [
        'batch__batch_assignments__container__area__geography',
        'batch__batch_assignments__container__hall__freshwater_station__geography'
    ]
    
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
