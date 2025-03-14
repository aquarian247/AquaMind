from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UserViewSet, CustomTokenObtainPairView, UserProfileView

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    # JWT Authentication endpoints
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User profile endpoint
    path('auth/profile/', UserProfileView.as_view(), name='user_profile'),
    
    # Include router URLs
    path('', include(router.urls)),
]
