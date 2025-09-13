"""
FCR Trends ViewSet for Operational API.

Provides RESTful access to FCR trend data with filtering and aggregation capabilities.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from typing import Optional

from apps.operational.services.fcr_trends_service import (
    FCRTrendsService,
    TimeInterval,
    AggregationLevel
)
from apps.operational.api.serializers.fcr_trends import FCRTrendsSerializer

# Import a dummy model for queryset
from django.contrib.auth.models import User


class FCRTrendsViewSet(viewsets.GenericViewSet):
    """
    ViewSet for FCR trends data.

    Provides aggregated FCR trend analysis with actual and predicted values
    across different time intervals and aggregation levels.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FCRTrendsSerializer
    queryset = User.objects.none()  # Empty queryset to avoid schema generation warnings

    @extend_schema(
        summary="Get FCR trends data",
        description="""
        Retrieve FCR (Feed Conversion Ratio) trend data with actual and predicted values across different time intervals and aggregation levels.

        **Time Intervals:**
        - `DAILY`: Single calendar day buckets
        - `WEEKLY`: Monday-Sunday inclusive buckets
        - `MONTHLY`: Calendar month buckets (1st to last day)

        **Aggregation Levels:**
        - `batch`: Aggregate by batch ID
        - `assignment`: Aggregate by container assignment ID
        - `geography`: Aggregate across all batches in geography (default when no filters provided)

        **Defaults when no filters provided:**
        - `aggregation_level`: 'geography'
        - `interval`: 'DAILY'
        - `start_date`: 1 year ago
        - `end_date`: today

        **FCR Units:** Ratio (feed consumed kg / biomass gained kg)
        """,
        parameters=[
            OpenApiParameter(
                name='start_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Start date for the trend analysis (ISO format: YYYY-MM-DD, default: 1 year ago)',
                required=False
            ),
            OpenApiParameter(
                name='end_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='End date for the trend analysis (ISO format: YYYY-MM-DD, default: today)',
                required=False
            ),
            OpenApiParameter(
                name='interval',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Time interval for aggregation. DAILY=calendar days, WEEKLY=Monday-Sunday inclusive, MONTHLY=calendar months.',
                enum=['DAILY', 'WEEKLY', 'MONTHLY'],
                default='DAILY',
                required=False
            ),
            OpenApiParameter(
                name='batch_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Optional batch ID for batch-level aggregation. When provided, aggregation_level becomes "batch".',
                required=False
            ),
            OpenApiParameter(
                name='assignment_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Optional assignment ID for container-level aggregation. When provided, aggregation_level becomes "assignment".',
                required=False
            ),
            OpenApiParameter(
                name='geography_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Optional geography ID for geography-level aggregation. When provided, aggregation_level becomes "geography".',
                required=False
            ),
            OpenApiParameter(
                name='include_predicted',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Include predicted FCR values from scenario models (default: true)',
                default=True,
                required=False
            ),
        ],
        responses={
            200: FCRTrendsSerializer,
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        },
        tags=['operational', 'fcr', 'trends']
    )
    def list(self, request):
        """
        Get FCR trends data.

        Query Parameters:
        - start_date: ISO date (default: 1 year ago)
        - end_date: ISO date (default: today)
        - interval: DAILY|WEEKLY|MONTHLY (default: WEEKLY)
        - batch_id: Optional batch ID for batch-level aggregation
        - assignment_id: Optional assignment ID for container-level aggregation
        - geography_id: Optional geography ID for geography-level aggregation
        """
        # Parse query parameters
        params = self._parse_query_parameters(request)

        if not params:
            return Response(
                {'error': 'Invalid query parameters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get trends data
            trends_data = FCRTrendsService.get_fcr_trends(
                start_date=params['start_date'],
                end_date=params['end_date'],
                interval=params['interval'],
                batch_id=params.get('batch_id'),
                assignment_id=params.get('assignment_id'),
                geography_id=params.get('geography_id'),
                include_predicted=params.get('include_predicted', True)
            )

            # Serialize and return
            serializer = self.serializer_class(instance=trends_data)
            return Response(serializer.data)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _parse_query_parameters(self, request) -> Optional[dict]:
        """
        Parse and validate query parameters.

        Returns:
            Dict of validated parameters or None if validation fails
        """
        params = {}

        # Date parameters
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str:
            # Default to 1 year ago
            params['start_date'] = date.today() - timedelta(days=365)
        else:
            try:
                params['start_date'] = date.fromisoformat(start_date_str)
            except ValueError:
                return None

        if not end_date_str:
            # Default to today
            params['end_date'] = date.today()
        else:
            try:
                params['end_date'] = date.fromisoformat(end_date_str)
            except ValueError:
                return None

        # Validate date range
        if params['start_date'] >= params['end_date']:
            return None

        # Interval parameter
        interval_str = request.query_params.get('interval', 'DAILY')
        try:
            params['interval'] = TimeInterval[interval_str]
        except KeyError:
            return None

        # Optional ID parameters
        for param_name in ['batch_id', 'assignment_id', 'geography_id']:
            param_value = request.query_params.get(param_name)
            if param_value:
                try:
                    params[param_name] = int(param_value)
                except ValueError:
                    return None

        # Include predicted parameter
        include_predicted = request.query_params.get('include_predicted', 'true')
        params['include_predicted'] = include_predicted.lower() == 'true'

        return params

    @action(detail=False, methods=['get'])
    def batch_trends(self, request, batch_id=None):
        """
        Get FCR trends for a specific batch.

        Args:
            batch_id: Batch ID from URL path
        """
        # Override batch_id from URL if provided
        if batch_id:
            request.query_params._mutable = True
            request.query_params['batch_id'] = batch_id
            request.query_params._mutable = False

        return self.list(request)

    @action(detail=False, methods=['get'])
    def assignment_trends(self, request, assignment_id=None):
        """
        Get FCR trends for a specific container assignment.

        Args:
            assignment_id: Assignment ID from URL path
        """
        # Override assignment_id from URL if provided
        if assignment_id:
            request.query_params._mutable = True
            request.query_params['assignment_id'] = assignment_id
            request.query_params._mutable = False

        return self.list(request)

    @action(detail=False, methods=['get'])
    def geography_trends(self, request, geography_id=None):
        """
        Get FCR trends for a specific geography.

        Args:
            geography_id: Geography ID from URL path
        """
        # Override geography_id from URL if provided
        if geography_id:
            request.query_params._mutable = True
            request.query_params['geography_id'] = geography_id
            request.query_params._mutable = False

        return self.list(request)
