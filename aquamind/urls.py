"""
URL configuration for aquamind project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.users.api.views import CustomObtainAuthToken
# from apps.core.views import CSRFTokenView  # Temporarily disabled
# drf-spectacular (OpenAPI 3.1) views – target replacement for drf-yasg
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

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
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", include(('apps.health.urls', 'health'), namespace='health')), # Include health app URLs
    
    # API documentation
    # --- drf-spectacular (new, OpenAPI 3.1 single source of truth) ---
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="spectacular-swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="spectacular-redoc",
    ),
    # --- legacy drf-yasg endpoints (to be deprecated once migration completes) ---
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Redirect root URL to admin for now
    path('', RedirectView.as_view(url='/admin/'), name='index'),
    
    # API endpoints using our centralized router
    path("api/v1/", include("aquamind.api.router")),
    # Include REST framework authentication URLs
    path("api-auth/", include("rest_framework.urls")),
    
    # Auth endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/', CustomObtainAuthToken.as_view(), name='api-token-auth'),
    
    # Authentication endpoints
    path("api/auth/token/", CustomObtainAuthToken.as_view(), name="api_token_auth"),
    path("api/auth/jwt/", TokenObtainPairView.as_view(), name="jwt_obtain_pair"),
    path("api/auth/jwt/refresh/", TokenRefreshView.as_view(), name="jwt_refresh"),
    # path("api/auth/csrf/", CSRFTokenView.as_view(), name="csrf_token"),  # Temporarily disabled
]
