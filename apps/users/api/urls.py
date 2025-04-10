from django.urls import path
from .views import CustomObtainAuthToken, dev_auth

urlpatterns = [
    path('token/', CustomObtainAuthToken.as_view(), name='api-token-auth'),
    path('dev-auth/', dev_auth, name='api-dev-auth'),
]
