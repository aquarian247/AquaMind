"""Accounting domain viewsets for finance core."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, permissions, viewsets

from apps.finance_core.api.permissions import IsFinanceUser
from apps.finance_core.api.serializers import (
    AccountGroupSerializer,
    AccountSerializer,
    AllocationRuleSerializer,
    CompanyDimensionSerializer,
    CostCenterSerializer,
    SiteDimensionSerializer,
)
from apps.finance.models import DimCompany, DimSite
from apps.finance_core.models import Account, AccountGroup, AllocationRule, CostCenter


class FinanceCoreBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsFinanceUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class FinanceCoreReadOnlyViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated, IsFinanceUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class AccountGroupViewSet(FinanceCoreBaseViewSet):
    queryset = AccountGroup.objects.select_related("parent").all()
    serializer_class = AccountGroupSerializer
    filterset_fields = ["account_type", "parent", "is_active"]
    search_fields = ["code", "name", "cost_group"]
    ordering_fields = ["code", "name", "display_order", "created_at"]
    ordering = ["account_type", "display_order", "code"]


class AccountViewSet(FinanceCoreBaseViewSet):
    queryset = Account.objects.select_related("group").all()
    serializer_class = AccountSerializer
    filterset_fields = ["account_type", "group", "is_active"]
    search_fields = ["code", "name", "description"]
    ordering_fields = ["code", "name", "created_at"]
    ordering = ["account_type", "code"]


class CostCenterViewSet(FinanceCoreBaseViewSet):
    queryset = CostCenter.objects.select_related("company", "site", "parent").prefetch_related("batch_links__batch").all()
    serializer_class = CostCenterSerializer
    filterset_fields = ["company", "site", "parent", "cost_center_type", "is_active"]
    search_fields = ["code", "name", "description", "site__site_name"]
    ordering_fields = ["code", "name", "created_at"]
    ordering = ["company__display_name", "code"]


class AllocationRuleViewSet(FinanceCoreBaseViewSet):
    queryset = AllocationRule.objects.select_related("account_group", "cost_center").all()
    serializer_class = AllocationRuleSerializer
    filterset_fields = ["account_group", "cost_center", "is_active"]
    search_fields = ["name", "account_group__code", "cost_center__code"]
    ordering_fields = ["effective_from", "effective_to", "created_at"]
    ordering = ["-effective_from", "name"]


class CompanyDimensionViewSet(FinanceCoreReadOnlyViewSet):
    queryset = DimCompany.objects.select_related("geography").all()
    serializer_class = CompanyDimensionSerializer
    lookup_field = "company_id"
    filterset_fields = ["geography", "subsidiary"]
    search_fields = ["display_name", "nav_company_code"]
    ordering_fields = ["display_name", "company_id"]
    ordering = ["display_name"]


class SiteDimensionViewSet(FinanceCoreReadOnlyViewSet):
    queryset = DimSite.objects.select_related("company", "company__geography").all()
    serializer_class = SiteDimensionSerializer
    lookup_field = "site_id"
    filterset_fields = ["company", "source_model"]
    search_fields = ["site_name"]
    ordering_fields = ["site_name", "site_id"]
    ordering = ["site_name"]
