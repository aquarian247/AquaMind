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
