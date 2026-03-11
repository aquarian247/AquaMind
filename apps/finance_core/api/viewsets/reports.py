"""Report endpoints for finance core."""

from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.finance_core.api.permissions import IsFinanceUser
from apps.finance_core.api.serializers import (
    MovementReportQuerySerializer,
    NavExportPreviewQuerySerializer,
    PreCloseSummaryQuerySerializer,
    RingValuationQuerySerializer,
)
from apps.finance_core.models import ValuationRun
from apps.finance_core.services import (
    build_preclose_summary,
    build_movement_report,
    build_nav_export_preview,
    build_ring_valuation_report,
)


class FinanceCoreReportViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsFinanceUser]
    serializer_class = MovementReportQuerySerializer

    def get_serializer_class(self):
        if self.action == "pre_close_summary":
            return PreCloseSummaryQuerySerializer
        if self.action == "ring_valuation":
            return RingValuationQuerySerializer
        if self.action == "nav_export_preview":
            return NavExportPreviewQuerySerializer
        return MovementReportQuerySerializer

    @action(detail=False, methods=["get"], url_path="movement")
    def movement(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        payload = build_movement_report(
            run_id=serializer.validated_data.get("run_id"),
            company_id=serializer.validated_data.get("company"),
            year=serializer.validated_data.get("year"),
            month=serializer.validated_data.get("month"),
        )
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="pre-close-summary")
    def pre_close_summary(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        payload = build_preclose_summary(
            company_id=serializer.validated_data["company"],
            operating_unit_id=serializer.validated_data["operating_unit"],
            year=serializer.validated_data["year"],
            month=serializer.validated_data["month"],
            budget_id=serializer.validated_data.get("budget"),
        )
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="ring-valuation")
    def ring_valuation(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        valuation_run = _resolve_valuation_run(serializer.validated_data)
        return Response(build_ring_valuation_report(valuation_run=valuation_run))

    @action(detail=False, methods=["get"], url_path="nav-export-preview")
    def nav_export_preview(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        valuation_run = _resolve_valuation_run(serializer.validated_data)
        as_csv = serializer.validated_data.get("format") == "csv"
        payload = build_nav_export_preview(valuation_run=valuation_run, as_csv=as_csv)
        if as_csv:
            return Response(payload, content_type="text/csv")
        return Response(payload)


def _resolve_valuation_run(data):
    if data.get("run_id"):
        return get_object_or_404(ValuationRun, pk=data["run_id"])

    queryset = ValuationRun.objects.all()
    if data.get("company"):
        queryset = queryset.filter(company_id=data["company"])
    if data.get("operating_unit"):
        queryset = queryset.filter(operating_unit_id=data["operating_unit"])
    if data.get("year"):
        queryset = queryset.filter(year=data["year"])
    if data.get("month"):
        queryset = queryset.filter(month=data["month"])

    valuation_run = queryset.order_by("-year", "-month", "-version").first()
    if not valuation_run:
        raise Http404("No valuation run matched the requested filters.")
    return valuation_run
