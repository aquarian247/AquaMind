"""Viewset for NAV export batch management."""

from django.http import StreamingHttpResponse
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema

from apps.finance.api.permissions import IsFinanceUser
from apps.finance.api.serializers import (
    NavExportBatchCreateSerializer,
    NavExportBatchSerializer,
)
from apps.finance.models import NavExportBatch
from apps.finance.services import (
    ExportAlreadyExists,
    ExportDataError,
    NoPendingTransactions,
    create_export_batch,
    generate_csv,
)


class NavExportBatchViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Create NAV export batches and stream journal files."""

    queryset = NavExportBatch.objects.all()
    lookup_field = "batch_id"
    permission_classes = [permissions.IsAuthenticated, IsFinanceUser]

    def get_serializer_class(self):
        if self.action == "create":
            return NavExportBatchCreateSerializer
        return NavExportBatchSerializer

    @extend_schema(
        summary="Create NAV export batch",
        description="Batch pending intercompany transactions into a NAV journal.",
        responses={status.HTTP_201_CREATED: NavExportBatchSerializer},
        parameters=[
            OpenApiParameter(
                name="force",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Set true to regenerate an existing batch for the same filters.",
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        company = serializer.validated_data["company"]
        date_from = serializer.validated_data["date_from"]
        date_to = serializer.validated_data["date_to"]
        force_flag = _parse_force_flag(request.query_params.get("force"))

        try:
            batch = create_export_batch(
                company_id=company.pk,
                date_from=date_from,
                date_to=date_to,
                force=force_flag,
            )
        except ExportAlreadyExists as exc:
            raise ValidationError({"non_field_errors": [str(exc)]}) from exc
        except NoPendingTransactions as exc:
            raise ValidationError({"non_field_errors": [str(exc)]}) from exc
        except ExportDataError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]}) from exc

        data = NavExportBatchSerializer(instance=batch, context=self.get_serializer_context()).data
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(
        summary="Download NAV export batch",
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description="CSV journal file",
            )
        },
    )
    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, *args, **kwargs):
        batch = self.get_object()
        filename = f"nav_export_{batch.batch_id}.csv"
        response = StreamingHttpResponse(generate_csv(batch.batch_id), content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response


def _parse_force_flag(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes"}
