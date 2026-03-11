"""Import services for finance core cost intake."""

from __future__ import annotations

import csv
import hashlib
import io
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.finance.models import DimSite
from apps.finance_core.models import AccountGroup, CostImportBatch, CostImportLine
from apps.finance_core.services.locking import LockGuardService

REQUIRED_HEADERS = {"CostGroup", "OperatingUnit", "Amount"}


def _read_uploaded_text(uploaded_file) -> str:
    if uploaded_file is None:
        raise ValidationError("CSV file is required.")
    content = uploaded_file.read()
    if isinstance(content, bytes):
        return content.decode("utf-8-sig")
    return str(content)


def import_nav_costs(*, uploaded_file, year: int, month: int, uploaded_by=None):
    """Import NAV actual costs with replace-period semantics for the affected sites."""

    text = _read_uploaded_text(uploaded_file)
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames or not REQUIRED_HEADERS.issubset(set(reader.fieldnames)):
        raise ValidationError(
            f"CSV must contain headers: {', '.join(sorted(REQUIRED_HEADERS))}."
        )

    raw_rows = []
    errors = []

    for row_number, row in enumerate(reader, start=2):
        try:
            cost_group_code = (row.get("CostGroup") or "").strip()
            operating_unit_name = (row.get("OperatingUnit") or "").strip()
            amount = Decimal(str(row.get("Amount", "0")).replace(",", ""))

            account_group = AccountGroup.objects.filter(cost_group=cost_group_code).first()
            if not account_group:
                account_group = AccountGroup.objects.filter(code=cost_group_code).first()
            if not account_group:
                raise ValidationError(f"Unknown CostGroup '{cost_group_code}'")

            operating_unit = DimSite.objects.filter(site_name=operating_unit_name).first()
            if not operating_unit:
                raise ValidationError(f"Unknown OperatingUnit '{operating_unit_name}'")

            if LockGuardService.is_locked(
                company_id=operating_unit.company_id,
                operating_unit_id=operating_unit.site_id,
                year=year,
                month=month,
            ):
                raise ValidationError(
                    f"Locked period for {operating_unit.site_name} {year}-{month:02d}"
                )

            raw_rows.append(
                {
                    "company": operating_unit.company,
                    "operating_unit": operating_unit,
                    "account_group": account_group,
                    "cost_group_code": cost_group_code,
                    "operating_unit_name": operating_unit_name,
                    "amount": amount,
                    "raw_payload": row,
                }
            )
        except Exception as exc:  # pragma: no cover - exercised through API tests
            errors.append({"row": row_number, "error": str(exc)})

    if errors:
        raise ValidationError({"rows": errors})

    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    operating_unit_ids = sorted({item["operating_unit"].site_id for item in raw_rows})

    with transaction.atomic():
        CostImportLine.objects.filter(
            year=year,
            month=month,
            operating_unit_id__in=operating_unit_ids,
        ).delete()

        import_batch = CostImportBatch.objects.create(
            year=year,
            month=month,
            source_filename=getattr(uploaded_file, "name", "upload.csv"),
            checksum=checksum,
            imported_row_count=len(raw_rows),
            total_amount=sum((item["amount"] for item in raw_rows), Decimal("0.00")),
            uploaded_by=uploaded_by,
        )

        CostImportLine.objects.bulk_create(
            [
                CostImportLine(
                    import_batch=import_batch,
                    company=item["company"],
                    operating_unit=item["operating_unit"],
                    account_group=item["account_group"],
                    year=year,
                    month=month,
                    cost_group_code=item["cost_group_code"],
                    operating_unit_name=item["operating_unit_name"],
                    amount=item["amount"],
                    raw_payload=item["raw_payload"],
                )
                for item in raw_rows
            ]
        )

    return import_batch
