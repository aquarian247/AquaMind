#!/usr/bin/env python3
"""Build the cutoff-correct FW-only <30m two-geography scope and transfer queue."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migration.tools.pilot_migrate_component_transfers import (
    expand_subtransfer_rows_for_source_scope,
    load_members_from_report,
    load_subtransfers_from_csv,
)
from apps.migration_support.models import ExternalIdMap


DEFAULT_INPUT_BATCHES = (
    PROJECT_ROOT / "scripts" / "migration" / "output" / "input_stitching" / "input_batches.csv"
)
DEFAULT_INPUT_MEMBERS = (
    PROJECT_ROOT
    / "scripts"
    / "migration"
    / "output"
    / "input_stitching"
    / "input_population_members.csv"
)
DEFAULT_REPORT_ROOT = (
    PROJECT_ROOT / "scripts" / "migration" / "output" / "input_batch_migration"
)
DEFAULT_EXTRACT_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"
DEFAULT_CUTOFF_DATE = "2026-01-22"
ALLOWED_STAGES = {"Egg&Alevin", "Fry", "Parr", "Smolt"}
EARLY_STAGE_ONLY = {frozenset({"Egg&Alevin"}), frozenset({"Fry"})}
MANUAL_RECONSTRUCTION = {
    "24Q1 LHS ex-LC|13|2023": (
        "Creation actions land on Parr assignments, not Egg&Alevin; "
        "outside the narrow zeroed-egg repair class."
    ),
    "Stofnfiskur feb 2025|1|2025": (
        "Guarded creation repair still leaves the batch materially below its "
        "creation total; needs smarter FW reconstruction."
    ),
    "Benchmark Gen. Mars 2025|1|2025": (
        "Guarded creation repair still leaves the batch materially below its "
        "creation total; needs smarter FW reconstruction."
    ),
    "Gjógv/Fiskaaling mars 2023|5|2023": (
        "Creation actions land on Parr assignments, not Egg&Alevin; "
        "outside the narrow zeroed-egg repair class."
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-batches", type=Path, default=DEFAULT_INPUT_BATCHES)
    parser.add_argument("--input-members", type=Path, default=DEFAULT_INPUT_MEMBERS)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--extract-dir", type=Path, default=DEFAULT_EXTRACT_DIR)
    parser.add_argument("--cutoff-date", default=DEFAULT_CUTOFF_DATE, help="YYYY-MM-DD")
    parser.add_argument(
        "--output-prefix",
        type=Path,
        required=True,
        help="Prefix for .json/.md/.strict.csv/.replay.csv/.transfer_queue.csv/.manual.csv/.blocked.csv",
    )
    return parser.parse_args()


def subtract_months(value: date, months: int) -> date:
    total_months = (value.year * 12 + (value.month - 1)) - months
    year = total_months // 12
    month = total_months % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def sanitize_batch_key(batch_key: str) -> str:
    return batch_key.replace("|", "_").replace(" ", "_").replace("/", "_")


def parse_dt(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def parse_stage_set(value: str) -> frozenset[str]:
    return frozenset(part.strip() for part in (value or "").split(",") if part.strip())


def derive_site_geography(site_name: str) -> str:
    site = (site_name or "").strip()
    if not site:
        return "Unknown"
    if re.match(r"^S\d{2}(\b|\s|$)", site) or re.match(r"^[ALH]\d{2}(\b|\s|$)", site):
        return "Faroe Islands"
    if (
        re.match(r"^S\d{3}(\b|\s|$)", site)
        or re.match(r"^N\d+", site)
        or re.match(r"^FW\d+", site)
        or re.match(r"^BRS\d+", site)
    ):
        return "Scotland"
    return "Unknown"


def load_member_index(path: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    sites_by_batch: dict[str, set[str]] = defaultdict(set)
    stitched_geos_by_batch: dict[str, set[str]] = defaultdict(set)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            batch_key = (row.get("batch_key") or "").strip()
            if not batch_key:
                continue
            site = (row.get("org_unit_name") or "").strip()
            stitched_geo = (row.get("geography") or "").strip()
            if site:
                sites_by_batch[batch_key].add(site)
            if stitched_geo:
                stitched_geos_by_batch[batch_key].add(stitched_geo)
    return (
        {key: sorted(values) for key, values in sites_by_batch.items()},
        {key: sorted(values) for key, values in stitched_geos_by_batch.items()},
    )


def resolve_component_key(report_dir: Path) -> str | None:
    path = report_dir / "components.csv"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            component_key = (row.get("component_key") or "").strip()
            if component_key:
                return component_key
    return None


def analyze_transfer_state(report_dir: Path, extract_dir: Path) -> dict[str, Any]:
    component_key = resolve_component_key(report_dir)
    members = load_members_from_report(report_dir, component_id=None, component_key=None)
    population_ids = {member.population_id for member in members if member.population_id}
    raw_rows = load_subtransfers_from_csv(extract_dir, population_ids)
    expanded_rows = expand_subtransfer_rows_for_source_scope(raw_rows, population_ids)
    old_internal = {
        (
            (row.get("OperationID") or "").strip(),
            (row.get("SourcePopBefore") or "").strip(),
            (row.get("DestPopAfter") or "").strip(),
        )
        for row in raw_rows
        if (row.get("SourcePopBefore") or "").strip() in population_ids
        and (row.get("DestPopAfter") or "").strip() in population_ids
    }
    new_internal = {
        (
            (row.get("OperationID") or "").strip(),
            (row.get("SourcePop") or "").strip(),
            (row.get("DestPop") or "").strip(),
        )
        for row in expanded_rows
        if (row.get("DestPop") or "").strip() in population_ids
    }
    return {
        "component_key": component_key,
        "member_count": len(population_ids),
        "raw_subtransfer_rows": len(raw_rows),
        "expanded_subtransfer_rows": len(expanded_rows),
        "old_internal_edge_count": len(old_internal),
        "new_internal_edge_count": len(new_internal),
        "missing_edge_count": len(new_internal - old_internal),
        "transfer_bearing": bool(raw_rows),
    }


def has_population_component_map(component_key: str | None) -> bool:
    if not component_key:
        return False
    return ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model="PopulationComponent",
        source_identifier=component_key,
    ).exists()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def compact_json_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for row in rows:
        compacted.append(
            {
                key: value
                for key, value in row.items()
                if (
                    value is not None
                    and value != ""
                    and value != []
                    and (value is not False or key in {"has_report_dir", "replay_candidate", "transfer_bearing"})
                )
                or key in {"has_report_dir", "replay_candidate", "transfer_bearing"}
            }
        )
    return compacted


def build_summary(rows: list[dict[str, Any]], *, cutoff_date: str, threshold_date: str) -> dict[str, Any]:
    strict_rows = rows
    replay_rows = [row for row in rows if row["replay_candidate"]]
    transfer_queue_rows = [
        row
        for row in rows
        if row["classification"] == "eligible" and row["transfer_bearing"]
    ]
    replay_transfer_queue_rows = [
        row
        for row in transfer_queue_rows
        if row["replay_candidate"]
    ]
    strict_only_transfer_queue_rows = [
        row
        for row in transfer_queue_rows
        if not row["replay_candidate"]
    ]
    manual_rows = [row for row in rows if row["classification"] == "manual_reconstruction_exception"]
    blocked_rows = [row for row in rows if row["classification"] == "blocked"]
    classification_counts = Counter(row["classification"] for row in rows)
    replay_classification_counts = Counter(row["classification"] for row in replay_rows)
    strict_geo_counts = Counter(row["derived_geography"] for row in strict_rows)
    replay_geo_counts = Counter(row["derived_geography"] for row in replay_rows)
    blocked_reason_counts = Counter(row["classification_reason"] for row in blocked_rows)
    missing_edge_rows = [
        row
        for row in transfer_queue_rows
        if int(row.get("missing_edge_count") or 0) > 0
    ]
    return {
        "cutoff_date": cutoff_date,
        "threshold_date": threshold_date,
        "strict_scope_total": len(strict_rows),
        "strict_scope_geography_counts": dict(sorted(strict_geo_counts.items())),
        "strict_scope_classification_counts": dict(sorted(classification_counts.items())),
        "strict_scope_transfer_queue_total": len(transfer_queue_rows),
        "strict_scope_transfer_queue_with_missing_edges": len(missing_edge_rows),
        "replay_candidate_total": len(replay_rows),
        "replay_candidate_geography_counts": dict(sorted(replay_geo_counts.items())),
        "replay_candidate_classification_counts": dict(sorted(replay_classification_counts.items())),
        "replay_candidate_transfer_queue_total": len(replay_transfer_queue_rows),
        "strict_only_transfer_queue_total": len(strict_only_transfer_queue_rows),
        "manual_reconstruction_total": len(manual_rows),
        "manual_transfer_bearing_total": sum(1 for row in manual_rows if row["transfer_bearing"]),
        "blocked_total": len(blocked_rows),
        "blocked_reason_counts": dict(sorted(blocked_reason_counts.items())),
        "top_missing_edge_batches": [
            {
                "batch_key": row["batch_key"],
                "derived_geography": row["derived_geography"],
                "aquamind_stages": row["aquamind_stages"],
                "raw_subtransfer_rows": row["raw_subtransfer_rows"],
                "missing_edge_count": row["missing_edge_count"],
            }
            for row in sorted(
                missing_edge_rows,
                key=lambda item: (-int(item["missing_edge_count"]), item["batch_key"]),
            )[:20]
        ],
    }


def render_markdown(
    summary: dict[str, Any],
    *,
    transfer_queue_csv: Path,
    strict_csv: Path,
    replay_csv: Path,
    manual_csv: Path,
    blocked_csv: Path,
) -> str:
    lines: list[str] = []
    lines.append("# FW U30 Two-Geography Scope And Transfer Queue")
    lines.append("")
    lines.append("## Scope Basis")
    lines.append("")
    lines.append(f"- Cutoff date: `{summary['cutoff_date']}`")
    lines.append(f"- `<30 months` threshold: `{summary['threshold_date']}`")
    lines.append("- Strict FW-only rule: valid + start on/after threshold + stages subset `{Egg&Alevin,Fry,Parr,Smolt}`")
    lines.append("- Replay-candidate rule: strict FW-only rows excluding singleton `{Egg&Alevin}` and `{Fry}` signatures")
    lines.append("- Geography basis: site-derived policy heuristics from `DATA_MAPPING_DOCUMENT.md`, not the stale stitched `geographies` field")
    lines.append("")
    lines.append("## Strict Scope")
    lines.append("")
    lines.append(f"- Strict rows: `{summary['strict_scope_total']}`")
    lines.append(f"- Geography split: `{summary['strict_scope_geography_counts']}`")
    lines.append(f"- Classification split: `{summary['strict_scope_classification_counts']}`")
    lines.append(f"- Eligible non-manual transfer-bearing rows: `{summary['strict_scope_transfer_queue_total']}`")
    lines.append(f"- Of those, rows with missing-edge exposure signal: `{summary['strict_scope_transfer_queue_with_missing_edges']}`")
    lines.append("")
    lines.append("## Replay Candidates")
    lines.append("")
    lines.append(f"- Replay-candidate rows: `{summary['replay_candidate_total']}`")
    lines.append(f"- Geography split: `{summary['replay_candidate_geography_counts']}`")
    lines.append(f"- Classification split: `{summary['replay_candidate_classification_counts']}`")
    lines.append(f"- Replay-candidate transfer queue rows: `{summary['replay_candidate_transfer_queue_total']}`")
    lines.append(f"- Additional strict-only early-stage transfer rows outside the older replay subset: `{summary['strict_only_transfer_queue_total']}`")
    lines.append("")
    lines.append("## Manual And Blocked")
    lines.append("")
    lines.append(f"- Manual reconstruction exceptions: `{summary['manual_reconstruction_total']}`")
    lines.append(f"- Manual exceptions that are transfer-bearing: `{summary['manual_transfer_bearing_total']}`")
    lines.append(f"- Blocked rows: `{summary['blocked_total']}`")
    lines.append(f"- Blocked reason counts: `{summary['blocked_reason_counts']}`")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- Strict scope CSV: `{strict_csv}`")
    lines.append(f"- Replay-candidate CSV: `{replay_csv}`")
    lines.append(f"- Transfer queue CSV: `{transfer_queue_csv}`")
    lines.append(f"- Manual exceptions CSV: `{manual_csv}`")
    lines.append(f"- Blocked rows CSV: `{blocked_csv}`")
    lines.append("")
    lines.append("## Top Missing-Edge Signals")
    lines.append("")
    lines.append("| Batch Key | Geography | Stages | Raw SubTransfers | Missing Edges |")
    lines.append("|---|---|---|---:|---:|")
    for row in summary["top_missing_edge_batches"]:
        lines.append(
            f"| `{row['batch_key']}` | `{row['derived_geography']}` | `{row['aquamind_stages']}` | "
            f"`{row['raw_subtransfer_rows']}` | `{row['missing_edge_count']}` |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    cutoff_day = date.fromisoformat(args.cutoff_date)
    threshold_day = subtract_months(cutoff_day, 30)
    output_prefix = args.output_prefix
    output_prefix.parent.mkdir(parents=True, exist_ok=True)

    sites_by_batch, stitched_geos_by_batch = load_member_index(args.input_members)
    rows: list[dict[str, Any]] = []
    with args.input_batches.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for source_row in reader:
            if (source_row.get("is_valid") or "").strip() != "True":
                continue
            earliest_start = parse_dt(source_row.get("earliest_start") or "")
            if earliest_start is None or earliest_start.date() < threshold_day:
                continue
            stage_set = parse_stage_set(source_row.get("aquamind_stages") or "")
            if not stage_set or not stage_set.issubset(ALLOWED_STAGES):
                continue

            batch_key = (source_row.get("batch_key") or "").strip()
            member_sites = sites_by_batch.get(batch_key, [])
            derived_geo_set = sorted(
                {
                    derive_site_geography(site)
                    for site in member_sites
                    if derive_site_geography(site) != "Unknown"
                }
            )
            if not derived_geo_set:
                derived_geography = "Unknown"
            elif len(derived_geo_set) == 1:
                derived_geography = derived_geo_set[0]
            else:
                derived_geography = "Mixed"

            report_dir = args.report_root / sanitize_batch_key(batch_key)
            has_report_dir = report_dir.exists()
            has_components_csv = (report_dir / "components.csv").exists()
            has_population_members_csv = (report_dir / "population_members.csv").exists()
            component_key = resolve_component_key(report_dir) if has_components_csv else None
            has_component_map = has_population_component_map(component_key)

            if not has_report_dir:
                classification = "blocked"
                classification_reason = "Missing input_batch_migration report dir."
            elif not has_components_csv:
                classification = "blocked"
                classification_reason = "Report dir missing components.csv."
            elif not has_population_members_csv:
                classification = "blocked"
                classification_reason = "Report dir missing population_members.csv."
            elif not component_key:
                classification = "blocked"
                classification_reason = "Unable to resolve component_key from components.csv."
            elif not has_component_map:
                classification = "blocked"
                classification_reason = "Missing ExternalIdMap for PopulationComponent."
            elif batch_key in MANUAL_RECONSTRUCTION:
                classification = "manual_reconstruction_exception"
                classification_reason = MANUAL_RECONSTRUCTION[batch_key]
            else:
                classification = "eligible"
                classification_reason = (
                    "Current input-batch report dir with components.csv and population_members.csv exists."
                )

            row: dict[str, Any] = {
                "batch_key": batch_key,
                "input_name": (source_row.get("input_name") or "").strip(),
                "input_number": (source_row.get("input_number") or "").strip(),
                "year_class": (source_row.get("year_class") or "").strip(),
                "earliest_start": earliest_start.isoformat(sep=" "),
                "latest_activity": (source_row.get("latest_activity") or "").strip(),
                "aquamind_stages": ", ".join(sorted(stage_set, key=["Egg&Alevin", "Fry", "Parr", "Smolt"].index)),
                "stage_signature": "|".join(sorted(stage_set)),
                "population_count": (source_row.get("population_count") or "").replace(",", "").strip(),
                "total_fish": (source_row.get("total_fish") or "").replace(",", "").strip(),
                "stitched_geographies": "; ".join(stitched_geos_by_batch.get(batch_key, [])),
                "member_sites": "; ".join(member_sites),
                "derived_geography": derived_geography,
                "derived_geographies": "; ".join(derived_geo_set),
                "report_dir": str(report_dir),
                "has_report_dir": has_report_dir,
                "has_components_csv": has_components_csv,
                "has_population_members_csv": has_population_members_csv,
                "has_population_component_map": has_component_map,
                "replay_candidate": stage_set not in EARLY_STAGE_ONLY,
                "classification": classification,
                "classification_reason": classification_reason,
                "component_key": component_key or "",
                "member_count": 0,
                "raw_subtransfer_rows": 0,
                "expanded_subtransfer_rows": 0,
                "old_internal_edge_count": 0,
                "new_internal_edge_count": 0,
                "missing_edge_count": 0,
                "transfer_bearing": False,
            }

            if has_components_csv and has_population_members_csv:
                row.update(analyze_transfer_state(report_dir, args.extract_dir))

            rows.append(row)

    rows.sort(
        key=lambda item: (
            item["derived_geography"],
            item["earliest_start"],
            item["batch_key"],
        )
    )

    strict_csv = output_prefix.with_suffix(".strict.csv")
    replay_csv = output_prefix.with_suffix(".replay.csv")
    transfer_queue_csv = output_prefix.with_suffix(".transfer_queue.csv")
    manual_csv = output_prefix.with_suffix(".manual.csv")
    blocked_csv = output_prefix.with_suffix(".blocked.csv")
    output_json = output_prefix.with_suffix(".json")
    output_md = output_prefix.with_suffix(".md")

    replay_rows = [row for row in rows if row["replay_candidate"]]
    transfer_queue_rows = [
        row
        for row in rows
        if row["classification"] == "eligible" and row["transfer_bearing"]
    ]
    manual_rows = [
        row for row in rows if row["classification"] == "manual_reconstruction_exception"
    ]
    blocked_rows = [row for row in rows if row["classification"] == "blocked"]

    write_csv(strict_csv, rows)
    write_csv(replay_csv, replay_rows)
    write_csv(transfer_queue_csv, transfer_queue_rows)
    write_csv(manual_csv, manual_rows)
    write_csv(blocked_csv, blocked_rows)

    summary = build_summary(
        rows,
        cutoff_date=args.cutoff_date,
        threshold_date=threshold_day.isoformat(),
    )
    payload = {
        "summary": summary,
        "artifacts": {
            "strict_csv": str(strict_csv),
            "replay_csv": str(replay_csv),
            "transfer_queue_csv": str(transfer_queue_csv),
            "manual_csv": str(manual_csv),
            "blocked_csv": str(blocked_csv),
            "markdown": str(output_md),
        },
        "rows": compact_json_rows(rows),
    }
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    output_md.write_text(
        render_markdown(
            summary,
            transfer_queue_csv=transfer_queue_csv,
            strict_csv=strict_csv,
            replay_csv=replay_csv,
            manual_csv=manual_csv,
            blocked_csv=blocked_csv,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
