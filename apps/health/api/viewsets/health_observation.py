"""
Health observation viewsets for health monitoring.

This module defines viewsets for health observation models, including
HealthParameter, HealthSamplingEvent, IndividualFishObservation, and FishParameterScore.
"""

from rest_framework import viewsets, permissions

from apps.health.models import (
    HealthParameter,
    HealthSamplingEvent,
    IndividualFishObservation,
    FishParameterScore
)
from apps.health.api.serializers import (
    HealthParameterSerializer,
    HealthSamplingEventSerializer,
    IndividualFishObservationSerializer,
    FishParameterScoreSerializer
)
from aquamind.utils.history_mixins import HistoryReasonMixin
from ..mixins import (
    UserAssignmentMixin,
    OptimizedQuerysetMixin,
    StandardFilterMixin,
    CalculateAggregatesMixin
)


class HealthParameterViewSet(HistoryReasonMixin, StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Health Parameters.
    
    Provides CRUD operations for health parameters used in fish health assessments.
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    queryset = HealthParameter.objects.all()
    serializer_class = HealthParameterSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # StandardFilterMixin configuration
    filterset_fields = {
        'is_active': ['exact'],
        'name': ['exact', 'icontains']
    }
    search_fields = ['name', 'description_score_1', 'description_score_2', 
                     'description_score_3', 'description_score_4', 'description_score_5']


class HealthSamplingEventViewSet(HistoryReasonMixin, UserAssignmentMixin, OptimizedQuerysetMixin, 
                                StandardFilterMixin, CalculateAggregatesMixin,
                                viewsets.ModelViewSet):
    """
    API endpoint for managing Health Sampling Events.
    
    Provides CRUD operations for health sampling events, including nested
    individual fish observations and parameter scores. Also provides an
    action to calculate aggregate metrics.
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    queryset = HealthSamplingEvent.objects.all()
    serializer_class = HealthSamplingEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    user_field = 'sampled_by'  # Override the default user field name
    
    # OptimizedQuerysetMixin configuration
    select_related_fields = ['assignment__batch', 'assignment__container', 
                           'assignment__lifecycle_stage', 'sampled_by']
    prefetch_related_fields = ['individual_fish_observations__parameter_scores__parameter']
    
    # StandardFilterMixin configuration
    filterset_fields = {
        'assignment__batch__id': ['exact'],
        'assignment__container__id': ['exact'],
        'sampling_date': ['exact', 'gte', 'lte'],
        'sampled_by__id': ['exact']
    }
    search_fields = ['notes']


class IndividualFishObservationViewSet(HistoryReasonMixin, OptimizedQuerysetMixin, StandardFilterMixin, 
                                      viewsets.ModelViewSet):
    """
    API endpoint for managing Individual Fish Observations.
    
    Provides CRUD operations for individual fish observations within a health sampling event.
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    queryset = IndividualFishObservation.objects.all()
    serializer_class = IndividualFishObservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # OptimizedQuerysetMixin configuration
    select_related_fields = ['sampling_event']
    prefetch_related_fields = ['parameter_scores__parameter']
    
    # StandardFilterMixin configuration
    filterset_fields = {
        'sampling_event__id': ['exact'],
        'fish_identifier': ['exact', 'icontains']
    }


class FishParameterScoreViewSet(HistoryReasonMixin, OptimizedQuerysetMixin, StandardFilterMixin, 
                               viewsets.ModelViewSet):
    """
    API endpoint for managing Fish Parameter Scores.
    
    Provides CRUD operations for parameter scores assigned to individual fish observations.
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    queryset = FishParameterScore.objects.all()
    serializer_class = FishParameterScoreSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # OptimizedQuerysetMixin configuration
    select_related_fields = ['individual_fish_observation__sampling_event', 'parameter']
    
    # StandardFilterMixin configuration
    filterset_fields = {
        'individual_fish_observation__id': ['exact'],
        'parameter__id': ['exact'],
        'score': ['exact', 'gte', 'lte']
    }
