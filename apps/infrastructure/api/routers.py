"""
Router registration for the infrastructure app API.

This module sets up the DRF router with all viewsets for the infrastructure app.
"""
from rest_framework.routers import DefaultRouter
from django.urls import path

from apps.infrastructure.api.viewsets.overview import (
    InfrastructureOverviewView,
)

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
from apps.infrastructure.api.viewsets.history import (
    GeographyHistoryViewSet,
    AreaHistoryViewSet,
    FreshwaterStationHistoryViewSet,
    HallHistoryViewSet,
    ContainerTypeHistoryViewSet,
    ContainerHistoryViewSet,
    SensorHistoryViewSet,
    FeedContainerHistoryViewSet
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'geographies', GeographyViewSet, basename='geography')
router.register(r'areas', AreaViewSet, basename='area')
router.register(r'freshwater-stations', FreshwaterStationViewSet, basename='freshwater-station')
router.register(r'halls', HallViewSet, basename='hall')
router.register(r'container-types', ContainerTypeViewSet, basename='container-type')
router.register(r'containers', ContainerViewSet, basename='container')
router.register(r'sensors', SensorViewSet, basename='sensor')
router.register(r'feed-containers', FeedContainerViewSet, basename='feed-container')

# Register history endpoints
router.register(r'history/geographies', GeographyHistoryViewSet, basename='geography-history')
router.register(r'history/areas', AreaHistoryViewSet, basename='area-history')
router.register(r'history/freshwater-stations', FreshwaterStationHistoryViewSet, basename='freshwater-station-history')
router.register(r'history/halls', HallHistoryViewSet, basename='hall-history')
router.register(r'history/container-types', ContainerTypeHistoryViewSet, basename='container-type-history')
router.register(r'history/containers', ContainerHistoryViewSet, basename='container-history')
router.register(r'history/sensors', SensorHistoryViewSet, basename='sensor-history')
router.register(r'history/feed-containers', FeedContainerHistoryViewSet, basename='feed-container-history')

# The API URLs are determined automatically by the router
urlpatterns = router.urls

# ------------------------------------------------------------------
# Custom aggregated overview endpoint (non-model, not suited for router)
# ------------------------------------------------------------------
urlpatterns += [
    path(
        "overview/",
        InfrastructureOverviewView.as_view(),
        name="infrastructure-overview",
    ),
]
