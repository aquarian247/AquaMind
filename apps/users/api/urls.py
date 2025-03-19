from django.urls import path
from .views import CustomObtainAuthToken

urlpatterns = [
    path('token/', CustomObtainAuthToken.as_view(), name='api-token-auth'),
]
