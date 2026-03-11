"""Accounting serializers for finance core."""

from rest_framework import serializers

from apps.finance_core.models import (
    Account,
    AccountGroup,
    AllocationRule,
    CostCenter,
    CostCenterBatchLink,
)


class DimCompanySummarySerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    display_name = serializers.CharField()
    currency = serializers.CharField(allow_null=True)
    nav_company_code = serializers.CharField(allow_null=True)
    subsidiary = serializers.CharField()


class DimSiteSummarySerializer(serializers.Serializer):
    site_id = serializers.IntegerField()
    site_name = serializers.CharField()
    source_model = serializers.CharField()


class CompanyDimensionSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    display_name = serializers.CharField()
    currency = serializers.CharField(allow_null=True)
    nav_company_code = serializers.CharField(allow_null=True)
    subsidiary = serializers.CharField()
    geography = serializers.CharField(source="geography.name")


class SiteDimensionSerializer(serializers.Serializer):
    site_id = serializers.IntegerField()
    site_name = serializers.CharField()
    source_model = serializers.CharField()
    source_pk = serializers.IntegerField()
    company = DimCompanySummarySerializer(read_only=True)


class AccountGroupSerializer(serializers.ModelSerializer):
    parent_code = serializers.CharField(source="parent.code", read_only=True, allow_null=True)

    class Meta:
        model = AccountGroup
        fields = (
            "group_id",
            "code",
            "name",
            "account_type",
            "parent",
            "parent_code",
            "cost_group",
            "description",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("group_id", "created_at", "updated_at")


class AccountSerializer(serializers.ModelSerializer):
    group_code = serializers.CharField(source="group.code", read_only=True, allow_null=True)

    class Meta:
        model = Account
        fields = (
            "account_id",
            "code",
            "name",
            "account_type",
            "group",
            "group_code",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("account_id", "created_at", "updated_at")


class CostCenterBatchLinkSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True)

    class Meta:
        model = CostCenterBatchLink
        fields = ("link_id", "batch", "batch_number", "created_by", "linked_at")
        read_only_fields = fields


class CostCenterSerializer(serializers.ModelSerializer):
    company_summary = DimCompanySummarySerializer(source="company", read_only=True)
    site_summary = DimSiteSummarySerializer(source="site", read_only=True, allow_null=True)
    parent_code = serializers.CharField(source="parent.code", read_only=True, allow_null=True)
    batch_links = CostCenterBatchLinkSerializer(many=True, read_only=True)

    class Meta:
        model = CostCenter
        fields = (
            "cost_center_id",
            "company",
            "company_summary",
            "site",
            "site_summary",
            "parent",
            "parent_code",
            "code",
            "name",
            "cost_center_type",
            "description",
            "is_active",
            "batch_links",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("cost_center_id", "created_at", "updated_at")


class AllocationRuleSerializer(serializers.ModelSerializer):
    account_group_code = serializers.CharField(source="account_group.code", read_only=True, allow_null=True)
    cost_center_code = serializers.CharField(source="cost_center.code", read_only=True, allow_null=True)

    class Meta:
        model = AllocationRule
        fields = (
            "rule_id",
            "name",
            "account_group",
            "account_group_code",
            "cost_center",
            "cost_center_code",
            "effective_from",
            "effective_to",
            "rule_definition",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("rule_id", "created_at", "updated_at")
