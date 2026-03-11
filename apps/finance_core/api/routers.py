"""Router registration for finance core API endpoints."""

from rest_framework.routers import DefaultRouter

from apps.finance_core.api.viewsets import (
    AccountGroupViewSet,
    AccountViewSet,
    AllocationRuleViewSet,
    BudgetEntryViewSet,
    BudgetViewSet,
    CompanyDimensionViewSet,
    CostCenterViewSet,
    CostImportBatchViewSet,
    FinanceCoreReportViewSet,
    PeriodLockViewSet,
    SiteDimensionViewSet,
    ValuationRunViewSet,
)

router = DefaultRouter()
router.register(r"companies", CompanyDimensionViewSet, basename="finance-core-companies")
router.register(r"account-groups", AccountGroupViewSet, basename="finance-core-account-groups")
router.register(r"accounts", AccountViewSet, basename="finance-core-accounts")
router.register(r"cost-centers", CostCenterViewSet, basename="finance-core-cost-centers")
router.register(r"operating-units", SiteDimensionViewSet, basename="finance-core-operating-units")
router.register(r"allocation-rules", AllocationRuleViewSet, basename="finance-core-allocation-rules")
router.register(r"budgets", BudgetViewSet, basename="finance-core-budgets")
router.register(r"budget-entries", BudgetEntryViewSet, basename="finance-core-budget-entries")
router.register(r"cost-imports", CostImportBatchViewSet, basename="finance-core-cost-imports")
router.register(r"periods", PeriodLockViewSet, basename="finance-core-periods")
router.register(r"valuation-runs", ValuationRunViewSet, basename="finance-core-valuation-runs")
router.register(r"reports", FinanceCoreReportViewSet, basename="finance-core-reports")

urlpatterns = router.urls
