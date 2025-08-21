"""
API Root discovery view for AquaMind.

This module provides a comprehensive overview of all available API endpoints,
organized by app/module for easy discovery and navigation.
"""
from collections import OrderedDict
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import AllowAny
from rest_framework.decorators import permission_classes


class APIRootView(APIView):
    """
    API Root discovery view that provides a comprehensive overview of all
    available API endpoints in the AquaMind system.
    
    This view is designed to help developers discover and navigate the API
    structure easily.
    """
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
            ('environmental', self._get_url(request, 'api/v1/environmental/', format)),
            ('batch', self._get_url(request, 'api/v1/batch/', format)),
            ('inventory', self._get_url(request, 'api/v1/inventory/', format)),
            ('health', self._get_url(request, 'api/v1/health/', format)),
            ('broodstock', self._get_url(request, 'api/v1/broodstock/', format)),
            ('infrastructure', self._get_url(request, 'api/v1/infrastructure/', format)),
            ('scenario', self._get_url(request, 'api/v1/scenario/', format)),
            ('users', self._get_url(request, 'api/v1/users/', format)),
        ])
        
        # Health check endpoint
        data['system'] = OrderedDict([
            ('health-check', self._get_url(request, 'api/v1/health/', format)),
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
        return request.build_absolute_uri(f'/{path}')
