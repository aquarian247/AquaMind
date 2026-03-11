"""Allocation engine for finance core."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models

from apps.finance_core.models import AllocationRule, CostImportLine
from apps.finance_core.selectors.biology import get_opening_biology_snapshot

TWOPLACES = Decimal("0.01")
DEFAULT_RULE = {
    "mode": "weighted",
    "weights": {"headcount": 0.5, "biomass": 0.5},
    "fallback": "equal_split",
}


def _round_currency(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _decimal_to_str(value: Decimal) -> str:
    return f"{value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)}"


def _normalise_rule(rule_definition):
    definition = DEFAULT_RULE | (rule_definition or {})
    weights = definition.get("weights") or {}
    headcount_weight = Decimal(str(weights.get("headcount", 0.5)))
    biomass_weight = Decimal(str(weights.get("biomass", 0.5)))
    return {
        "mode": definition.get("mode", "weighted"),
        "weights": {
            "headcount": headcount_weight,
            "biomass": biomass_weight,
        },
        "fallback": definition.get("fallback", "equal_split"),
    }


def resolve_allocation_rule(*, account_group, cost_center_id: int | None, as_of_date: date):
    """Resolve the most specific rule for an allocation candidate."""

    base_queryset = AllocationRule.objects.filter(
        is_active=True,
        effective_from__lte=as_of_date,
    ).filter(
        models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=as_of_date)
    )

    cost_center_rule = None
    if cost_center_id is not None:
        cost_center_rule = (
            base_queryset.filter(cost_center_id=cost_center_id)
            .order_by("-effective_from", "-rule_id")
            .first()
        )
    if cost_center_rule:
        return cost_center_rule, _normalise_rule(cost_center_rule.rule_definition)

    account_group_rule = (
        base_queryset.filter(account_group=account_group, cost_center__isnull=True)
        .order_by("-effective_from", "-rule_id")
        .first()
    )
    if account_group_rule:
        return account_group_rule, _normalise_rule(account_group_rule.rule_definition)

    return None, _normalise_rule(DEFAULT_RULE)


def _aggregate_biology_rows(rows):
    grouped = {}
    missing = []

    for row in rows:
        if not row["cost_center_id"]:
            missing.append(
                {
                    "batch_id": row["batch_id"],
                    "batch_number": row["batch_number"],
                    "container_id": row["container_id"],
                    "container_name": row["container_name"],
                }
            )
            continue

        key = row["cost_center_id"]
        group = grouped.setdefault(
            key,
            {
                "cost_center_id": row["cost_center_id"],
                "cost_center_code": row["cost_center_code"],
                "cost_center_name": row["cost_center_name"],
                "population_count": Decimal("0"),
                "biomass_kg": Decimal("0"),
                "assignments": [],
                "batch_ids": [],
                "batch_numbers": [],
            },
        )
        group["population_count"] += Decimal(str(row["population_count"]))
        group["biomass_kg"] += Decimal(str(row["biomass_kg"]))
        group["assignments"].append(row)
        if row["batch_id"] not in group["batch_ids"]:
            group["batch_ids"].append(row["batch_id"])
            group["batch_numbers"].append(row["batch_number"])

    return list(grouped.values()), missing


def build_allocation_preview(*, year: int, month: int, operating_unit_id: int, company_id: int | None = None):
    """Build allocation preview rows for a site-period."""

    opening_date = date(year, month, 1)
    biology_rows = get_opening_biology_snapshot(
        year=year,
        month=month,
        operating_unit_id=operating_unit_id,
        company_id=company_id,
    )
    if not biology_rows:
        raise ValidationError("No biology rows found for the requested operating unit and period.")

    grouped_biology, missing_projects = _aggregate_biology_rows(biology_rows)
    if missing_projects:
        raise ValidationError(
            {
                "missing_cost_projects": missing_projects,
                "detail": "One or more batches are missing linked finance-core cost projects.",
            }
        )

    cost_lines = list(
        CostImportLine.objects.select_related("account_group", "operating_unit")
        .filter(year=year, month=month, operating_unit_id=operating_unit_id)
        .order_by("cost_group_code", "line_id")
    )
    if company_id:
        cost_lines = [line for line in cost_lines if line.company_id == company_id]
    if not cost_lines:
        raise ValidationError("No imported actual cost lines exist for the requested period.")

    total_population = sum((item["population_count"] for item in grouped_biology), Decimal("0"))
    total_biomass = sum((item["biomass_kg"] for item in grouped_biology), Decimal("0"))

    allocations = []
    rule_snapshots = []

    for line in cost_lines:
        line_scores = []
        for item in grouped_biology:
            rule_obj, rule = resolve_allocation_rule(
                account_group=line.account_group,
                cost_center_id=item["cost_center_id"],
                as_of_date=opening_date,
            )
            headcount_share = (
                item["population_count"] / total_population
                if total_population > 0
                else Decimal("0")
            )
            biomass_share = (
                item["biomass_kg"] / total_biomass
                if total_biomass > 0
                else Decimal("0")
            )

            if total_population <= 0 and total_biomass <= 0 and rule["fallback"] == "equal_split":
                score = Decimal("1") / Decimal(len(grouped_biology))
            else:
                score = (
                    rule["weights"]["headcount"] * headcount_share
                    + rule["weights"]["biomass"] * biomass_share
                )

            line_scores.append(
                {
                    "item": item,
                    "rule": rule,
                    "rule_id": rule_obj.rule_id if rule_obj else None,
                    "score": score,
                    "headcount_share": headcount_share,
                    "biomass_share": biomass_share,
                }
            )

        total_score = sum((entry["score"] for entry in line_scores), Decimal("0"))
        if total_score <= 0:
            total_score = Decimal(len(line_scores))
            for entry in line_scores:
                entry["score"] = Decimal("1")

        allocated_total = Decimal("0")
        running_rows = []
        for entry in line_scores:
            share = entry["score"] / total_score
            amount = _round_currency(line.amount * share)
            allocated_total += amount
            running_rows.append((entry, share, amount))

        rounding_delta = _round_currency(line.amount - allocated_total)
        if running_rows:
            entry, share, amount = running_rows[0]
            running_rows[0] = (entry, share, amount + rounding_delta)

        for entry, share, amount in running_rows:
            rule_snapshot = {
                "rule_id": entry["rule_id"],
                "cost_group": line.cost_group_code,
                "cost_center_id": entry["item"]["cost_center_id"],
                "cost_center_code": entry["item"]["cost_center_code"],
                "definition": {
                    "mode": entry["rule"]["mode"],
                    "weights": {
                        "headcount": str(entry["rule"]["weights"]["headcount"]),
                        "biomass": str(entry["rule"]["weights"]["biomass"]),
                    },
                    "fallback": entry["rule"]["fallback"],
                },
            }
            if rule_snapshot not in rule_snapshots:
                rule_snapshots.append(rule_snapshot)

            allocations.append(
                {
                    "source_line_id": line.line_id,
                    "cost_group_code": line.cost_group_code,
                    "cost_center_id": entry["item"]["cost_center_id"],
                    "cost_center_code": entry["item"]["cost_center_code"],
                    "cost_center_name": entry["item"]["cost_center_name"],
                    "share_percent": str((share * Decimal("100")).quantize(TWOPLACES)),
                    "headcount_share_percent": str((entry["headcount_share"] * Decimal("100")).quantize(TWOPLACES)),
                    "biomass_share_percent": str((entry["biomass_share"] * Decimal("100")).quantize(TWOPLACES)),
                    "allocated_amount": _decimal_to_str(amount),
                    "batch_numbers": entry["item"]["batch_numbers"],
                }
            )

    preview_biology = [
        {
            "cost_center_id": item["cost_center_id"],
            "cost_center_code": item["cost_center_code"],
            "cost_center_name": item["cost_center_name"],
            "population_count": str(item["population_count"]),
            "biomass_kg": str(item["biomass_kg"].quantize(TWOPLACES)),
            "batch_numbers": item["batch_numbers"],
        }
        for item in grouped_biology
    ]

    preview_cost_lines = [
        {
            "line_id": line.line_id,
            "cost_group_code": line.cost_group_code,
            "operating_unit_name": line.operating_unit_name,
            "amount": _decimal_to_str(line.amount),
        }
        for line in cost_lines
    ]

    return {
        "year": year,
        "month": month,
        "operating_unit_id": operating_unit_id,
        "biology_snapshot": preview_biology,
        "cost_lines": preview_cost_lines,
        "allocations": allocations,
        "rule_snapshots": rule_snapshots,
        "totals": {
            "biology_population": str(total_population),
            "biology_biomass_kg": str(total_biomass.quantize(TWOPLACES)),
            "imported_amount": _decimal_to_str(sum((line.amount for line in cost_lines), Decimal("0.00"))),
            "allocated_amount": _decimal_to_str(
                sum((Decimal(row["allocated_amount"]) for row in allocations), Decimal("0.00"))
            ),
        },
    }


def summarize_allocations_by_cost_center(allocation_rows):
    """Aggregate preview rows to cost-center totals."""

    summary = defaultdict(lambda: Decimal("0.00"))
    for row in allocation_rows:
        summary[(row["cost_center_id"], row["cost_center_code"], row["cost_center_name"])] += Decimal(
            row["allocated_amount"]
        )
    return [
        {
            "cost_center_id": key[0],
            "cost_center_code": key[1],
            "cost_center_name": key[2],
            "allocated_amount": _decimal_to_str(amount),
        }
        for key, amount in summary.items()
    ]
