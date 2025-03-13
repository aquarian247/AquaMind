"""
Router registration for the environmental app API.

This module sets up the DRF router with all viewsets for the environmental app.
"""
from rest_framework.routers import DefaultRouter

from apps.environmental.api.viewsets import (
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
router.register(r'photoperiod', PhotoperiodDataViewSet, basename='photoperiod')
router.register(r'weather', WeatherDataViewSet, basename='weather')
router.register(r'stage-transitions', StageTransitionEnvironmentalViewSet, basename='transition')

# The API URLs are determined automatically by the router
urlpatterns = router.urls
