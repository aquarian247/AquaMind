"""
History API Utilities for AquaMind

This module provides reusable classes for implementing history API endpoints
across all apps in the AquaMind project. These utilities ensure consistent
filtering, pagination, and serialization for historical data access.

Classes:
    - HistoryFilter: Base filter class for history endpoints
    - HistoryPagination: Pagination class optimized for history data
    - HistorySerializer: Base serializer for history records
    - HistoryViewSetMixin: Mixin for history viewsets
"""

import django_filters as filters
from django_filters import rest_framework as rest_filters


class HistoryFilter(filters.FilterSet):
    """
    Base filter class for history endpoints.

    Provides common filters for all history viewsets:
    - date_from: Filter by history_date >= date_from
    - date_to: Filter by history_date <= date_to
    - history_user: Filter by history_user username
    - history_type: Filter by history_type (+, ~, -)

    Usage:
        class MyModelHistoryFilter(HistoryFilter):
            class Meta:
                model = MyModel.history.model
                fields = '__all__'
    """

    date_from = filters.DateTimeFilter(
        field_name='history_date',
        lookup_expr='gte',
        help_text="Filter records from this date onwards (inclusive)"
    )
    date_to = filters.DateTimeFilter(
        field_name='history_date',
        lookup_expr='lte',
        help_text="Filter records up to this date (inclusive)"
    )
    history_user = filters.CharFilter(
        field_name='history_user__username',
        lookup_expr='icontains',
        help_text="Filter by username of the user who made the change"
    )
    history_type = filters.ChoiceFilter(
        choices=[
            ('+', 'Created'),
            ('~', 'Updated'),
            ('-', 'Deleted')
        ],
        field_name='history_type',
        help_text="Filter by type of change: + (Created), ~ (Updated), - (Deleted)"
    )


class HistoryPagination:
    """
    Pagination class optimized for history data.

    Uses a default page size of 25 items, which is suitable for
    most history browsing use cases. Allows customization via
    query parameters.
    """

    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

    def __init__(self):
        # Import here to avoid Django settings requirement at module level
        from rest_framework.pagination import PageNumberPagination
        self._pagination_class = PageNumberPagination
        self._pagination_class.page_size = self.page_size
        self._pagination_class.page_size_query_param = self.page_size_query_param
        self._pagination_class.max_page_size = self.max_page_size

    def __getattr__(self, name):
        return getattr(self._pagination_class, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            setattr(self._pagination_class, name, value)


class HistorySerializer:
    """
    Base serializer for history records.

    Provides common fields that should be exposed for all history endpoints:
    - history_user: String representation of the user who made the change
    - history_date: When the change was made
    - history_type: Type of change (+, ~, -)
    - history_change_reason: Reason for the change (if provided)

    Usage:
        class MyModelHistorySerializer(HistorySerializer):
            class Meta:
                model = MyModel.history.model
                fields = '__all__'
    """

    def __init__(self, *args, **kwargs):
        # Import here to avoid Django settings requirement at module level
        from rest_framework import serializers
        super().__init__(*args, **kwargs)

        # Add common history fields
        self.fields['history_user'] = serializers.StringRelatedField(read_only=True)
        self.fields['history_date'] = serializers.DateTimeField(read_only=True)
        self.fields['history_type'] = serializers.CharField(read_only=True)
        self.fields['history_change_reason'] = serializers.CharField(read_only=True)

    class Meta:
        fields = [
            'history_user',
            'history_date',
            'history_type',
            'history_change_reason'
        ]


class HistoryViewSetMixin:
    """
    Mixin for history viewsets.

    Provides common configuration for all history viewsets:
    - ReadOnlyModelViewSet base
    - HistoryPagination
    - Standard queryset ordering by history_date descending
    - OpenAPI documentation enhancements

    Usage:
        class MyModelHistoryViewSet(HistoryViewSetMixin, ReadOnlyModelViewSet):
            queryset = MyModel.history.all()
            serializer_class = MyModelHistorySerializer
            filterset_class = MyModelHistoryFilter
    """

    def get_queryset(self):
        """Order history records by date descending (most recent first)."""
        return super().get_queryset().order_by('-history_date')

    def list(self, request, *args, **kwargs):
        """List historical records with enhanced OpenAPI documentation."""
        return super().list(request, *args, **kwargs)


class HistoryViewSet(HistoryViewSetMixin):
    """
    Base viewset for history endpoints.

    Provides a base class for history viewsets that can be combined
    with ReadOnlyModelViewSet.

    Usage:
        class MyModelHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
            queryset = MyModel.history.all()
            serializer_class = MyModelHistorySerializer
            filterset_class = MyModelHistoryFilter
    """
    pass
