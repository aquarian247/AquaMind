from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    EnvironmentalParameterViewSet,
    EnvironmentalReadingViewSet,
    PhotoperiodDataViewSet,
    WeatherDataViewSet,
    StageTransitionEnvironmentalViewSet
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'parameters', EnvironmentalParameterViewSet, basename='parameter')
router.register(r'readings', EnvironmentalReadingViewSet, basename='reading')
router.register(r'photoperiods', PhotoperiodDataViewSet, basename='photoperiod')
router.register(r'weather', WeatherDataViewSet, basename='weather')
router.register(r'transitions', StageTransitionEnvironmentalViewSet, basename='transition')

# The API URLs are determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
]