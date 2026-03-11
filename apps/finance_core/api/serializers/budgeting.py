"""Budgeting and month-close serializers for finance core."""

from rest_framework import serializers

from apps.finance_core.models import Budget, BudgetEntry, ValuationRun


class BudgetSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.display_name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, allow_null=True)

    class Meta:
        model = Budget
        fields = (
            "budget_id",
            "company",
            "company_name",
            "name",
            "fiscal_year",
            "status",
            "version",
            "notes",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("budget_id", "created_by", "created_at", "updated_at")

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class BudgetEntrySerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    cost_center_code = serializers.CharField(source="cost_center.code", read_only=True)

    class Meta:
        model = BudgetEntry
        fields = (
            "entry_id",
            "budget",
            "account",
            "account_code",
            "cost_center",
            "cost_center_code",
            "month",
            "amount",
            "allocated_from",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("entry_id", "created_at", "updated_at")


class BudgetAllocateSerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    operating_unit = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ValuationRunRequestSerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    operating_unit = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    mortality_adjustments = serializers.JSONField(required=False, default=dict)


class BudgetCopySerializer(serializers.Serializer):
    target_year = serializers.IntegerField(min_value=2000)
    new_name = serializers.CharField(required=False, allow_blank=True, default="")


class BudgetEntryBulkImportRowSerializer(serializers.Serializer):
    account = serializers.IntegerField()
    cost_center = serializers.IntegerField()
    month = serializers.IntegerField(min_value=1, max_value=12)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class BudgetEntryBulkImportSerializer(serializers.Serializer):
    budget = serializers.IntegerField()
    rows = BudgetEntryBulkImportRowSerializer(many=True)


class ValuationRunSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.display_name", read_only=True)
    operating_unit_name = serializers.CharField(source="operating_unit.site_name", read_only=True)

    class Meta:
        model = ValuationRun
        fields = (
            "run_id",
            "company",
            "company_name",
            "operating_unit",
            "operating_unit_name",
            "budget",
            "import_batch",
            "year",
            "month",
            "version",
            "status",
            "created_by",
            "approved_by",
            "run_timestamp",
            "completed_at",
            "notes",
            "biology_snapshot",
            "allocation_snapshot",
            "rule_snapshot",
            "mortality_snapshot",
            "totals_snapshot",
            "nav_posting",
            "updated_at",
        )
        read_only_fields = fields
