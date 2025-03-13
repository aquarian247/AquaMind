"""
Router registration for the infrastructure app API.

This module sets up the DRF router with all viewsets for the infrastructure app.
"""
from rest_framework.routers import DefaultRouter

from apps.infrastructure.api.viewsets import (
    GeographyViewSet,
    AreaViewSet,
    FreshwaterStationViewSet,
    HallViewSet,
    ContainerTypeViewSet,
    ContainerViewSet,
    SensorViewSet,
    FeedContainerViewSet
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'geographies', GeographyViewSet)
router.register(r'areas', AreaViewSet)
router.register(r'freshwater-stations', FreshwaterStationViewSet)
router.register(r'halls', HallViewSet)
router.register(r'container-types', ContainerTypeViewSet)
router.register(r'containers', ContainerViewSet)
router.register(r'sensors', SensorViewSet)
router.register(r'feed-containers', FeedContainerViewSet)

# The API URLs are determined automatically by the router
urlpatterns = router.urls
