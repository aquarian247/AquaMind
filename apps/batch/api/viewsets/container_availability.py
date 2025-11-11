"""
Container Availability ViewSet for timeline-aware container selection.

This endpoint enriches container data with occupancy forecasting to enable
planners to see which containers will be available on a future delivery date.
"""
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Sum, F
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.infrastructure.models import Container
from apps.batch.models import BatchContainerAssignment
from apps.batch.api.serializers.container_availability import ContainerAvailabilityResponseSerializer


class ContainerAvailabilityViewSet(viewsets.ViewSet):
    """
    ViewSet for container availability forecasting.
    
    Provides timeline-aware container selection for workflow planning.
    Shows which containers are:
    - Empty (immediately available)
    - Occupied but will be empty by delivery date (available)
    - Occupied beyond delivery date (conflict)
    """
    serializer_class = ContainerAvailabilityResponseSerializer
    
    @extend_schema(
        operation_id='listContainerAvailability',
        summary='Get containers with timeline-aware availability forecasting',
        description=(
            'Returns containers enriched with occupancy forecasting for workflow planning. '
            'Shows which containers are immediately available, will be available by delivery date, '
            'or have conflicts (still occupied on delivery date).'
        ),
        parameters=[
            OpenApiParameter(
                name='geography',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=True,
                description='Filter by geography ID'
            ),
            OpenApiParameter(
                name='delivery_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Date when action will execute (YYYY-MM-DD). Defaults to today.'
            ),
            OpenApiParameter(
                name='container_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by container type name (e.g. TANK, PEN, TRAY)'
            ),
            OpenApiParameter(
                name='lifecycle_stage',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by compatible lifecycle stage ID'
            ),
            OpenApiParameter(
                name='include_occupied',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Include occupied containers (default: true)'
            ),
        ],
        responses={
            200: ContainerAvailabilityResponseSerializer,
            400: OpenApiTypes.OBJECT,
        },
        tags=['batch']
    )
    def list(self, request):
        """
        GET /api/v1/batch/containers/availability/
        
        Query Parameters:
        - geography (int, required): Filter by geography ID
        - delivery_date (str, optional): Date when action will execute (YYYY-MM-DD)
        - container_type (str, optional): Filter by type (TANK, PEN, TRAY, etc.)
        - lifecycle_stage (int, optional): Filter by compatible lifecycle stage ID
        - include_occupied (bool, optional, default: true): Include occupied containers
        
        Returns:
        - Enriched container list with availability forecasting
        """
        # Extract query parameters
        geography_id = request.query_params.get('geography')
        delivery_date_str = request.query_params.get('delivery_date')
        container_type = request.query_params.get('container_type')
        lifecycle_stage_id = request.query_params.get('lifecycle_stage')
        include_occupied = request.query_params.get('include_occupied', 'true').lower() == 'true'
        
        # Validate required parameters
        if not geography_id:
            return Response(
                {'error': 'geography parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse delivery date
        if delivery_date_str:
            try:
                delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            delivery_date = timezone.now().date()
        
        # Build container queryset
        containers = Container.objects.filter(
            area__geography_id=geography_id,
            active=True
        ).select_related('area', 'container_type')
        
        # Filter by container type if specified
        if container_type:
            containers = containers.filter(container_type__name=container_type)
        
        # Filter by lifecycle stage compatibility if specified
        if lifecycle_stage_id:
            containers = containers.filter(
                container_type__compatible_lifecycle_stages__id=lifecycle_stage_id
            )
        
        # Enrich containers with availability data
        results = []
        for container in containers:
            enriched_data = self._enrich_container(container, delivery_date)
            
            # Filter out occupied containers if not requested
            if not include_occupied and enriched_data['current_status'] == 'OCCUPIED':
                if enriched_data['availability_status'] == 'CONFLICT':
                    continue
            
            results.append(enriched_data)
        
        # Sort by availability priority
        # Priority: EMPTY > AVAILABLE > OCCUPIED_BUT_OK > CONFLICT
        priority_order = {'EMPTY': 0, 'AVAILABLE': 1, 'OCCUPIED_BUT_OK': 2, 'CONFLICT': 3}
        results.sort(key=lambda x: (
            priority_order.get(x['availability_status'], 99),
            x['name']
        ))
        
        return Response({
            'count': len(results),
            'results': results
        })
    
    def _enrich_container(self, container, delivery_date):
        """
        Enrich container with availability forecasting data.
        
        Args:
            container: Container model instance
            delivery_date: Date when action will execute
            
        Returns:
            dict: Enriched container data with availability forecast
        """
        # Get current active assignments
        active_assignments = BatchContainerAssignment.objects.filter(
            container=container,
            is_active=True
        ).select_related('batch', 'lifecycle_stage').order_by('-assignment_date')
        
        # Build current assignments list
        current_assignments_data = []
        total_current_biomass = 0
        latest_expected_departure = None
        
        for assignment in active_assignments:
            expected_departure = assignment.expected_departure_date
            current_assignments_data.append({
                'batch_id': assignment.batch.id,
                'batch_number': assignment.batch.batch_number,
                'population_count': assignment.population_count,
                'lifecycle_stage': assignment.lifecycle_stage.name,
                'assignment_date': assignment.assignment_date.isoformat(),
                'expected_departure_date': expected_departure.isoformat() if expected_departure else None,
            })
            total_current_biomass += float(assignment.biomass_kg or 0)
            
            # Track latest expected departure
            if expected_departure:
                if latest_expected_departure is None or expected_departure > latest_expected_departure:
                    latest_expected_departure = expected_departure
        
        # Determine current status
        current_status = 'OCCUPIED' if active_assignments.exists() else 'EMPTY'
        
        # Calculate availability forecast
        if current_status == 'EMPTY':
            availability_status = 'EMPTY'
            days_until_available = None
            availability_message = 'Empty and ready'
        else:
            if latest_expected_departure is None:
                # No expected departure - cannot forecast
                availability_status = 'CONFLICT'
                days_until_available = None
                availability_message = '⚠️ Cannot determine availability (no typical duration data)'
            elif delivery_date > latest_expected_departure:
                # Container will be empty before delivery
                days_buffer = (delivery_date - latest_expected_departure).days
                availability_status = 'AVAILABLE'
                days_until_available = days_buffer
                availability_message = f'Available from {latest_expected_departure.isoformat()} ({days_buffer} days before your delivery)'
            elif delivery_date == latest_expected_departure:
                # Same day - risky but technically OK
                availability_status = 'OCCUPIED_BUT_OK'
                days_until_available = 0
                availability_message = f'Available on delivery day {latest_expected_departure.isoformat()} (no buffer - risky)'
            else:
                # Still occupied on delivery date - conflict
                days_conflict = (latest_expected_departure - delivery_date).days
                availability_status = 'CONFLICT'
                days_until_available = -days_conflict
                availability_message = f'⚠️ Conflict: Occupied until {latest_expected_departure.isoformat()} ({days_conflict} day{"s" if days_conflict != 1 else ""} after your delivery)'
        
        # Calculate capacity
        max_biomass = float(container.max_biomass_kg or 0)
        available_capacity_kg = max(0, max_biomass - total_current_biomass)
        available_capacity_percent = (available_capacity_kg / max_biomass * 100) if max_biomass > 0 else 0
        
        # Build enriched response
        return {
            'id': container.id,
            'name': container.name,
            'container_type': container.container_type.name,
            'volume_m3': float(container.volume_m3 or 0),
            'max_biomass_kg': max_biomass,
            
            # Current occupancy
            'current_status': current_status,
            'current_assignments': current_assignments_data,
            
            # Availability forecast
            'availability_status': availability_status,
            'days_until_available': days_until_available,
            'availability_message': availability_message,
            
            # Capacity
            'available_capacity_kg': round(available_capacity_kg, 2),
            'available_capacity_percent': round(available_capacity_percent, 1),
        }

