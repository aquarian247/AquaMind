"""
Viewset mixins for the Health app.

This module provides reusable mixins for viewsets in the Health app,
focusing on common patterns like user assignment, filtering, and
optimized queryset loading.
"""

from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response


class UserAssignmentMixin:
    """
    Mixin for automatically assigning the current user to a model instance.
    
    This mixin provides a perform_create method that sets the user field
    to the authenticated user making the request.
    """
    user_field = 'user'  # Default field name, can be overridden in subclasses
    
    def perform_create(self, serializer):
        """
        Set the user field to the authenticated user making the request.
        
        Args:
            serializer: The serializer instance being used to create the object
        """
        if self.request.user.is_authenticated:
            kwargs = {self.user_field: self.request.user}
            serializer.save(**kwargs)
        else:
            serializer.save()


class OptimizedQuerysetMixin:
    """
    Mixin for optimizing querysets with select_related and prefetch_related.
    
    This mixin provides a get_queryset method that applies select_related and
    prefetch_related to the base queryset to reduce database queries.
    """
    select_related_fields = []  # Fields to use with select_related
    prefetch_related_fields = []  # Fields to use with prefetch_related
    
    def get_queryset(self):
        """
        Apply select_related and prefetch_related to the base queryset.
        
        Returns:
            QuerySet: The optimized queryset
        """
        queryset = super().get_queryset()
        
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        
        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)
        
        return queryset


class StandardFilterMixin:
    """
    Mixin for standardizing filtering across viewsets.
    
    This mixin sets up DjangoFilterBackend and SearchFilter for consistent
    filtering behavior across viewsets.
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = {}  # Override in subclasses
    search_fields = []  # Override in subclasses
    
    def get_filterset_fields(self):
        """
        Get the filterset fields for this viewset.
        
        Returns:
            dict: The filterset fields
        """
        return self.filterset_fields


class CalculateAggregatesMixin:
    """
    Mixin for adding a calculate-aggregates action to viewsets.
    
    This mixin provides an action that triggers the calculation of aggregate
    metrics for a model instance.
    """
    
    @action(detail=True, methods=['post'], url_path='calculate-aggregates')
    def calculate_aggregates(self, request, pk=None):
        """
        Trigger the calculation of aggregate metrics for a model instance.
        
        Args:
            request: The request object
            pk: The primary key of the instance
            
        Returns:
            Response: The serialized instance after calculation
        """
        instance = self.get_object()
        
        # Call the calculate_aggregate_metrics method if it exists
        if hasattr(instance, 'calculate_aggregate_metrics'):
            instance.calculate_aggregate_metrics()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
