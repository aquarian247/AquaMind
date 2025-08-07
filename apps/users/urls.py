"""
Users app – **Primary JWT Authentication & User API**
=====================================================

This URL configuration exposes the **production-grade authentication system**
used by the React / TypeScript frontend.  It is based on
*django-rest-framework-simplejwt* and implements:

1.  JSON Web Token (JWT) obtain / refresh endpoints
2.  “Me / Profile” endpoint for the currently authenticated user
3.  CRUD operations for user management via `UserViewSet`

In contrast, *development-only* token endpoints (DRF token + `dev-auth`) live
in `apps.users.api.urls` and are mounted under `/auth/…` by the project router.
That separation allows local/CI scripts to grab a quick token without JWT
overhead while keeping this file focused on the production flow.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UserViewSet, CustomTokenObtainPairView, UserProfileView

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    # ------------------------------------------------------------------ #
    # JWT Authentication endpoints (frontend login / refresh)             #
    # ------------------------------------------------------------------ #
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # ------------------------------------------------------------------ #
    # User profile (“/me”) endpoint                                       #
    # ------------------------------------------------------------------ #
    path('auth/profile/', UserProfileView.as_view(), name='user_profile'),
    
    # ------------------------------------------------------------------ #
    # User CRUD routes (list, create, retrieve, etc.)                     #
    # ------------------------------------------------------------------ #
    path('', include(router.urls)),
]
