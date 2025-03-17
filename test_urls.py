"""
URL configuration for testing environment.
Explicitly includes all API routes needed for tests.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Import routers directly
from apps.infrastructure.api.routers import router as infrastructure_router
from apps.environmental.api.routers import router as environmental_router
from apps.batch.api.routers import router as batch_router

# Swagger/OpenAPI documentation setup
schema_view = get_schema_view(
    openapi.Info(
        title="AquaMind API",
        default_version='v1',
        description="API for AquaMind aquaculture management system",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="Commercial License"),
    ),
    public=True,
    permission_classes=(permissions.IsAuthenticated,),
)

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # API documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Register API routes explicitly for testing with proper namespaces
    path('api/v1/infrastructure/', include((infrastructure_router.urls, 'infrastructure'))),
    path('api/v1/environmental/', include((environmental_router.urls, 'environmental'))),
    path('api/v1/batch/', include((batch_router.urls, 'batch'))),
    
    # Include REST framework authentication URLs
    path("api-auth/", include("rest_framework.urls")),
]
