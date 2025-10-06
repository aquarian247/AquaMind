"""
Main API router configuration for the AquaMind project.

This module integrates all app-specific routers into a single API entry point,
providing consistent URL patterns for the entire application.
"""
from django.urls import path, include
from rest_framework import permissions
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
from apps.operational.api.routers import router as operational_router
from apps.harvest.api.routers import router as harvest_router
# from apps.core.api.routers import router as core_router  # Temporarily disabled for testing
# Import the users URLs

# Configure API URL patterns
router = DefaultRouter()

# Include routers from all apps

urlpatterns = [
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
    path('environmental/', include(environmental_router.urls)),
    path('batch/', include(batch_router.urls)),
    path('inventory/', include(inventory_router.urls)),
    path('health/', include(health_router.urls)),
    path('broodstock/', include(broodstock_router.urls)),
    # Restored infrastructure endpoints
    path('infrastructure/', include(infrastructure_router.urls)),
    path('scenario/', include(scenario_router.urls)),
    path('operational/', include(operational_router.urls)),
    path('operational/', include(harvest_router.urls)),
    path('users/', include('apps.users.urls')),
]
