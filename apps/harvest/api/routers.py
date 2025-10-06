"""Router registration for harvest API endpoints."""

from rest_framework.routers import DefaultRouter

from apps.harvest.api.viewsets import HarvestEventViewSet, HarvestLotViewSet

router = DefaultRouter()
router.register(r'harvest-events', HarvestEventViewSet, basename='harvest-events')
router.register(r'harvest-lots', HarvestLotViewSet, basename='harvest-lots')

urlpatterns = router.urls
