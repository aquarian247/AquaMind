from rest_framework.routers import DefaultRouter
from apps.planning.api.viewsets import (
    PlannedActivityViewSet,
    ActivityTemplateViewSet
)

router = DefaultRouter()
router.register(r'planned-activities', PlannedActivityViewSet, basename='planned-activity')
router.register(r'activity-templates', ActivityTemplateViewSet, basename='activity-template')







