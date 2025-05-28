"""
Main API router configuration for the AquaMind project.

This module integrates all app-specific routers into a single API entry point,
providing consistent URL patterns for the entire application.
"""
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from apps.core.views import health_check
from rest_framework import routers

from apps.infrastructure.api.routers import router as infrastructure_router
from apps.environmental.api.routers import router as environmental_router
from apps.batch.api.routers import router as batch_router
from apps.inventory.api.routers import router as inventory_router
from apps.health.api.routers import router as health_router
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
router = routers.DefaultRouter()

# Include routers from all apps
router.registry.extend(batch_router.registry)
router.registry.extend(environmental_router.registry)
router.registry.extend(infrastructure_router.registry)
router.registry.extend(inventory_router.registry)
router.registry.extend(health_router.registry)

urlpatterns = [
    # API documentation endpoints
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Authentication endpoints
    path('auth/', include('apps.users.api.urls')),
    
    # Health check endpoint
    path('health-check/', health_check, name='health-check'),
    
    # API endpoints for each app
    path('infrastructure/', include((infrastructure_router.urls, 'infrastructure'))),
    path('environmental/', include((environmental_router.urls, 'environmental'))),
    path('batch/', include((batch_router.urls, 'batch'))),
    path('inventory/', include((inventory_router.urls, 'inventory'))),
    path('health/', include((health_router.urls, 'health-api'))),
    path('users/', include('apps.users.urls')),
]
