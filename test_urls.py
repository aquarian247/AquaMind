"""
URL configuration for testing environment.
Explicitly includes all API routes needed for tests.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
# drf-spectacular (OpenAPI 3.1) views – single source of truth for tests
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.users.api.views import CustomObtainAuthToken

# Import routers directly
from apps.infrastructure.api.routers import router as infrastructure_router
from apps.environmental.api.routers import router as environmental_router
from apps.batch.api.routers import router as batch_router
from apps.health.api.routers import router as health_router

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # API documentation (drf-spectacular)
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[permissions.AllowAny]),
        name="schema",
    ),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[permissions.AllowAny]),
        name="spectacular-swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema", permission_classes=[permissions.AllowAny]),
        name="spectacular-redoc",
    ),
    
    # Register API routes explicitly for testing with proper namespaces
    path('api/v1/infrastructure/', include((infrastructure_router.urls, 'infrastructure'))),
    path('api/v1/environmental/', include((environmental_router.urls, 'environmental'))),
    path('api/v1/batch/', include((batch_router.urls, 'batch'))),
    path('api/v1/health/', include((health_router.urls, 'health'))),
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/auth/', include('apps.users.api.urls')),
    
    # Include REST framework authentication URLs
    path("api-auth/", include("rest_framework.urls")),
    
    # JWT Authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/', CustomObtainAuthToken.as_view(), name='api-token-auth'),
]
