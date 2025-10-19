"""
Batch transfer workflow filters.

These filters provide advanced filtering for batch transfer workflow endpoints.
"""
import django_filters as filters
from django_filters import rest_framework as rest_filters
from apps.batch.models import BatchTransferWorkflow


class BatchTransferWorkflowFilter(rest_filters.FilterSet):
    """
    Advanced filter class for BatchTransferWorkflow model.

    Provides comprehensive filtering options for workflow tracking.
    """

    # Date range filters
    planned_start_after = filters.DateFilter(
        field_name='planned_start_date',
        lookup_expr='gte'
    )
    planned_start_before = filters.DateFilter(
        field_name='planned_start_date',
        lookup_expr='lte'
    )
    actual_start_after = filters.DateFilter(
        field_name='actual_start_date',
        lookup_expr='gte'
    )
    actual_start_before = filters.DateFilter(
        field_name='actual_start_date',
        lookup_expr='lte'
    )

    # Workflow type filter
    workflow_type_in = filters.MultipleChoiceFilter(
        field_name='workflow_type',
        choices=BatchTransferWorkflow.WORKFLOW_TYPE_CHOICES,
        lookup_expr='in'
    )

    # Status filter
    status_in = filters.MultipleChoiceFilter(
        field_name='status',
        choices=BatchTransferWorkflow.STATUS_CHOICES,
        lookup_expr='in'
    )

    # Batch relationship filters
    batch_number = filters.CharFilter(
        field_name='batch__batch_number',
        lookup_expr='icontains'
    )

    # Progress filters
    completion_min = filters.NumberFilter(
        field_name='completion_percentage',
        lookup_expr='gte'
    )
    completion_max = filters.NumberFilter(
        field_name='completion_percentage',
        lookup_expr='lte'
    )

    # Subsidiary filters
    source_subsidiary = filters.CharFilter(
        field_name='source_subsidiary',
        lookup_expr='iexact'
    )
    dest_subsidiary = filters.CharFilter(
        field_name='dest_subsidiary',
        lookup_expr='iexact'
    )

    class Meta:
        model = BatchTransferWorkflow
        fields = [
            'batch',
            'workflow_type',
            'status',
            'is_intercompany',
            'source_lifecycle_stage',
            'dest_lifecycle_stage',
            'initiated_by',
            'completed_by',
            'planned_start_after',
            'planned_start_before',
            'actual_start_after',
            'actual_start_before',
            'workflow_type_in',
            'status_in',
            'batch_number',
            'completion_min',
            'completion_max',
            'source_subsidiary',
            'dest_subsidiary',
        ]
