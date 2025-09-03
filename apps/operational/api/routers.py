"""
Operational API routers.

Registers all operational API endpoints with explicit kebab-case basenames
following api_standards.md guidelines.
"""
from rest_framework.routers import DefaultRouter
from apps.operational.api.viewsets.fcr_trends import FCRTrendsViewSet

# Create router instance
router = DefaultRouter()

# Register FCR trends endpoint
# Note: Using explicit basename following api_standards.md
router.register(
    r'fcr-trends',
    FCRTrendsViewSet,
    basename='fcr-trends'
)
