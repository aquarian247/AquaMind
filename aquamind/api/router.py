"""
Main API router configuration for the AquaMind project.

This module integrates all app-specific routers into a single API entry point,
providing consistent URL patterns for the entire application.
"""
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from apps.infrastructure.api.routers import router as infrastructure_router
from apps.environmental.api.routers import router as environmental_router
from apps.batch.api.routers import router as batch_router
# Import the users URLs

# Create a schema view for API documentation
schema_view = get_schema_view(
    openapi.Info(
        title="AquaMind API",
        default_version='v1',
        description="API for AquaMind - Aquaculture Management System",
        terms_of_service="https://www.aquamind.com/terms/",
        contact=openapi.Contact(email="contact@aquamind.com"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=(permissions.IsAuthenticated,),
)

# Configure API URL patterns
urlpatterns = [
    # API documentation endpoints
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API endpoints for each app
    path('infrastructure/', include((infrastructure_router.urls, 'infrastructure'))),
    path('environmental/', include((environmental_router.urls, 'environmental'))),
    path('batch/', include((batch_router.urls, 'batch'))),
    path('users/', include('apps.users.urls')),
]
