"""
Infrastructure overview API endpoint.

This module provides an API endpoint for retrieving aggregated metrics
about the infrastructure, including container counts, capacity, and biomass.
"""
from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from drf_spectacular.utils import extend_schema, OpenApiResponse
from apps.infrastructure.models.container import Container
from apps.batch.models.assignment import BatchContainerAssignment
from apps.inventory.models.feeding import FeedingEvent


class InfrastructureOverviewView(APIView):
    """
    API endpoint for retrieving aggregated infrastructure overview metrics.
    
    This endpoint provides key metrics about the aquaculture infrastructure,
    including total container count, total capacity, active biomass,
    sensor alerts, and feeding events in the last 24 hours.
    
    The data is aggregated at the database level for optimal performance
    and cached to reduce database load.
    """
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @method_decorator(cache_page(60))  # Cache for 60 seconds
    @extend_schema(
        operation_id="infrastructure_overview",
        description="Retrieve aggregated infrastructure overview metrics. "
        "Returns totals for containers, capacity, active biomass, a placeholder "
        "sensor alert count, and the number of feeding events in the last 24 hours.",
        tags=["Infrastructure"],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "total_containers": {"type": "integer"},
                        "capacity_kg": {"type": "number"},
                        "active_biomass_kg": {"type": "number"},
                        "sensor_alerts": {"type": "integer"},
                        "feeding_events_today": {"type": "integer"},
                    },
                    "required": [
                        "total_containers",
                        "capacity_kg",
                        "active_biomass_kg",
                        "sensor_alerts",
                        "feeding_events_today",
                    ],
                },
                description="Aggregated overview metrics",
            )
        },
    )
    def get(self, request):
        """
        Get aggregated infrastructure overview metrics.
        
        Returns:
            Response: JSON response containing infrastructure metrics
        """
        # Get total containers count
        total_containers = Container.objects.count()
        
        # Get total capacity (sum of max_biomass_kg)
        capacity_result = Container.objects.aggregate(
            sum=Sum('max_biomass_kg')
        )
        capacity_kg = float(capacity_result['sum'] or 0)
        
        # Get active biomass (sum of biomass_kg where is_active=True)
        active_biomass_result = BatchContainerAssignment.objects.filter(
            is_active=True
        ).aggregate(
            sum=Sum('biomass_kg')
        )
        active_biomass_kg = float(active_biomass_result['sum'] or 0)
        
        # Count feeding events in the last 24 hours
        # Only count events whose ``feeding_date`` equals *today* (not last 24 h).
        today = timezone.now().date()
        feeding_events_today = FeedingEvent.objects.filter(
            feeding_date=today
        ).count()
        
        # Return aggregated metrics
        return Response({
            'total_containers': total_containers,
            'capacity_kg': capacity_kg,
            'active_biomass_kg': active_biomass_kg,
            'sensor_alerts': 0,  # Placeholder for now
            'feeding_events_today': feeding_events_today,
        })
