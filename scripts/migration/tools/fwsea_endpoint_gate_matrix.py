#!/usr/bin/env python3
"""Run FWSEA endpoint pairing gate across a semantic cohort set and build a matrix."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ANALYSIS_DIR = (
    PROJECT_ROOT
    / "aquamind"
    / "docs"
    / "progress"
    / "migration"
    / "analysis_reports"
    / "2026-02-11"
)
DEFAULT_SEMANTIC_GLOB = "semantic_validation_*_fw20_parallel_post_fix.summary.json"
DEFAULT_REPORT_DIR_ROOT = PROJECT_ROOT / "scripts" / "migration" / "output" / "input_batch_migration"
DEFAULT_CSV_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"
GATE_SCRIPT = PROJECT_ROOT / "scripts" / "migration" / "tools" / "fwsea_endpoint_pairing_gate.py"


def normalize(value: str | None) -> str:
    return (value or "").strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run FWSEA endpoint pairing gates across a semantic cohort set"
    )
    parser.add_argument(
        "--analysis-dir",
        default=str(DEFAULT_ANALYSIS_DIR),
        help="Analysis directory containing semantic summary JSON files",
    )
    parser.add_argument(
        "--semantic-summary-glob",
        default=DEFAULT_SEMANTIC_GLOB,
        help="Glob pattern (under --analysis-dir) for semantic summary JSON files",
    )
    parser.add_argument(
        "--report-dir-root",
        default=str(DEFAULT_REPORT_DIR_ROOT),
        help="Root containing per-component population_members.csv report directories",
    )
    parser.add_argument(
        "--csv-dir",
        default=str(DEFAULT_CSV_DIR),
        help="FishTalk extract CSV directory",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_ANALYSIS_DIR / "fw20_endpoint_gate_matrix_2026-02-11"),
        help="Directory for per-cohort gate outputs + matrix JSON/TSV",
    )
    parser.add_argument(
        "--output-md",
        default=str(DEFAULT_ANALYSIS_DIR / "fw20_fwsea_endpoint_gate_matrix_2026-02-11.md"),
        help="Matrix markdown output path",
    )
    parser.add_argument(
        "--expected-direction",
        choices=("any", "sales_to_input", "input_to_sales"),
        default="sales_to_input",
    )
    parser.add_argument("--max-source-candidates", type=int, default=2)
    parser.add_argument("--max-target-candidates", type=int, default=1)
    parser.add_argument("--min-deterministic-coverage", type=float, default=0.9)
    parser.add_argument("--max-ambiguous-rows", type=int, default=0)
    parser.add_argument("--max-targets-per-source", type=int, default=1)
    parser.add_argument("--min-candidate-rows", type=int, default=10)
    parser.add_argument("--require-evidence", action="store_true", default=True)
    parser.add_argument("--require-marine-target", action="store_true", default=True)
    parser.add_argument("--min-marine-target-ratio", type=float, default=1.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    analysis_dir = Path(args.analysis_dir)
    report_dir_root = Path(args.report_dir_root)
    csv_dir = Path(args.csv_dir)
    output_dir = Path(args.output_dir)
    output_md = Path(args.output_md)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    semantic_summary_files = sorted(analysis_dir.glob(args.semantic_summary_glob))
    if not semantic_summary_files:
        print(f"No semantic summary files matched: {analysis_dir / args.semantic_summary_glob}")
        return 1

    key_to_report_dirs: dict[str, list[Path]] = {}
    for members_path in report_dir_root.glob("*/population_members.csv"):
        with members_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            first_row = next(reader, None)
        if not first_row:
            continue
        component_key = normalize(first_row.get("component_key")).upper()
        if not component_key:
            continue
        key_to_report_dirs.setdefault(component_key, []).append(members_path.parent)

    rows: list[dict] = []
    missing: list[dict] = []

    for semantic_summary in semantic_summary_files:
        payload = json.loads(semantic_summary.read_text(encoding="utf-8"))
        batch_name = ((payload.get("batch") or {}).get("batch_number") or semantic_summary.stem).strip()
        component_key = normalize(payload.get("component_key")).upper()
        report_dirs = key_to_report_dirs.get(component_key, [])
        if not report_dirs:
            missing.append(
                {
                    "batch_name": batch_name,
                    "component_key": component_key,
                    "reason": "missing_report_dir",
                    "semantic_summary": semantic_summary.name,
                }
            )
            continue

        report_dir = report_dirs[0]
        slug = "".join(ch if ch.isalnum() else "_" for ch in report_dir.name).strip("_")
        gate_md = output_dir / f"fwsea_endpoint_gate_{slug}.md"
        gate_json = output_dir / f"fwsea_endpoint_gate_{slug}.summary.json"

        cmd = [
            sys.executable,
            str(GATE_SCRIPT),
            "--csv-dir",
            str(csv_dir),
            "--report-dir",
            str(report_dir),
            "--component-key",
            component_key,
            "--expected-direction",
            args.expected_direction,
            "--max-source-candidates",
            str(args.max_source_candidates),
            "--max-target-candidates",
            str(args.max_target_candidates),
            "--min-deterministic-coverage",
            str(args.min_deterministic_coverage),
            "--max-ambiguous-rows",
            str(args.max_ambiguous_rows),
            "--max-targets-per-source",
            str(args.max_targets_per_source),
            "--min-candidate-rows",
            str(args.min_candidate_rows),
            "--min-marine-target-ratio",
            str(args.min_marine_target_ratio),
            "--semantic-summary-json",
            str(semantic_summary),
            "--output",
            str(gate_md),
            "--summary-json",
            str(gate_json),
        ]
        if args.require_evidence:
            cmd.append("--require-evidence")
        if args.require_marine_target:
            cmd.append("--require-marine-target")

        run = subprocess.run(cmd, capture_output=True, text=True)

        gate_payload = json.loads(gate_json.read_text(encoding="utf-8")) if gate_json.exists() else {}
        metrics = gate_payload.get("metrics") or {}
        gates = gate_payload.get("gates") or {}
        reason_counts = ((gate_payload.get("counts") or {}).get("reason_counts") or {})

        failed_gates: list[str] = []
        for gate_name in (
            "evidence",
            "uniqueness",
            "coverage",
            "stability",
            "marine_target",
            "incomplete_linkage_fallback",
        ):
            gate_data = gates.get(gate_name) or {}
            if gate_data.get("applicable") is False:
                continue
            if gate_data and gate_data.get("passed") is False:
                failed_gates.append(gate_name)

        rows.append(
            {
                "batch_name": batch_name,
                "component_key": component_key,
                "report_dir": report_dir.name,
                "semantic_summary": semantic_summary.name,
                "gate_summary": gate_json.name,
                "gate_report": gate_md.name,
                "returncode": run.returncode,
                "overall_passed": bool(gates.get("overall_passed")),
                "failed_gates": failed_gates,
                "touched_rows": int(metrics.get("touched_rows") or 0),
                "candidate_rows": int(metrics.get("candidate_rows") or 0),
                "deterministic_rows": int(metrics.get("deterministic_rows") or 0),
                "ambiguous_rows": int(metrics.get("ambiguous_rows") or 0),
                "deterministic_coverage": float(metrics.get("deterministic_coverage") or 0.0),
                "marine_target_ratio": float(metrics.get("marine_target_ratio") or 0.0),
                "max_targets_per_source": int(metrics.get("max_targets_per_source_observed") or 0),
                "incomplete_linkage_fallback_count": metrics.get("incomplete_linkage_fallback_count"),
                "reason_counts": reason_counts,
            }
        )

    rows.sort(key=lambda row: row["batch_name"])
    pass_count = sum(1 for row in rows if row["overall_passed"])
    fail_count = len(rows) - pass_count

    fail_gate_counts: Counter[str] = Counter()
    for row in rows:
        for gate_name in row.get("failed_gates") or []:
            fail_gate_counts[gate_name] += 1

    matrix_summary_json = output_dir / "fw20_endpoint_gate_matrix.summary.json"
    matrix_summary_json.write_text(
        json.dumps(
            {
                "rows": rows,
                "missing": missing,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "fail_gate_counts": dict(fail_gate_counts),
                "config": {
                    "expected_direction": args.expected_direction,
                    "max_source_candidates": args.max_source_candidates,
                    "max_target_candidates": args.max_target_candidates,
                    "min_deterministic_coverage": args.min_deterministic_coverage,
                    "max_ambiguous_rows": args.max_ambiguous_rows,
                    "max_targets_per_source": args.max_targets_per_source,
                    "min_candidate_rows": args.min_candidate_rows,
                    "require_evidence": args.require_evidence,
                    "require_marine_target": args.require_marine_target,
                    "min_marine_target_ratio": args.min_marine_target_ratio,
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    matrix_tsv = output_dir / "fw20_endpoint_gate_matrix.tsv"
    with matrix_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "batch_name",
                "component_key",
                "gate",
                "failed_gates",
                "candidate_rows",
                "deterministic_rows",
                "ambiguous_rows",
                "deterministic_coverage",
                "marine_target_ratio",
                "max_targets_per_source",
                "incomplete_linkage_fallback_count",
                "gate_summary",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row["batch_name"],
                    row["component_key"],
                    "PASS" if row["overall_passed"] else "FAIL",
                    ",".join(row.get("failed_gates") or []) or "-",
                    row["candidate_rows"],
                    row["deterministic_rows"],
                    row["ambiguous_rows"],
                    f"{row['deterministic_coverage']:.3f}",
                    f"{row['marine_target_ratio']:.3f}",
                    row["max_targets_per_source"],
                    row["incomplete_linkage_fallback_count"],
                    row["gate_summary"],
                ]
            )

    lines: list[str] = []
    lines.append("# FW20 FWSEA Endpoint Gate Matrix")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(
        f"- Cohort source: `{args.semantic_summary_glob}` under `{analysis_dir}` "
        f"({len(semantic_summary_files)} semantic summaries)."
    )
    lines.append("- Gate config:")
    lines.append(f"  - `expected-direction={args.expected_direction}`")
    lines.append(f"  - `max-source-candidates={args.max_source_candidates}`")
    lines.append(f"  - `max-target-candidates={args.max_target_candidates}`")
    lines.append(f"  - `min-deterministic-coverage={args.min_deterministic_coverage}`")
    lines.append(f"  - `max-ambiguous-rows={args.max_ambiguous_rows}`")
    lines.append(f"  - `max-targets-per-source={args.max_targets_per_source}`")
    lines.append(
        f"  - `min-candidate-rows={args.min_candidate_rows}` "
        f"(`require-evidence={args.require_evidence}`)"
    )
    lines.append(
        f"  - `require-marine-target={args.require_marine_target}` "
        f"(`min-marine-target-ratio={args.min_marine_target_ratio}`)"
    )
    lines.append("")
    lines.append("## Topline")
    lines.append("")
    lines.append(f"- Gate PASS: `{pass_count}/{len(rows)}`")
    lines.append(f"- Gate FAIL: `{fail_count}/{len(rows)}`")
    lines.append("")
    lines.append("## Gate-Failure Totals")
    lines.append("")
    for gate_name, count in sorted(fail_gate_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- `{gate_name}`: {count}")
    lines.append("")
    lines.append(
        "| batch | gate | failed gates | candidate rows | deterministic rows | ambiguous rows | "
        "coverage | marine ratio | max targets/source | incomplete-linkage fallback |"
    )
    lines.append(
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for row in rows:
        failed_gates = ", ".join(row.get("failed_gates") or []) or "-"
        incomplete = row["incomplete_linkage_fallback_count"]
        lines.append(
            f"| {row['batch_name']} | {'PASS' if row['overall_passed'] else 'FAIL'} | {failed_gates} | "
            f"{row['candidate_rows']} | {row['deterministic_rows']} | {row['ambiguous_rows']} | "
            f"{row['deterministic_coverage']:.3f} | {row['marine_target_ratio']:.3f} | "
            f"{row['max_targets_per_source']} | {incomplete if incomplete is not None else 'n/a'} |"
        )

    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- Matrix JSON: `{matrix_summary_json}`")
    lines.append(f"- Matrix TSV: `{matrix_tsv}`")
    lines.append(f"- Per-cohort gate files: `{output_dir}`")
    if missing:
        lines.append("")
        lines.append("## Missing Mappings")
        lines.append("")
        for row in missing:
            lines.append(
                f"- {row['batch_name']} (`{row['component_key']}`): "
                f"{row['reason']} ({row['semantic_summary']})"
            )

    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {output_md}")
    print(f"Wrote {matrix_summary_json}")
    print(f"Wrote {matrix_tsv}")
    print(f"Rows={len(rows)} PASS={pass_count} FAIL={fail_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

