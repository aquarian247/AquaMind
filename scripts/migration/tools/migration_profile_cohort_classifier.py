#!/usr/bin/env python3
# flake8: noqa
"""Classify cohort semantic summaries into profile recommendation groups."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migration.tools.extract_freshness_guard import (
    DEFAULT_BACKUP_HORIZON_DATE,
    DEFAULT_CSV_DIR,
    evaluate_extract_freshness,
    print_summary as print_extract_freshness_summary,
)


DEFAULT_ANALYSIS_DIR = (
    PROJECT_ROOT
    / "aquamind"
    / "docs"
    / "progress"
    / "migration"
    / "analysis_reports"
    / date.today().isoformat()
)


@dataclass(frozen=True)
class CohortClassification:
    batch_name: str
    batch_id: int | None
    component_key: str
    summary_path: str
    summary_mtime_iso: str
    summary_mtime_epoch: float
    signatures: list[str]
    recommended_profile: str
    confidence: str
    rationale: str
    recommended_override: str | None
    regression_gates_passed: bool
    outside_holder_count: int
    transition_alert_count: int
    non_bridge_zero_assignments: int
    zero_count_transfer_actions: int


def as_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def derive_profile_decision(
    *,
    regression_passed: bool,
    outside_holder_count: int,
    transition_alert_count: int,
    non_bridge_zero_assignments: int,
    zero_count_transfer_actions: int,
) -> tuple[list[str], str, str, str, str | None]:
    signatures: list[str] = []
    if outside_holder_count > 0:
        signatures.append("outside_holder_mismatch")
    if transition_alert_count > 0:
        signatures.append("transition_delta_alert")
    if non_bridge_zero_assignments > 0:
        signatures.append("non_bridge_zero_assignments")
    if zero_count_transfer_actions > 0:
        signatures.append("zero_count_transfer_actions")
    if not regression_passed:
        signatures.append("regression_gate_failure")
    if not signatures:
        signatures = ["clean"]

    if "outside_holder_mismatch" in signatures:
        return (
            signatures,
            "fw_default",
            "high",
            "Outside-holder mismatch requires strict holder-consistency behavior.",
            None,
        )
    if signatures == ["clean"]:
        return (
            signatures,
            "fw_default",
            "high",
            "No semantic or gate signatures indicate divergence from baseline.",
            None,
        )
    if (
        "transition_delta_alert" in signatures
        and "regression_gate_failure" not in signatures
    ):
        return (
            signatures,
            "legacy_latest_member",
            "medium",
            "Transition alerts suggest testing stage-mode sensitivity.",
            "--lifecycle-frontier-window-hours <tune> (or compare legacy_latest_member)",
        )
    if "non_bridge_zero_assignments" in signatures:
        return (
            signatures,
            "fw_default",
            "medium",
            "Non-bridge zero assignments suggest supersede-window tuning within strict baseline.",
            "--same-stage-supersede-max-hours <tune>",
        )
    return (
        signatures,
        "fw_default",
        "medium",
        "Keep strict default until cohort-specific evidence supports deviation.",
        None,
    )


def classify_summary(summary_path: Path) -> CohortClassification:
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    batch = payload.get("batch") or {}
    regression = payload.get("regression_gates") or {}
    stage_sanity = payload.get("stage_sanity") or {}
    occupancy = stage_sanity.get("active_container_occupancy_evidence") or {}
    transfer_actions = payload.get("transfer_actions") or {}

    batch_name = str(batch.get("batch_number") or summary_path.stem)
    batch_id = as_int(batch.get("id"), default=0) or None
    component_key = str(payload.get("component_key") or "")
    regression_passed = bool(regression.get("passed"))
    outside_holder_count = as_int(
        occupancy.get("latest_holder_outside_component_count"), default=0
    )
    transition_alert_count = as_int(
        regression.get("transition_alert_count"), default=0
    )
    non_bridge_zero_assignments = as_int(
        stage_sanity.get("zero_assignment_non_bridge_count")
        or regression.get("non_bridge_zero_assignments"),
        default=0,
    )
    zero_count_transfer_actions = as_int(
        transfer_actions.get("zero_count"),
        default=0,
    )

    (
        signatures,
        recommended_profile,
        confidence,
        rationale,
        recommended_override,
    ) = derive_profile_decision(
        regression_passed=regression_passed,
        outside_holder_count=outside_holder_count,
        transition_alert_count=transition_alert_count,
        non_bridge_zero_assignments=non_bridge_zero_assignments,
        zero_count_transfer_actions=zero_count_transfer_actions,
    )
    mtime_epoch = float(summary_path.stat().st_mtime)
    mtime_iso = datetime.fromtimestamp(mtime_epoch).isoformat(
        sep=" ", timespec="seconds"
    )

    return CohortClassification(
        batch_name=batch_name,
        batch_id=batch_id,
        component_key=component_key,
        summary_path=str(summary_path),
        summary_mtime_iso=mtime_iso,
        summary_mtime_epoch=mtime_epoch,
        signatures=signatures,
        recommended_profile=recommended_profile,
        confidence=confidence,
        rationale=rationale,
        recommended_override=recommended_override,
        regression_gates_passed=regression_passed,
        outside_holder_count=outside_holder_count,
        transition_alert_count=transition_alert_count,
        non_bridge_zero_assignments=non_bridge_zero_assignments,
        zero_count_transfer_actions=zero_count_transfer_actions,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Classify cohort semantic summaries into profile recommendation groups "
            "and emit markdown/json outputs."
        )
    )
    parser.add_argument(
        "--analysis-dir",
        default=str(DEFAULT_ANALYSIS_DIR),
        help="Directory containing semantic validation summary JSON files.",
    )
    parser.add_argument(
        "--summary-glob",
        default="*semantic_validation*.summary.json",
        help="Rglob pattern for summary JSON files (default: *semantic_validation*.summary.json).",
    )
    parser.add_argument(
        "--csv-dir",
        default=str(DEFAULT_CSV_DIR),
        help="Extract CSV directory used for freshness preflight.",
    )
    parser.add_argument(
        "--skip-extract-freshness-preflight",
        action="store_true",
        help="Skip extract freshness preflight before classification.",
    )
    parser.add_argument(
        "--extract-horizon-date",
        default=DEFAULT_BACKUP_HORIZON_DATE,
        help=(
            "Required horizon date (YYYY-MM-DD) for extract preflight. "
            "status_values/sub_transfers max dates must be >= this. "
            f"(default: {DEFAULT_BACKUP_HORIZON_DATE})"
        ),
    )
    parser.add_argument(
        "--extract-max-status-subtransfer-skew-hours",
        type=int,
        default=24,
        help="Max allowed skew between status_values and sub_transfers max times.",
    )
    parser.add_argument(
        "--extract-max-operation-stage-lag-days",
        type=int,
        default=14,
        help="Max allowed lag for operation_stage_changes behind status/sub anchor.",
    )
    lag_group = parser.add_mutually_exclusive_group()
    lag_group.add_argument(
        "--extract-enforce-operation-stage-lag",
        dest="extract_enforce_operation_stage_lag",
        action="store_true",
        help=(
            "Treat operation_stage_changes lag threshold breaches as failures "
            "(default)."
        ),
    )
    lag_group.add_argument(
        "--extract-allow-operation-stage-lag",
        dest="extract_enforce_operation_stage_lag",
        action="store_false",
        help=(
            "Downgrade operation_stage_changes lag threshold breaches to warnings."
        ),
    )
    parser.set_defaults(extract_enforce_operation_stage_lag=True)
    parser.add_argument(
        "--extract-fail-on-warnings",
        action="store_true",
        help="Fail preflight when warnings exist.",
    )
    parser.add_argument(
        "--output",
        help=(
            "Optional markdown output path. "
            "Default: <analysis-dir>/profile_cohort_classification_<today>.md"
        ),
    )
    parser.add_argument(
        "--summary-json",
        help=(
            "Optional JSON output path. "
            "Default: <analysis-dir>/profile_cohort_classification_<today>.summary.json"
        ),
    )
    parser.add_argument(
        "--no-dedupe-by-component-key",
        action="store_true",
        help=(
            "Do not deduplicate multiple summaries for the same component key. "
            "Default behavior keeps only the newest summary per component."
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    analysis_dir = Path(args.analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    extract_preflight = None
    if not args.skip_extract_freshness_preflight:
        extract_preflight = evaluate_extract_freshness(
            csv_dir=Path(args.csv_dir),
            horizon_date=args.extract_horizon_date,
            max_status_subtransfer_skew_hours=args.extract_max_status_subtransfer_skew_hours,
            max_operation_stage_lag_days=args.extract_max_operation_stage_lag_days,
            enforce_operation_stage_lag=args.extract_enforce_operation_stage_lag,
            fail_on_warnings=args.extract_fail_on_warnings,
        )
        print_extract_freshness_summary(extract_preflight)
        if not extract_preflight.passed:
            print(
                "\n[ERROR] Extract freshness preflight failed. "
                "Classification aborted."
            )
            return 1

    summary_paths = sorted(analysis_dir.rglob(args.summary_glob))
    if not summary_paths:
        print(
            f"No summary JSON files matched pattern '{args.summary_glob}' "
            f"under {analysis_dir}"
        )
        return 1

    cohort_rows: list[CohortClassification] = []
    skipped_files: list[str] = []
    for summary_path in summary_paths:
        try:
            cohort_rows.append(classify_summary(summary_path))
        except Exception as exc:
            skipped_files.append(f"{summary_path}: {exc}")

    if not args.no_dedupe_by_component_key and cohort_rows:
        latest_by_component: dict[str, CohortClassification] = {}
        for row in cohort_rows:
            dedupe_key = (
                row.component_key.strip().upper()
                if row.component_key.strip()
                else row.batch_name.strip().upper()
            )
            existing = latest_by_component.get(dedupe_key)
            if existing is None or row.summary_mtime_epoch > existing.summary_mtime_epoch:
                latest_by_component[dedupe_key] = row
        cohort_rows = list(latest_by_component.values())

    if not cohort_rows:
        print("No valid cohort summaries could be classified.")
        if skipped_files:
            for entry in skipped_files:
                print(f"- {entry}")
        return 1

    grouped: dict[tuple[str, tuple[str, ...]], list[CohortClassification]] = {}
    for row in cohort_rows:
        key = (row.recommended_profile, tuple(sorted(row.signatures)))
        grouped.setdefault(key, []).append(row)

    output_path = (
        Path(args.output)
        if args.output
        else analysis_dir / f"profile_cohort_classification_{date.today().isoformat()}.md"
    )
    summary_json_path = (
        Path(args.summary_json)
        if args.summary_json
        else analysis_dir
        / f"profile_cohort_classification_{date.today().isoformat()}.summary.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Migration Profile Cohort Classification")
    lines.append("")
    lines.append(f"- Generated: `{datetime.now().isoformat(sep=' ', timespec='seconds')}`")
    lines.append(f"- Analysis dir: `{analysis_dir}`")
    lines.append(f"- Summary glob: `{args.summary_glob}`")
    lines.append(
        "- Dedupe mode: "
        f"`{'disabled' if args.no_dedupe_by_component_key else 'newest-per-component'}`"
    )
    lines.append(f"- Cohorts classified: `{len(cohort_rows)}`")
    lines.append("")
    if extract_preflight is not None:
        lines.append("## Extract preflight")
        lines.append("")
        lines.append(f"- Result: `{'PASS' if extract_preflight.passed else 'FAIL'}`")
        lines.append(
            f"- Horizon date: `{extract_preflight.horizon_date or 'not set'}`"
        )
        if extract_preflight.status_subtransfer_skew_hours is not None:
            lines.append(
                "- Status/SubTransfers skew (hours): "
                f"`{extract_preflight.status_subtransfer_skew_hours:.2f}`"
            )
        if extract_preflight.operation_stage_lag_days is not None:
            lines.append(
                "- OperationStage lag (days): "
                f"`{extract_preflight.operation_stage_lag_days:.2f}`"
            )
        lines.append("")

    lines.append("## Cohort rows")
    lines.append("")
    lines.append(
        "| Batch | Component key | Signatures | Recommended profile | Confidence | Gates | "
        "Outside-holder | Transition alerts | Non-bridge zeros | Zero transfer actions |"
    )
    lines.append(
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |"
    )
    for row in sorted(cohort_rows, key=lambda value: value.batch_name.lower()):
        lines.append(
            f"| {row.batch_name} | `{row.component_key}` | "
            f"`{', '.join(row.signatures)}` | `{row.recommended_profile}` | "
            f"`{row.confidence}` | "
            f"{'PASS' if row.regression_gates_passed else 'FAIL'} | "
            f"{row.outside_holder_count} | {row.transition_alert_count} | "
            f"{row.non_bridge_zero_assignments} | {row.zero_count_transfer_actions} |"
        )

    lines.append("")
    lines.append("## Grouped recommendations")
    lines.append("")
    lines.append("| Recommended profile | Signature set | Cohort count | Cohorts |")
    lines.append("| --- | --- | ---: | --- |")
    for (profile, signatures), rows in sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), item[0][0], ",".join(item[0][1])),
    ):
        cohort_names = ", ".join(sorted(row.batch_name for row in rows))
        lines.append(
            f"| `{profile}` | `{', '.join(signatures)}` | {len(rows)} | {cohort_names} |"
        )

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    if skipped_files:
        lines.append("- Skipped summary files due to parse errors:")
        for entry in skipped_files:
            lines.append(f"  - `{entry}`")
    else:
        lines.append("- No summary files were skipped.")

    lines.append(
        "- Create new profiles only when at least 3 cohorts share a stable "
        "failure signature and the mitigation is policy-like."
    )
    lines.append(
        "- Keep `fw_default` as baseline and treat relaxed/legacy profiles as "
        "diagnostic controls unless validated by regression gates."
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")

    summary_payload = {
        "generated_at": datetime.now().isoformat(sep=" ", timespec="seconds"),
        "analysis_dir": str(analysis_dir),
        "summary_glob": args.summary_glob,
        "cohort_count": len(cohort_rows),
        "extract_preflight": (
            extract_preflight.to_dict() if extract_preflight is not None else None
        ),
        "cohorts": [asdict(row) for row in cohort_rows],
        "groups": [
            {
                "recommended_profile": profile,
                "signatures": list(signatures),
                "cohort_count": len(rows),
                "cohorts": [
                    {
                        "batch_name": row.batch_name,
                        "component_key": row.component_key,
                    }
                    for row in sorted(rows, key=lambda value: value.batch_name.lower())
                ],
            }
            for (profile, signatures), rows in sorted(
                grouped.items(),
                key=lambda item: (-len(item[1]), item[0][0], ",".join(item[0][1])),
            )
        ],
        "skipped_files": skipped_files,
    }
    summary_json_path.write_text(
        json.dumps(summary_payload, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote classification report: {output_path}")
    print(f"Wrote classification summary: {summary_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
