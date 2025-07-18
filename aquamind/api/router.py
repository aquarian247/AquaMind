"""
Main API router configuration for the AquaMind project.

This module integrates all app-specific routers into a single API entry point,
providing consistent URL patterns for the entire application.
"""
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.routers import DefaultRouter

# Core functionality imports
# from apps.core.views import health_check  # Temporarily disabled

# App-specific routers
from apps.environmental.api.routers import router as environmental_router
from apps.batch.api.routers import router as batch_router
from apps.inventory.api.routers import router as inventory_router
from apps.health.api.routers import router as health_router
from apps.broodstock.api.routers import router as broodstock_router
from apps.infrastructure.api.routers import router as infrastructure_router
from apps.scenario.api.routers import router as scenario_router
# from apps.core.api.routers import router as core_router  # Temporarily disabled for testing
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
router = DefaultRouter()

# Include routers from all apps
router.registry.extend(batch_router.registry)
router.registry.extend(environmental_router.registry)
router.registry.extend(inventory_router.registry)
router.registry.extend(health_router.registry)
router.registry.extend(broodstock_router.registry)
router.registry.extend(scenario_router.registry)

urlpatterns = [
    # API documentation endpoints
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Authentication endpoints
    path('auth/', include('apps.users.api.urls')),
    
    # Health check endpoint
    # path('health/', health_check, name='health_check'),  # Temporarily disabled
    
    # API endpoints for each app
    # ------------------------------------------------------------------
    # NOTE:
    # Infrastructure endpoints were **temporarily disabled** during Phase-4
    # contract-unification to eliminate duplicate URL patterns that caused
    # 404 noise in Schemathesis.  Now that the router duplication issue is
    # resolved we restore them via a single explicit `path()` include.
    # ------------------------------------------------------------------
    path('environmental/', include((environmental_router.urls, 'environmental'))),
    path('batch/', include((batch_router.urls, 'batch'))),
    path('inventory/', include((inventory_router.urls, 'inventory'))),
    path('health/', include((health_router.urls, 'health-api'))),
    path('broodstock/', include((broodstock_router.urls, 'broodstock'))),
    # Restored infrastructure endpoints
    path('infrastructure/', include((infrastructure_router.urls, 'infrastructure'))),
    path('scenario/', include((scenario_router.urls, 'scenario'))),
    path('users/', include('apps.users.urls')),
]
