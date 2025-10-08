"""Export services for NAV journal batches."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterator, Sequence

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.finance.models import (
    DimCompany,
    FactHarvest,
    IntercompanyTransaction,
    NavExportBatch,
    NavExportLine,
)


class ExportError(Exception):
    """Base class for NAV export errors."""


class ExportAlreadyExists(ExportError):
    """Raised when a batch already exists for the requested filters."""

    def __init__(self, batch: NavExportBatch):
        self.batch = batch
        super().__init__(
            "A NAV export batch already exists for this company and date range."
        )


class NoPendingTransactions(ExportError):
    """Raised when no pending transactions match the export criteria."""


class ExportDataError(ExportError):
    """Raised when source data required for export is missing."""


@dataclass(frozen=True)
class ExportRequest:
    company_id: int
    date_from: date
    date_to: date
    force: bool = False


def create_export_batch(
    company_id: int,
    date_from: date,
    date_to: date,
    *,
    force: bool = False,
) -> NavExportBatch:
    """Create a NAV export batch and persist journal lines."""

    if date_from > date_to:
        raise ValidationError("date_from must be before or equal to date_to")

    request = ExportRequest(company_id=company_id, date_from=date_from, date_to=date_to, force=force)

    with transaction.atomic():
        batch = _initialise_batch(request)

        transactions = list(
            _pending_transactions(request)
            .select_related(
                "policy",
                "policy__from_company",
                "policy__to_company",
                "policy__product_grade",
                "event",
            )
            .order_by("posting_date", "tx_id")
        )

        if not transactions:
            raise NoPendingTransactions("No pending transactions found for export range.")

        fact_map = _build_fact_map(batch.company_id, transactions)

        account_no, balancing_account_no = _resolve_account_numbers()
        lines: list[NavExportLine] = []
        currency = batch.currency

        for tx in transactions:
            fact = fact_map.get(tx.pk)
            if not fact:
                raise ExportDataError(
                    "Missing FactHarvest for transaction policy and event combination."
                )

            amount = tx.amount if tx.amount is not None else Decimal("0.00")
            currency = currency or tx.currency or batch.company.currency

            lines.append(
                NavExportLine(
                    batch=batch,
                    transaction=tx,
                    document_no=_format_document_no(tx.tx_id),
                    account_no=account_no,
                    balancing_account_no=balancing_account_no,
                    amount=amount,
                    description=f"Intercompany {tx.policy.product_grade.name}",
                    dim_company=fact.dim_company,
                    dim_site=fact.dim_site,
                    product_grade=fact.product_grade,
                    batch_id_int=fact.dim_batch_id,
                )
            )

        NavExportLine.objects.bulk_create(lines)

        IntercompanyTransaction.objects.filter(
            pk__in=[tx.pk for tx in transactions]
        ).update(state=IntercompanyTransaction.State.EXPORTED)

        batch.posting_date = max(tx.posting_date for tx in transactions)
        batch.currency = currency
        batch.state = NavExportBatch.State.EXPORTED
        batch.save(update_fields=["posting_date", "currency", "state", "updated_at"])

        return batch


def generate_csv(batch_id: int) -> Iterator[bytes]:
    """Stream NAV export batch as CSV rows encoded in UTF-8."""

    batch = (
        NavExportBatch.objects.select_related("company")
        .prefetch_related(
            "lines__dim_company",
            "lines__dim_site",
            "lines__product_grade",
        )
        .get(batch_id=batch_id)
    )

    lines = batch.lines.select_related("dim_company", "dim_site", "product_grade").order_by("line_id")

    yield _to_csv_row(
        ["export_id", "created_at", "company", "posting_date", "currency"]
    )
    yield _to_csv_row(
        [
            _format_export_identifier(batch.batch_id),
            batch.created_at.isoformat(),
            batch.company.display_name,
            batch.posting_date.isoformat(),
            batch.currency or "",
        ]
    )
    yield _to_csv_row(
        [
            "document_no",
            "account_no",
            "balancing_account_no",
            "amount",
            "description",
            "dim_company",
            "dim_site",
            "dim_product_grade",
            "batch_id",
        ]
    )

    for line in lines:
        yield _to_csv_row(
            [
                line.document_no,
                line.account_no,
                line.balancing_account_no,
                f"{line.amount:.2f}",
                line.description,
                line.dim_company.display_name,
                line.dim_site.site_name,
                line.product_grade.code,
                str(line.batch_id_int),
            ]
        )


def _initialise_batch(request: ExportRequest) -> NavExportBatch:
    existing = (
        NavExportBatch.objects.select_for_update()
        .filter(
            company_id=request.company_id,
            date_from=request.date_from,
            date_to=request.date_to,
        )
        .first()
    )

    if existing:
        if not request.force:
            raise ExportAlreadyExists(existing)
        _reset_existing_batch(existing)
        return existing

    company = DimCompany.objects.select_for_update().get(pk=request.company_id)
    return NavExportBatch.objects.create(
        company=company,
        date_from=request.date_from,
        date_to=request.date_to,
        posting_date=request.date_to,
        currency=company.currency,
    )


def _pending_transactions(request: ExportRequest):
    return IntercompanyTransaction.objects.filter(
        policy__from_company_id=request.company_id,
        posting_date__gte=request.date_from,
        posting_date__lte=request.date_to,
        state=IntercompanyTransaction.State.PENDING,
    )


def _build_fact_map(
    company_id: int, transactions: Sequence[IntercompanyTransaction]
) -> dict[int, FactHarvest]:
    event_ids = {tx.event_id for tx in transactions}
    grade_ids = {tx.policy.product_grade_id for tx in transactions}

    facts = FactHarvest.objects.select_related(
        "dim_company", "dim_site", "product_grade"
    ).filter(
        event_id__in=event_ids,
        product_grade_id__in=grade_ids,
        dim_company_id=company_id,
    )

    fact_by_key = {
        (fact.event_id, fact.product_grade_id): fact
        for fact in facts
    }

    mapping: dict[int, FactHarvest] = {}
    for tx in transactions:
        mapping[tx.pk] = fact_by_key.get((tx.event_id, tx.policy.product_grade_id))
    return mapping


def _reset_existing_batch(batch: NavExportBatch) -> None:
    tx_ids = list(
        NavExportLine.objects.filter(batch=batch)
        .values_list("transaction_id", flat=True)
        .distinct()
    )

    if tx_ids:
        IntercompanyTransaction.objects.select_for_update().filter(pk__in=tx_ids).update(
            state=IntercompanyTransaction.State.PENDING
        )

    NavExportLine.objects.filter(batch=batch).delete()
    batch.state = NavExportBatch.State.DRAFT
    batch.posting_date = batch.date_to
    batch.currency = batch.company.currency
    batch.save(update_fields=["state", "posting_date", "currency", "updated_at"])


def _resolve_account_numbers() -> tuple[str, str]:
    account_map = getattr(settings, "NAV_ACCOUNT_MAP", {}) or {}
    return (
        account_map.get("sales_account", "4000"),
        account_map.get("balancing_account", "3000"),
    )


def _format_document_no(tx_id: int) -> str:
    return f"IC{tx_id}"


def _format_export_identifier(batch_id: int) -> str:
    return f"IC{batch_id:05d}"


def _to_csv_row(values: Sequence[str]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(values)
    return buffer.getvalue().encode("utf-8")
