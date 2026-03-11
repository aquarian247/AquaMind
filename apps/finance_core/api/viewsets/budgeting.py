"""Budgeting, imports, locks, and valuation viewsets for finance core."""

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.finance.models import DimSite
from apps.users.models import Role
from apps.finance_core.api.filters import BudgetEntryFilterSet, ValuationRunFilterSet
from apps.finance_core.api.permissions import IsFinanceUser
from apps.finance_core.api.serializers import (
    BudgetAllocateSerializer,
    BudgetCopySerializer,
    BudgetEntryBulkImportSerializer,
    BudgetEntrySerializer,
    BudgetSerializer,
    CostImportBatchSerializer,
    CostImportUploadSerializer,
    PeriodLockActionSerializer,
    PeriodLockSerializer,
    PeriodUnlockSerializer,
    ValuationRunRequestSerializer,
    ValuationRunSerializer,
)
from apps.finance_core.models import Budget, BudgetEntry, CostImportBatch, PeriodLock, ValuationRun
from apps.finance_core.services import (
    create_allocation_preview_run,
    finalize_valuation_run,
    import_nav_costs,
    lock_period,
    reopen_period,
)


class FinanceCoreSecureViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsFinanceUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class BudgetViewSet(FinanceCoreSecureViewSet):
    queryset = Budget.objects.select_related("company", "created_by").all()
    serializer_class = BudgetSerializer
    filterset_fields = ["company", "fiscal_year", "status"]
    search_fields = ["name", "company__display_name"]
    ordering_fields = ["fiscal_year", "name", "created_at", "version"]
    ordering = ["-fiscal_year", "company__display_name", "name"]

    @extend_schema(
        request=BudgetCopySerializer,
        responses={201: BudgetSerializer},
    )
    @action(detail=True, methods=["post"], url_path="copy")
    def copy_budget(self, request, pk=None):
        budget = self.get_object()
        serializer = BudgetCopySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        copied_budget = Budget.objects.create(
            company=budget.company,
            name=serializer.validated_data["new_name"] or f"{budget.name} Copy",
            fiscal_year=serializer.validated_data["target_year"],
            status=budget.status,
            version=1,
            notes=budget.notes,
            created_by=request.user,
        )
        BudgetEntry.objects.bulk_create(
            [
                BudgetEntry(
                    budget=copied_budget,
                    account=entry.account,
                    cost_center=entry.cost_center,
                    month=entry.month,
                    amount=entry.amount,
                    notes=entry.notes,
                )
                for entry in budget.entries.all()
            ]
        )
        return Response(BudgetSerializer(copied_budget, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=BudgetAllocateSerializer,
        responses={201: ValuationRunSerializer},
    )
    @action(detail=True, methods=["post"], url_path="allocate")
    def allocate(self, request, pk=None):
        budget = self.get_object()
        serializer = BudgetAllocateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        operating_unit = get_object_or_404(DimSite, pk=serializer.validated_data["operating_unit"])
        valuation_run = create_allocation_preview_run(
            budget=budget,
            month=serializer.validated_data["month"],
            operating_unit=operating_unit,
            user=request.user,
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response(
            ValuationRunSerializer(valuation_run).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=ValuationRunRequestSerializer,
        responses={201: ValuationRunSerializer},
    )
    @action(detail=True, methods=["post"], url_path="valuation-run")
    def valuation_run(self, request, pk=None):
        budget = self.get_object()
        serializer = ValuationRunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        operating_unit = get_object_or_404(DimSite, pk=serializer.validated_data["operating_unit"])
        valuation_run = finalize_valuation_run(
            budget=budget,
            month=serializer.validated_data["month"],
            operating_unit=operating_unit,
            user=request.user,
            mortality_adjustments=serializer.validated_data.get("mortality_adjustments") or {},
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response(
            ValuationRunSerializer(valuation_run).data,
            status=status.HTTP_201_CREATED,
        )


class BudgetEntryViewSet(FinanceCoreSecureViewSet):
    queryset = BudgetEntry.objects.select_related("budget", "account", "cost_center").all()
    serializer_class = BudgetEntrySerializer
    filterset_class = BudgetEntryFilterSet
    search_fields = ["account__code", "cost_center__code", "notes"]
    ordering_fields = ["month", "amount", "created_at"]
    ordering = ["budget__fiscal_year", "month", "account__code"]

    @extend_schema(
        request=BudgetEntryBulkImportSerializer,
        responses={201: BudgetEntrySerializer(many=True)},
    )
    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        serializer = BudgetEntryBulkImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        budget = get_object_or_404(Budget, pk=serializer.validated_data["budget"])
        rows = serializer.validated_data["rows"]

        created = []
        for row in rows:
            entry, _ = BudgetEntry.objects.update_or_create(
                budget=budget,
                account_id=row["account"],
                cost_center_id=row["cost_center"],
                month=row["month"],
                defaults={
                    "amount": row["amount"],
                    "notes": row.get("notes", ""),
                },
            )
            created.append(entry)

        return Response(
            BudgetEntrySerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class CostImportBatchViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = CostImportBatch.objects.select_related("uploaded_by").all()
    permission_classes = [permissions.IsAuthenticated, IsFinanceUser]
    serializer_class = CostImportBatchSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["year", "month"]
    ordering_fields = ["created_at", "year", "month"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return CostImportUploadSerializer
        return CostImportBatchSerializer

    @extend_schema(
        request=CostImportUploadSerializer,
        responses={201: CostImportBatchSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        import_batch = import_nav_costs(
            uploaded_file=serializer.validated_data["file"],
            year=serializer.validated_data["year"],
            month=serializer.validated_data["month"],
            uploaded_by=request.user,
        )
        return Response(
            CostImportBatchSerializer(import_batch).data,
            status=status.HTTP_201_CREATED,
        )


class PeriodLockViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = PeriodLock.objects.select_related("company", "operating_unit").all()
    serializer_class = PeriodLockSerializer
    permission_classes = [permissions.IsAuthenticated, IsFinanceUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["company", "operating_unit", "year", "month", "is_locked"]
    ordering = ["-year", "-month"]

    @extend_schema(
        request=PeriodLockActionSerializer,
        responses={200: PeriodLockSerializer},
    )
    @action(detail=False, methods=["post"], url_path="lock")
    def lock(self, request):
        serializer = PeriodLockActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        operating_unit = get_object_or_404(DimSite, pk=serializer.validated_data["operating_unit"])
        period_lock = lock_period(
            company=operating_unit.company,
            operating_unit=operating_unit,
            year=serializer.validated_data["year"],
            month=serializer.validated_data["month"],
            user=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response(PeriodLockSerializer(period_lock).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=PeriodUnlockSerializer,
        responses={200: PeriodLockSerializer},
    )
    @action(detail=True, methods=["post"], url_path="unlock")
    def unlock(self, request, pk=None):
        period_lock = self.get_object()
        serializer = PeriodUnlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = getattr(request.user, "profile", None)
        if not request.user.is_superuser and (
            not profile or profile.role != Role.ADMIN
        ):
            raise PermissionDenied("Only administrators can reopen locked periods.")

        period_lock = reopen_period(
            period_lock=period_lock,
            user=request.user,
            reason=serializer.validated_data["reason"],
        )
        return Response(PeriodLockSerializer(period_lock).data, status=status.HTTP_200_OK)


class ValuationRunViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ValuationRun.objects.select_related("company", "operating_unit", "budget", "import_batch").all()
    serializer_class = ValuationRunSerializer
    permission_classes = [permissions.IsAuthenticated, IsFinanceUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ValuationRunFilterSet
    ordering_fields = ["year", "month", "version", "run_timestamp"]
    ordering = ["-year", "-month", "-version"]
