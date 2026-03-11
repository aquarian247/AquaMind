"""Operational serializers for imports, locks, and reports."""

from rest_framework import serializers

from apps.finance_core.models import CostImportBatch, PeriodLock


class CostImportBatchSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True, allow_null=True)

    class Meta:
        model = CostImportBatch
        fields = (
            "import_batch_id",
            "year",
            "month",
            "source_filename",
            "checksum",
            "imported_row_count",
            "total_amount",
            "uploaded_by",
            "uploaded_by_username",
            "created_at",
        )
        read_only_fields = fields


class CostImportUploadSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000)
    month = serializers.IntegerField(min_value=1, max_value=12)
    file = serializers.FileField()


class PeriodLockSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.display_name", read_only=True)
    operating_unit_name = serializers.CharField(source="operating_unit.site_name", read_only=True)
    locked_by_username = serializers.CharField(
        source="locked_by.username",
        read_only=True,
        allow_null=True,
    )
    reopened_by_username = serializers.CharField(
        source="reopened_by.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = PeriodLock
        fields = (
            "period_lock_id",
            "company",
            "company_name",
            "operating_unit",
            "operating_unit_name",
            "year",
            "month",
            "is_locked",
            "version",
            "lock_reason",
            "locked_by",
            "locked_by_username",
            "locked_at",
            "reopened_by",
            "reopened_by_username",
            "reopened_at",
            "reopen_reason",
            "updated_at",
        )
        read_only_fields = (
            "period_lock_id",
            "company_name",
            "operating_unit_name",
            "version",
            "locked_at",
            "reopened_at",
            "updated_at",
        )


class PeriodLockActionSerializer(serializers.Serializer):
    company = serializers.IntegerField()
    operating_unit = serializers.IntegerField()
    year = serializers.IntegerField(min_value=2000)
    month = serializers.IntegerField(min_value=1, max_value=12)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class PeriodUnlockSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False)


class MovementReportQuerySerializer(serializers.Serializer):
    run_id = serializers.IntegerField(required=False)
    company = serializers.IntegerField(required=False)
    year = serializers.IntegerField(required=False, min_value=2000)
    month = serializers.IntegerField(required=False, min_value=1, max_value=12)


class RingValuationQuerySerializer(serializers.Serializer):
    run_id = serializers.IntegerField(required=False)
    company = serializers.IntegerField(required=False)
    operating_unit = serializers.IntegerField(required=False)
    year = serializers.IntegerField(required=False, min_value=2000)
    month = serializers.IntegerField(required=False, min_value=1, max_value=12)


class NavExportPreviewQuerySerializer(serializers.Serializer):
    run_id = serializers.IntegerField(required=False)
    company = serializers.IntegerField(required=False)
    operating_unit = serializers.IntegerField(required=False)
    year = serializers.IntegerField(required=False, min_value=2000)
    month = serializers.IntegerField(required=False, min_value=1, max_value=12)
    format = serializers.ChoiceField(required=False, choices=["json", "csv"], default="json")


class PreCloseSummaryQuerySerializer(serializers.Serializer):
    company = serializers.IntegerField()
    operating_unit = serializers.IntegerField()
    year = serializers.IntegerField(min_value=2000)
    month = serializers.IntegerField(min_value=1, max_value=12)
    budget = serializers.IntegerField(required=False)
