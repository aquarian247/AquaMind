"""Router registration for finance API endpoints."""

from rest_framework.routers import DefaultRouter

from apps.finance.api.viewsets import (
    FactHarvestViewSet,
    IntercompanyTransactionViewSet,
    NavExportBatchViewSet,
)


router = DefaultRouter()
router.register(
    r'facts/harvests',
    FactHarvestViewSet,
    basename='finance-fact-harvests',
)
router.register(
    r'intercompany/transactions',
    IntercompanyTransactionViewSet,
    basename='finance-intercompany-transactions',
)
router.register(
    r'nav-exports',
    NavExportBatchViewSet,
    basename='finance-nav-exports',
)

urlpatterns = router.urls
