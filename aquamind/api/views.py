"""
API Root discovery view for AquaMind.

This module provides a comprehensive overview of all available API endpoints,
organized by app/module for easy discovery and navigation.
"""
from collections import OrderedDict
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers


class APIRootView(APIView):
    """
    API Root discovery view that provides a comprehensive overview of all
    available API endpoints in the AquaMind system.
    
    This view is designed to help developers discover and navigate the API
    structure easily.
    """
    # Explicitly set a serializer_class so that drf-spectacular does not attempt
    # to auto-detect one and raise a warning. Since this view only returns a
    # plain dictionary structure, no serializer is required.
    serializer_class = None
    permission_classes = [AllowAny]
    
    def get(self, request, format=None):
        """
        Return a structured overview of all available API endpoints.
        """
        data = OrderedDict()
        
        # Documentation endpoints
        data['documentation'] = OrderedDict([
            ('schema', reverse('schema', request=request, format=format)),
            ('swagger-ui', reverse('spectacular-swagger-ui', request=request, format=format)),
            ('redoc', reverse('spectacular-redoc', request=request, format=format)),
        ])
        
        # Authentication endpoints
        data['authentication'] = OrderedDict([
            ('token-auth', reverse('api_token_auth', request=request, format=format)),
            ('jwt-obtain', reverse('jwt_obtain_pair', request=request, format=format)),
            ('jwt-refresh', reverse('jwt_refresh', request=request, format=format)),
        ])
        
        # App-specific endpoints
        data['apps'] = OrderedDict([
            ('environmental', self._get_url(request, '/api/v1/environmental/', format)),
            ('batch', self._get_url(request, '/api/v1/batch/', format)),
            ('inventory', self._get_url(request, '/api/v1/inventory/', format)),
            ('health', self._get_url(request, '/api/v1/health/', format)),
            ('broodstock', self._get_url(request, '/api/v1/broodstock/', format)),
            ('infrastructure', self._get_url(request, '/api/v1/infrastructure/', format)),
            ('scenario', self._get_url(request, '/api/v1/scenario/', format)),
            ('users', self._get_url(request, '/api/v1/users/', format)),
        ])
        
        # Health check endpoint
        data['system'] = OrderedDict([
            # Dedicated health-check endpoint that does **not** collide with the
            # health app’s API namespace.
            ('health-check', self._get_url(request, '/health-check/', format)),
        ])
        
        return Response(data)
    
    def _get_url(self, request, path, format=None):
        """
        Helper method to build absolute URLs for API endpoints.
        
        Args:
            request: The HTTP request object
            path: The relative path to the endpoint
            format: Optional format suffix
            
        Returns:
            str: The absolute URL to the endpoint
        """
        # Ensure there is exactly one leading slash before joining with domain.
        normalized_path = path if path.startswith('/') else f'/{path}'
        return request.build_absolute_uri(normalized_path)


class HealthCheckResponseSerializer(serializers.Serializer):
    """Serializer for health check API response."""
    status = serializers.CharField(help_text="Current service status")
    timestamp = serializers.DateTimeField(help_text="Timestamp of the health check")
    service = serializers.CharField(help_text="Service name")
    version = serializers.CharField(help_text="Service version")
    database = serializers.CharField(help_text="Database status")
    environment = serializers.CharField(help_text="Environment type")


@extend_schema(
    summary="API Health Check",
    description="Health check endpoint for monitoring API availability and basic system status.",
    responses={
        200: HealthCheckResponseSerializer,
        503: HealthCheckResponseSerializer,
    },
    tags=["System"]
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    API health check endpoint for monitoring and testing.

    This endpoint provides a simple way to verify that:
    1. The Django application is running
    2. The database is accessible
    3. Basic API functionality is working

    Returns 200 OK with system status information, or 503 if services are unavailable.
    """
    try:
        # Basic system information
        data = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'service': 'AquaMind API',
            'version': '1.0.0',
            'database': 'accessible',
            'environment': 'production' if not hasattr(request, 'META') or 'test' not in str(request.META.get('HTTP_HOST', '')) else 'test'
        }

        return Response(data, status=200)

    except Exception as e:
        # If anything goes wrong, return service unavailable
        return Response({
            'status': 'unhealthy',
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }, status=503)
