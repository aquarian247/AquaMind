"""Serializers for intercompany transaction endpoints."""

from rest_framework import serializers

from apps.finance.api.serializers.fact_harvest import (
    CompanySummarySerializer,
    ProductGradeSummarySerializer,
)
from apps.finance.models import IntercompanyPolicy, IntercompanyTransaction


class IntercompanyPolicySummarySerializer(serializers.ModelSerializer):
    """Compact representation of an intercompany pricing policy."""

    id = serializers.IntegerField(source="policy_id", read_only=True)
    from_company = CompanySummarySerializer(read_only=True)
    to_company = CompanySummarySerializer(read_only=True)
    product_grade = ProductGradeSummarySerializer(read_only=True)

    class Meta:
        model = IntercompanyPolicy
        fields = (
            "id",
            "method",
            "markup_percent",
            "from_company",
            "to_company",
            "product_grade",
        )
        read_only_fields = fields


class IntercompanyTransactionSerializer(serializers.ModelSerializer):
    """Read-only serializer for intercompany transactions."""

    policy = IntercompanyPolicySummarySerializer(
        read_only=True,
        help_text="Policy metadata including participating companies.",
    )

    class Meta:
        model = IntercompanyTransaction
        fields = (
            "tx_id",
            "event",
            "posting_date",
            "amount",
            "currency",
            "state",
            "policy",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
