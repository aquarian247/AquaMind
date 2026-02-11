#!/usr/bin/env python3
# flake8: noqa
"""Run semantic validation + regression gates for migrated pilot components."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SEMANTIC_SCRIPT = PROJECT_ROOT / "scripts" / "migration" / "tools" / "migration_semantic_validation_report.py"
FWSEA_ENDPOINT_GATE_SCRIPT = (
    PROJECT_ROOT / "scripts" / "migration" / "tools" / "fwsea_endpoint_pairing_gate.py"
)
DEFAULT_ANALYSIS_DIR = (
    PROJECT_ROOT
    / "aquamind"
    / "docs"
    / "progress"
    / "migration"
    / "analysis_reports"
    / "2026-02-06"
)
DEFAULT_REPORT_DIR_ROOT = PROJECT_ROOT / "scripts" / "migration" / "output" / "input_batch_migration"
DEFAULT_CSV_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"


@dataclass(frozen=True)
class PilotComponent:
    batch_name: str
    component_key: str
    report_dir_name: str
    report_filename: str
    summary_filename: str


PILOT_COMPONENTS = [
    PilotComponent(
        batch_name="SF NOV 23",
        component_key="FA8EA452-AFE1-490D-B236-0150415B6E6F",
        report_dir_name="SF_NOV_23_5_2023",
        report_filename="semantic_validation_sf_nov_23_2026-02-06.md",
        summary_filename="semantic_validation_sf_nov_23_2026-02-06.summary.json",
    ),
    PilotComponent(
        batch_name="Stofnfiskur S-21 nov23",
        component_key="B884F78F-1E92-49C0-AE28-39DFC2E18C01",
        report_dir_name="Stofnfiskur_S-21_nov23_5_2023",
        report_filename="semantic_validation_stofnfiskur_s21_nov23_2026-02-06.md",
        summary_filename="semantic_validation_stofnfiskur_s21_nov23_2026-02-06.summary.json",
    ),
    PilotComponent(
        batch_name="Benchmark Gen. Juni 2024",
        component_key="5DC4DA59-A891-4BBB-BB2E-0CC95C633F20",
        report_dir_name="Benchmark_Gen._Juni_2024_2_2024",
        report_filename="semantic_validation_benchmark_gen_juni_2024_2026-02-06.md",
        summary_filename="semantic_validation_benchmark_gen_juni_2024_2026-02-06.summary.json",
    ),
    PilotComponent(
        batch_name="Summar 2024",
        component_key="81AC7D6F-3C81-4F36-9875-881C828F62E3",
        report_dir_name="Summar_2024_1_2024_433A6D50-7B57-4309-8D16-776C5D1DE1B5",
        report_filename="semantic_validation_summar_2024_2026-02-06.md",
        summary_filename="semantic_validation_summar_2024_2026-02-06.summary.json",
    ),
    PilotComponent(
        batch_name="Vár 2024",
        component_key="251B661F-E0A6-4AD0-9B59-40A6CE1ADC86",
        report_dir_name="Vár_2024_1_2024_82A9B732-322F-4D4C-AD7C-E09ACC7F8545",
        report_filename="semantic_validation_var_2024_2026-02-06.md",
        summary_filename="semantic_validation_var_2024_2026-02-06.summary.json",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run semantic validation regression gates for migrated pilot components"
    )
    parser.add_argument(
        "--analysis-dir",
        default=str(DEFAULT_ANALYSIS_DIR),
        help="Directory where semantic markdown and JSON summary outputs are written",
    )
    parser.add_argument(
        "--report-dir-root",
        default=str(DEFAULT_REPORT_DIR_ROOT),
        help="Root directory containing per-component population_members.csv report directories",
    )
    parser.add_argument(
        "--use-csv",
        default=str(DEFAULT_CSV_DIR),
        help="FishTalk CSV extract directory",
    )
    parser.add_argument(
        "--stage-entry-window-days",
        type=int,
        default=2,
        help="Stage-entry window days passed to semantic validator (default: 2)",
    )
    parser.add_argument(
        "--max-non-bridge-zero-assignments",
        type=int,
        default=2,
        help="Regression gate threshold passed to semantic validator (default: 2)",
    )
    parser.add_argument(
        "--component-key",
        action="append",
        default=[],
        help="Optional component key filter (repeatable); defaults to full pilot set.",
    )
    parser.add_argument(
        "--cohort-output",
        help=(
            "Optional cohort markdown output path. "
            "Default: <analysis-dir>/semantic_validation_pilot_cohort_<today>.md"
        ),
    )
    parser.add_argument(
        "--run-fwsea-endpoint-gates",
        action="store_true",
        help="Run FWSEA endpoint-pairing acceptance gate tooling per component",
    )
    parser.add_argument(
        "--fwsea-endpoint-enforce",
        action="store_true",
        help="Treat FWSEA endpoint gate failures as regression failure",
    )
    parser.add_argument(
        "--fwsea-endpoint-expected-direction",
        choices=("any", "sales_to_input", "input_to_sales"),
        default="sales_to_input",
        help="Expected endpoint direction for deterministic FWSEA rows (default: sales_to_input)",
    )
    parser.add_argument(
        "--fwsea-endpoint-max-source-candidates",
        type=int,
        default=2,
        help="Max source endpoint candidates per row (default: 2)",
    )
    parser.add_argument(
        "--fwsea-endpoint-max-target-candidates",
        type=int,
        default=1,
        help="Max target endpoint candidates per row (default: 1)",
    )
    parser.add_argument(
        "--fwsea-endpoint-min-deterministic-coverage",
        type=float,
        default=0.9,
        help="Minimum deterministic coverage for endpoint candidates (default: 0.9)",
    )
    parser.add_argument(
        "--fwsea-endpoint-max-ambiguous-rows",
        type=int,
        default=0,
        help="Maximum ambiguous endpoint candidate rows allowed (default: 0)",
    )
    parser.add_argument(
        "--fwsea-endpoint-max-targets-per-source",
        type=int,
        default=1,
        help="Maximum target endpoints per source endpoint (default: 1)",
    )
    parser.add_argument(
        "--fwsea-endpoint-min-candidate-rows",
        type=int,
        default=10,
        help="Minimum endpoint candidate rows required for evidence gate (default: 10)",
    )
    parser.add_argument(
        "--fwsea-endpoint-require-evidence",
        action="store_true",
        help="Require endpoint evidence gate to pass (candidate rows >= min threshold)",
    )
    parser.add_argument(
        "--fwsea-endpoint-require-marine-target",
        action="store_true",
        help="Require deterministic endpoint rows to target marine populations",
    )
    parser.add_argument(
        "--fwsea-endpoint-min-marine-target-ratio",
        type=float,
        default=1.0,
        help="Minimum marine-target ratio when marine-target gate is enabled (default: 1.0)",
    )
    parser.add_argument(
        "--fwsea-endpoint-max-incomplete-linkage-fallback",
        type=int,
        help="Optional max incomplete-linkage fallback threshold from semantic summary",
    )
    parser.add_argument(
        "--fwsea-endpoint-baseline-incomplete-linkage-fallback",
        type=int,
        help="Optional baseline incomplete-linkage fallback count; current must be <= baseline",
    )
    return parser.parse_args()


def format_pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.0"
    return f"{(numerator / denominator) * 100:.1f}"


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return slug or "component"


def main() -> int:
    args = parse_args()
    analysis_dir = Path(args.analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    report_dir_root = Path(args.report_dir_root)
    csv_dir = Path(args.use_csv)

    selected_components = PILOT_COMPONENTS
    if args.component_key:
        allowed = {value.strip().upper() for value in args.component_key if value and value.strip()}
        selected_components = [
            component for component in PILOT_COMPONENTS if component.component_key.upper() in allowed
        ]
        if not selected_components:
            print("No pilot components matched --component-key filters.")
            return 1

    component_rows: list[dict] = []
    failed_components: list[str] = []
    endpoint_failed_components: list[str] = []
    endpoint_component_rows: list[dict] = []
    aggregated_basis_counts: defaultdict[str, int] = defaultdict(int)
    aggregated_reason_counts: defaultdict[str, int] = defaultdict(int)

    for component in selected_components:
        report_dir = report_dir_root / component.report_dir_name
        report_path = analysis_dir / component.report_filename
        summary_path = analysis_dir / component.summary_filename

        cmd = [
            sys.executable,
            str(SEMANTIC_SCRIPT),
            "--component-key",
            component.component_key,
            "--report-dir",
            str(report_dir),
            "--use-csv",
            str(csv_dir),
            "--stage-entry-window-days",
            str(args.stage_entry_window_days),
            "--max-non-bridge-zero-assignments",
            str(args.max_non_bridge_zero_assignments),
            "--output",
            str(report_path),
            "--summary-json",
            str(summary_path),
            "--check-regression-gates",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        if result.returncode != 0:
            failed_components.append(component.batch_name)

        if summary_path.exists():
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            stage_sanity = payload.get("stage_sanity") or {}
            gates = payload.get("regression_gates") or {}
            transfer_actions = payload.get("transfer_actions") or {}
        else:
            failed_components.append(component.batch_name)
            stage_sanity = {}
            gates = {}
            transfer_actions = {}

        transition_count = int(stage_sanity.get("transition_count") or 0)
        bridge_aware_count = int(stage_sanity.get("transition_bridge_aware_count") or 0)
        entry_window_count = int(stage_sanity.get("transition_entry_window_count") or 0)
        for key, value in (stage_sanity.get("transition_basis_counts") or {}).items():
            aggregated_basis_counts[key] += int(value or 0)
        for key, value in (stage_sanity.get("transition_entry_window_reason_counts") or {}).items():
            aggregated_reason_counts[key] += int(value or 0)

        row = {
            "batch_name": component.batch_name,
            "component_key": component.component_key,
            "transition_count": transition_count,
            "bridge_aware_count": bridge_aware_count,
            "entry_window_count": entry_window_count,
            "entry_window_rate_pct": format_pct(entry_window_count, transition_count),
            "positive_transition_alert_count": int(gates.get("transition_alert_count") or 0),
            "zero_count_transfer_actions": int(transfer_actions.get("zero_count") or 0),
            "non_bridge_zero_assignments": int(stage_sanity.get("zero_assignment_non_bridge_count") or 0),
            "regression_gates_passed": bool(gates.get("passed")),
            "fwsea_endpoint_gate_applicable": False,
            "fwsea_endpoint_gate_passed": None,
            "fwsea_endpoint_candidate_rows": None,
            "fwsea_endpoint_deterministic_rows": None,
            "fwsea_endpoint_coverage_pct": None,
            "fwsea_endpoint_max_targets_per_source": None,
            "fwsea_endpoint_report_name": None,
        }

        if args.run_fwsea_endpoint_gates:
            endpoint_slug = safe_slug(component.report_dir_name)
            endpoint_report_path = (
                analysis_dir
                / f"fwsea_endpoint_gate_{endpoint_slug}_{date.today().isoformat()}.md"
            )
            endpoint_summary_path = (
                analysis_dir
                / f"fwsea_endpoint_gate_{endpoint_slug}_{date.today().isoformat()}.summary.json"
            )
            endpoint_cmd = [
                sys.executable,
                str(FWSEA_ENDPOINT_GATE_SCRIPT),
                "--csv-dir",
                str(csv_dir),
                "--report-dir",
                str(report_dir),
                "--component-key",
                component.component_key,
                "--expected-direction",
                args.fwsea_endpoint_expected_direction,
                "--max-source-candidates",
                str(args.fwsea_endpoint_max_source_candidates),
                "--max-target-candidates",
                str(args.fwsea_endpoint_max_target_candidates),
                "--min-deterministic-coverage",
                str(args.fwsea_endpoint_min_deterministic_coverage),
                "--max-ambiguous-rows",
                str(args.fwsea_endpoint_max_ambiguous_rows),
                "--max-targets-per-source",
                str(args.fwsea_endpoint_max_targets_per_source),
                "--min-candidate-rows",
                str(args.fwsea_endpoint_min_candidate_rows),
                "--output",
                str(endpoint_report_path),
                "--summary-json",
                str(endpoint_summary_path),
                "--semantic-summary-json",
                str(summary_path),
            ]
            if args.fwsea_endpoint_require_evidence:
                endpoint_cmd.append("--require-evidence")
            if args.fwsea_endpoint_require_marine_target:
                endpoint_cmd.append("--require-marine-target")
                endpoint_cmd.extend(
                    [
                        "--min-marine-target-ratio",
                        str(args.fwsea_endpoint_min_marine_target_ratio),
                    ]
                )
            if args.fwsea_endpoint_max_incomplete_linkage_fallback is not None:
                endpoint_cmd.extend(
                    [
                        "--max-incomplete-linkage-fallback",
                        str(args.fwsea_endpoint_max_incomplete_linkage_fallback),
                    ]
                )
            if args.fwsea_endpoint_baseline_incomplete_linkage_fallback is not None:
                endpoint_cmd.extend(
                    [
                        "--baseline-incomplete-linkage-fallback",
                        str(args.fwsea_endpoint_baseline_incomplete_linkage_fallback),
                    ]
                )
            if args.fwsea_endpoint_enforce:
                endpoint_cmd.append("--check-gates")

            endpoint_result = subprocess.run(endpoint_cmd, capture_output=True, text=True)
            if endpoint_result.stdout.strip():
                print(endpoint_result.stdout.strip())
            if endpoint_result.stderr.strip():
                print(endpoint_result.stderr.strip())

            row["fwsea_endpoint_gate_applicable"] = True
            row["fwsea_endpoint_report_name"] = endpoint_report_path.name

            if endpoint_summary_path.exists():
                endpoint_payload = json.loads(endpoint_summary_path.read_text(encoding="utf-8"))
                endpoint_metrics = endpoint_payload.get("metrics") or {}
                endpoint_gates = endpoint_payload.get("gates") or {}
                row["fwsea_endpoint_gate_passed"] = bool(endpoint_gates.get("overall_passed"))
                row["fwsea_endpoint_candidate_rows"] = int(endpoint_metrics.get("candidate_rows") or 0)
                row["fwsea_endpoint_deterministic_rows"] = int(endpoint_metrics.get("deterministic_rows") or 0)
                coverage = float(endpoint_metrics.get("deterministic_coverage") or 0.0)
                row["fwsea_endpoint_coverage_pct"] = f"{coverage * 100:.1f}"
                row["fwsea_endpoint_max_targets_per_source"] = int(
                    endpoint_metrics.get("max_targets_per_source_observed") or 0
                )

                endpoint_component_rows.append(
                    {
                        "batch_name": component.batch_name,
                        "component_key": component.component_key,
                        "candidate_rows": row["fwsea_endpoint_candidate_rows"],
                        "deterministic_rows": row["fwsea_endpoint_deterministic_rows"],
                        "coverage_pct": row["fwsea_endpoint_coverage_pct"],
                        "max_targets_per_source": row["fwsea_endpoint_max_targets_per_source"],
                        "gate_passed": row["fwsea_endpoint_gate_passed"],
                        "report_name": endpoint_report_path.name,
                    }
                )

            if args.fwsea_endpoint_enforce and endpoint_result.returncode != 0:
                endpoint_failed_components.append(component.batch_name)

        component_rows.append(row)
        if not row["regression_gates_passed"]:
            failed_components.append(component.batch_name)
        if (
            args.run_fwsea_endpoint_gates
            and args.fwsea_endpoint_enforce
            and row["fwsea_endpoint_gate_passed"] is False
        ):
            endpoint_failed_components.append(component.batch_name)

    total_transitions = sum(row["transition_count"] for row in component_rows)
    total_bridge_aware = sum(row["bridge_aware_count"] for row in component_rows)
    total_entry_window = sum(row["entry_window_count"] for row in component_rows)
    total_positive_alerts = sum(row["positive_transition_alert_count"] for row in component_rows)
    total_zero_transfer_actions = sum(row["zero_count_transfer_actions"] for row in component_rows)
    total_non_bridge_zero_assignments = sum(row["non_bridge_zero_assignments"] for row in component_rows)

    cohort_output = (
        Path(args.cohort_output)
        if args.cohort_output
        else analysis_dir / f"semantic_validation_pilot_cohort_{date.today().isoformat()}.md"
    )
    lines: list[str] = []
    lines.append("# Semantic Validation Pilot Cohort Regression Check")
    lines.append("")
    lines.append(f"- Components checked: {len(component_rows)}")
    lines.append(f"- Stage-entry window days: {args.stage_entry_window_days}")
    lines.append(f"- CSV extract: `{csv_dir}`")
    lines.append(f"- Non-bridge zero-assignment threshold: {args.max_non_bridge_zero_assignments}")
    lines.append(
        f"- FWSEA endpoint gates: {'enabled' if args.run_fwsea_endpoint_gates else 'disabled'} "
        f"(enforce={args.fwsea_endpoint_enforce})"
    )
    if args.run_fwsea_endpoint_gates:
        lines.append(
            "- FWSEA endpoint thresholds: "
            f"direction={args.fwsea_endpoint_expected_direction}, "
            f"source<= {args.fwsea_endpoint_max_source_candidates}, "
            f"target<= {args.fwsea_endpoint_max_target_candidates}, "
            f"coverage>= {args.fwsea_endpoint_min_deterministic_coverage:.2f}, "
            f"ambiguous<= {args.fwsea_endpoint_max_ambiguous_rows}, "
            f"max-targets/source<= {args.fwsea_endpoint_max_targets_per_source}, "
            f"candidate-rows>= {args.fwsea_endpoint_min_candidate_rows}"
        )
    lines.append(
        "- Aggregate transition basis usage: "
        f"{total_bridge_aware}/{total_transitions} bridge-aware ({format_pct(total_bridge_aware, total_transitions)}%), "
        f"{total_entry_window}/{total_transitions} entry-window ({format_pct(total_entry_window, total_transitions)}%)."
    )
    lines.append("")
    lines.append(
        "| Batch | Component key | Transitions | Bridge-aware | Entry-window | Entry-window rate % | "
        "Positive delta alerts | Zero-count transfer actions | Non-bridge zero assignments | Gates |"
    )
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for row in component_rows:
        lines.append(
            f"| {row['batch_name']} | `{row['component_key']}` | {row['transition_count']} | "
            f"{row['bridge_aware_count']} | {row['entry_window_count']} | {row['entry_window_rate_pct']} | "
            f"{row['positive_transition_alert_count']} | {row['zero_count_transfer_actions']} | "
            f"{row['non_bridge_zero_assignments']} | "
            f"{'PASS' if row['regression_gates_passed'] else 'FAIL'} |"
        )

    lines.append("")
    lines.append("## Aggregate Totals")
    lines.append("")
    lines.append(f"- Total transitions: {total_transitions}")
    lines.append(f"- Bridge-aware transitions: {total_bridge_aware}")
    lines.append(f"- Entry-window transitions: {total_entry_window}")
    lines.append(f"- Positive transition alerts (without mixed-batch rows): {total_positive_alerts}")
    lines.append(f"- Zero-count transfer actions: {total_zero_transfer_actions}")
    lines.append(f"- Non-bridge zero assignments: {total_non_bridge_zero_assignments}")
    lines.append("")
    lines.append("## Entry-window Reason Breakdown")
    lines.append("")
    lines.append("| Reason | Transition count |")
    lines.append("| --- | ---: |")
    for reason, count in sorted(aggregated_reason_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {reason} | {count} |")

    if args.run_fwsea_endpoint_gates:
        lines.append("")
        lines.append("## FWSEA Endpoint Gate Results")
        lines.append("")
        lines.append(
            "| Batch | Component key | Candidate rows | Deterministic rows | Coverage % | "
            "Max targets/source | Gate | Report |"
        )
        lines.append("| --- | --- | ---: | ---: | ---: | ---: | --- | --- |")
        for row in endpoint_component_rows:
            gate_text = (
                "PASS"
                if row.get("gate_passed") is True
                else ("FAIL" if row.get("gate_passed") is False else "INCONCLUSIVE")
            )
            lines.append(
                f"| {row['batch_name']} | `{row['component_key']}` | "
                f"{row.get('candidate_rows', 0)} | {row.get('deterministic_rows', 0)} | "
                f"{row.get('coverage_pct', '0.0')} | {row.get('max_targets_per_source', 0)} | "
                f"{gate_text} | `{row.get('report_name')}` |"
            )

    lines.append("")
    lines.append("## Overall Result")
    lines.append("")
    all_failed_components = set(failed_components)
    if args.fwsea_endpoint_enforce:
        all_failed_components.update(endpoint_failed_components)
    if all_failed_components:
        unique_failed = sorted(all_failed_components)
        lines.append(
            "- Regression check: FAIL "
            f"(components with failures: {', '.join(unique_failed)})"
        )
    else:
        lines.append("- Regression check: PASS")

    cohort_output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote cohort summary to {cohort_output}")

    return 1 if all_failed_components else 0


if __name__ == "__main__":
    raise SystemExit(main())
