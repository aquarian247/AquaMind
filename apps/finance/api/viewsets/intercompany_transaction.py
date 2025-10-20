"""Viewset for intercompany transactions."""

from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import filters, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.finance.api.filters import IntercompanyTransactionFilterSet
from apps.finance.api.pagination import FinancePagination
from apps.finance.api.permissions import IsFinanceUser
from apps.finance.api.serializers import IntercompanyTransactionSerializer
from apps.finance.models import IntercompanyTransaction

@extend_schema_view(
    list=extend_schema(
        summary="List intercompany transactions",
        description="Retrieve detected intercompany transactions with optional filters.",
        parameters=[
            OpenApiParameter(
                name="state",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by transaction state (pending, exported, posted).",
            ),
            OpenApiParameter(
                name="company",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by finance company ID participating in the policy.",
            ),
            OpenApiParameter(
                name="date_from",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Inclusive lower bound for posting date.",
            ),
            OpenApiParameter(
                name="date_to",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Inclusive upper bound for posting date.",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Ordering fields, e.g. '-posting_date'.",
            ),
        ],
    ),
    retrieve=extend_schema(
        parameters=[
            OpenApiParameter(
                name="tx_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Unique intercompany transaction identifier.",
            )
        ]
    ),
)
class IntercompanyTransactionViewSet(ReadOnlyModelViewSet):
    """Read-only access to intercompany transactions."""

    serializer_class = IntercompanyTransactionSerializer
    lookup_field = "tx_id"
    lookup_url_kwarg = "tx_id"
    filterset_class = IntercompanyTransactionFilterSet
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = (
        "posting_date",
        "created_at",
        "updated_at",
        "tx_id",
    )
    ordering = ("-posting_date", "-tx_id")
    permission_classes = [permissions.IsAuthenticated, IsFinanceUser]
    pagination_class = FinancePagination

    def get_queryset(self):
        return (
            IntercompanyTransaction.objects.select_related(
                "policy",
                "policy__from_company",
                "policy__from_company__geography",
                "policy__to_company",
                "policy__to_company__geography",
                "policy__product_grade",
                "policy__lifecycle_stage",
                "content_type",
                "approved_by",
                "event",  # Legacy field
            )
            .order_by("-posting_date", "-tx_id")
        )

    @extend_schema(
        summary="Approve intercompany transaction",
        description=(
            "Approve a pending intercompany transaction. "
            "Transitions state from PENDING to POSTED. "
            "Only Finance Managers can approve transactions."
        ),
        request=None,
        responses={
            200: IntercompanyTransactionSerializer,
            400: {
                "description": (
                    "Transaction is not in PENDING state or "
                    "user lacks permission"
                )
            },
            404: {"description": "Transaction not found"},
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
        permission_classes=[permissions.IsAuthenticated, IsFinanceUser],
    )
    def approve(self, request, tx_id=None):
        """
        Approve an intercompany transaction.

        Validates:
        - Transaction exists
        - Transaction is in PENDING state
        - User has Finance Manager permissions

        Returns:
            200: Approved transaction
            400: Cannot approve (wrong state)
            403: Insufficient permissions
            404: Transaction not found
        """
        transaction_obj = self.get_object()

        # Check if user can approve (Finance Manager role)
        # For now, any authenticated finance user can approve
        # TODO: Add role-based permission check
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Attempt approval
        try:
            transaction_obj.approve(user=request.user)
            transaction_obj.refresh_from_db()

            serializer = self.get_serializer(transaction_obj)
            return Response(
                {
                    "message": "Transaction approved successfully",
                    "transaction": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="List pending approvals",
        description=(
            "Get all transactions in PENDING state awaiting approval. "
            "Useful for approval dashboards."
        ),
        responses={200: IntercompanyTransactionSerializer(many=True)},
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="pending-approvals",
        permission_classes=[permissions.IsAuthenticated, IsFinanceUser],
    )
    def pending_approvals(self, request):
        """
        List all pending transactions awaiting approval.

        Returns:
            List of transactions in PENDING state
        """
        pending = self.get_queryset().filter(
            state=IntercompanyTransaction.State.PENDING
        )

        page = self.paginate_queryset(pending)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
