#!/usr/bin/env python3
"""Deterministic endpoint-pairing acceptance gate for FWSEA linkage evidence.

Tooling-only diagnostics for migration policy readiness:
- no runtime coupling,
- no policy mutation.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CSV_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"


def normalize(value: str | None) -> str:
    return (value or "").strip()


def load_csv_rows(path: Path, *, required: bool = True) -> list[dict[str, str]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required CSV file: {path}")
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_component_scope(
    *,
    report_dir: Path,
    component_key: str | None,
    component_id: str | None,
) -> dict[str, object]:
    rows = load_csv_rows(report_dir / "population_members.csv", required=True)

    wanted_key = normalize(component_key)
    wanted_id = normalize(component_id)
    if not wanted_key and not wanted_id:
        keys = {normalize(row.get("component_key")) for row in rows if normalize(row.get("component_key"))}
        ids = {normalize(row.get("component_id")) for row in rows if normalize(row.get("component_id"))}
        if len(keys) == 1:
            wanted_key = next(iter(keys))
        elif len(ids) == 1:
            wanted_id = next(iter(ids))
        else:
            raise ValueError("Provide --component-key or --component-id when report contains multiple components.")

    population_ids: set[str] = set()
    resolved_key = wanted_key
    resolved_id = wanted_id
    for row in rows:
        row_key = normalize(row.get("component_key"))
        row_id = normalize(row.get("component_id"))
        if wanted_key and row_key != wanted_key:
            continue
        if wanted_id and row_id != wanted_id:
            continue
        pop_id = normalize(row.get("population_id"))
        if pop_id:
            population_ids.add(pop_id)
        if not resolved_key and row_key:
            resolved_key = row_key
        if not resolved_id and row_id:
            resolved_id = row_id

    if not population_ids:
        raise ValueError(
            f"No component populations found for component_key={wanted_key!r} component_id={wanted_id!r}."
        )

    return {
        "component_key": resolved_key or "",
        "component_id": resolved_id or "",
        "population_ids": population_ids,
    }


def classify_prod_stage(value: str) -> str:
    upper = normalize(value).upper()
    if "MARINE" in upper:
        return "marine"
    if "HATCHERY" in upper or "FRESH" in upper or "FW" in upper:
        return "fw"
    return "unknown"


def load_incomplete_linkage_fallback_count(summary_path: Path | None) -> int | None:
    if summary_path is None:
        return None
    if not summary_path.exists():
        return None
    payload = json.loads(summary_path.read_text(encoding="utf-8"))

    stage_sanity = payload.get("stage_sanity") or {}
    reason_counts = stage_sanity.get("transition_entry_window_reason_counts") or {}
    reason_count = 0
    for key in ("incomplete_linkage", "incomplete linkage", "incomplete-linkage"):
        try:
            reason_count = max(reason_count, int(reason_counts.get(key) or 0))
        except Exception:
            continue

    regression_gates = payload.get("regression_gates") or {}
    excluded_alert_count = int(regression_gates.get("transition_alert_excluded_incomplete_linkage_count") or 0)
    return max(reason_count, excluded_alert_count)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Endpoint-pairing acceptance gate for deterministic FWSEA linkage"
    )
    parser.add_argument(
        "--csv-dir",
        default=str(DEFAULT_CSV_DIR),
        help="CSV extract directory (default: scripts/migration/data/extract)",
    )
    parser.add_argument(
        "--report-dir",
        required=True,
        help="Component report directory containing population_members.csv",
    )
    parser.add_argument("--component-key", help="Optional component_key filter")
    parser.add_argument("--component-id", help="Optional component_id filter")
    parser.add_argument(
        "--expected-direction",
        choices=("any", "sales_to_input", "input_to_sales"),
        default="sales_to_input",
        help="Expected component movement direction for deterministic rows",
    )
    parser.add_argument("--max-source-candidates", type=int, default=2)
    parser.add_argument("--max-target-candidates", type=int, default=1)
    parser.add_argument("--min-deterministic-coverage", type=float, default=0.9)
    parser.add_argument("--max-ambiguous-rows", type=int, default=0)
    parser.add_argument("--max-targets-per-source", type=int, default=1)
    parser.add_argument("--min-candidate-rows", type=int, default=10)
    parser.add_argument("--require-evidence", action="store_true")
    parser.add_argument("--require-marine-target", action="store_true")
    parser.add_argument("--min-marine-target-ratio", type=float, default=1.0)
    parser.add_argument(
        "--semantic-summary-json",
        help="Optional semantic summary JSON for incomplete-linkage fallback gating",
    )
    parser.add_argument(
        "--max-incomplete-linkage-fallback",
        type=int,
        help="Optional absolute threshold for incomplete-linkage fallback count",
    )
    parser.add_argument(
        "--baseline-incomplete-linkage-fallback",
        type=int,
        help="Optional baseline; current fallback must be <= baseline",
    )
    parser.add_argument("--output", required=True, help="Output markdown path")
    parser.add_argument("--summary-json", help="Optional summary JSON output path")
    parser.add_argument("--max-example-rows", type=int, default=25)
    parser.add_argument("--check-gates", action="store_true", help="Return non-zero if gates fail")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_dir = Path(args.csv_dir)
    report_dir = Path(args.report_dir)

    scope = load_component_scope(
        report_dir=report_dir,
        component_key=args.component_key,
        component_id=args.component_id,
    )
    component_population_ids = set(scope["population_ids"])

    internal_rows = load_csv_rows(csv_dir / "internal_delivery.csv", required=True)
    action_rows = load_csv_rows(csv_dir / "internal_delivery_actions.csv", required=True)
    populations_rows = load_csv_rows(csv_dir / "populations.csv", required=True)
    grouped_rows = load_csv_rows(csv_dir / "grouped_organisation.csv", required=True)

    op_to_population_ids: defaultdict[str, set[str]] = defaultdict(set)
    for row in action_rows:
        op_id = normalize(row.get("OperationID"))
        pop_id = normalize(row.get("PopulationID"))
        if op_id and pop_id:
            op_to_population_ids[op_id].add(pop_id)

    population_to_container: dict[str, str] = {}
    for row in populations_rows:
        pop_id = normalize(row.get("PopulationID"))
        container_id = normalize(row.get("ContainerID"))
        if pop_id:
            population_to_container[pop_id] = container_id

    container_to_prod_stage: dict[str, str] = {}
    for row in grouped_rows:
        container_id = normalize(row.get("ContainerID"))
        if container_id and container_id not in container_to_prod_stage:
            container_to_prod_stage[container_id] = normalize(row.get("ProdStage"))

    def population_stage_class(population_id: str) -> str:
        container_id = population_to_container.get(population_id, "")
        return classify_prod_stage(container_to_prod_stage.get(container_id, ""))

    row_outcomes: list[dict[str, object]] = []
    reason_counts: Counter[str] = Counter()
    direction_counts: Counter[str] = Counter()
    pair_stage_counts: Counter[str] = Counter()
    source_to_targets: defaultdict[str, set[str]] = defaultdict(set)

    touched_rows = 0
    both_side_touch_rows = 0
    candidate_rows = 0
    deterministic_rows = 0
    marine_target_deterministic_rows = 0

    for row in internal_rows:
        sales_op = normalize(row.get("SalesOperationID"))
        input_op = normalize(row.get("InputOperationID"))
        sales_pop_ids = op_to_population_ids.get(sales_op, set())
        input_pop_ids = op_to_population_ids.get(input_op, set()) if input_op else set()

        sales_component_ids = sales_pop_ids & component_population_ids
        input_component_ids = input_pop_ids & component_population_ids
        if not sales_component_ids and not input_component_ids:
            continue
        touched_rows += 1

        outcome: dict[str, object] = {
            "sales_operation_id": sales_op,
            "input_operation_id": input_op,
            "sales_component_population_count": len(sales_component_ids),
            "input_component_population_count": len(input_component_ids),
            "sales_operation_population_count": len(sales_pop_ids),
            "input_operation_population_count": len(input_pop_ids),
            "direction": "none",
            "source_component_population_count": 0,
            "target_population_count": 0,
            "deterministic": False,
            "reason": "",
        }

        if sales_component_ids and input_component_ids:
            both_side_touch_rows += 1
            outcome["direction"] = "both_side_touch"
            outcome["reason"] = "both_side_touch"
            row_outcomes.append(outcome)
            reason_counts["both_side_touch"] += 1
            direction_counts["both_side_touch"] += 1
            continue

        if sales_component_ids:
            direction = "sales_to_input"
            source_ids = set(sales_component_ids)
            target_ids = set(input_pop_ids) - component_population_ids
        else:
            direction = "input_to_sales"
            source_ids = set(input_component_ids)
            target_ids = set(sales_pop_ids) - component_population_ids

        direction_counts[direction] += 1
        outcome["direction"] = direction
        outcome["source_component_population_count"] = len(source_ids)
        outcome["target_population_count"] = len(target_ids)
        if not target_ids:
            outcome["reason"] = "no_counterpart_populations"
            row_outcomes.append(outcome)
            reason_counts["no_counterpart_populations"] += 1
            continue

        candidate_rows += 1

        source_stage_classes = Counter(population_stage_class(pop_id) for pop_id in source_ids)
        target_stage_classes = Counter(population_stage_class(pop_id) for pop_id in target_ids)
        dominant_source_stage = max(source_stage_classes, key=source_stage_classes.get) if source_stage_classes else "unknown"
        dominant_target_stage = max(target_stage_classes, key=target_stage_classes.get) if target_stage_classes else "unknown"
        pair_stage_counts[f"{dominant_source_stage}->{dominant_target_stage}"] += 1
        outcome["source_stage_class_counts"] = dict(source_stage_classes)
        outcome["target_stage_class_counts"] = dict(target_stage_classes)

        if args.expected_direction != "any" and direction != args.expected_direction:
            outcome["reason"] = "direction_mismatch"
            row_outcomes.append(outcome)
            reason_counts["direction_mismatch"] += 1
            continue

        if not (1 <= len(source_ids) <= args.max_source_candidates):
            outcome["reason"] = "source_candidate_count_out_of_bounds"
            row_outcomes.append(outcome)
            reason_counts["source_candidate_count_out_of_bounds"] += 1
            continue

        if not (1 <= len(target_ids) <= args.max_target_candidates):
            outcome["reason"] = "target_candidate_count_out_of_bounds"
            row_outcomes.append(outcome)
            reason_counts["target_candidate_count_out_of_bounds"] += 1
            continue

        deterministic_rows += 1
        outcome["deterministic"] = True
        outcome["reason"] = "deterministic"

        target_all_marine = bool(target_ids) and all(population_stage_class(pop_id) == "marine" for pop_id in target_ids)
        if target_all_marine:
            marine_target_deterministic_rows += 1
        outcome["target_all_marine"] = target_all_marine

        for src_id in source_ids:
            source_to_targets[src_id].update(target_ids)

        row_outcomes.append(outcome)
        reason_counts["deterministic"] += 1

    ambiguous_rows = candidate_rows - deterministic_rows
    deterministic_coverage = (deterministic_rows / candidate_rows) if candidate_rows > 0 else 0.0
    marine_target_ratio = (
        marine_target_deterministic_rows / deterministic_rows if deterministic_rows > 0 else 0.0
    )

    sources_with_multiple_targets = sum(1 for targets in source_to_targets.values() if len(targets) > 1)
    max_targets_per_source_observed = max((len(targets) for targets in source_to_targets.values()), default=0)

    incomplete_fallback_count = load_incomplete_linkage_fallback_count(
        Path(args.semantic_summary_json) if args.semantic_summary_json else None
    )

    evidence_gate_applicable = touched_rows > 0 or args.require_evidence
    evidence_gate_passed = (
        (candidate_rows >= args.min_candidate_rows) if evidence_gate_applicable else True
    )

    uniqueness_gate_passed = ambiguous_rows <= args.max_ambiguous_rows
    coverage_gate_passed = deterministic_coverage >= args.min_deterministic_coverage
    stability_gate_passed = max_targets_per_source_observed <= args.max_targets_per_source

    marine_gate_applicable = args.require_marine_target
    marine_gate_passed = (
        marine_target_ratio >= args.min_marine_target_ratio if marine_gate_applicable else True
    )

    incomplete_gate_applicable = (
        incomplete_fallback_count is not None
        and (
            args.max_incomplete_linkage_fallback is not None
            or args.baseline_incomplete_linkage_fallback is not None
        )
    )
    incomplete_threshold = None
    if incomplete_gate_applicable:
        if args.baseline_incomplete_linkage_fallback is not None:
            incomplete_threshold = args.baseline_incomplete_linkage_fallback
        else:
            incomplete_threshold = args.max_incomplete_linkage_fallback
    incomplete_gate_passed = (
        incomplete_fallback_count <= int(incomplete_threshold)
        if incomplete_gate_applicable and incomplete_fallback_count is not None and incomplete_threshold is not None
        else True
    )

    overall_passed = all(
        [
            evidence_gate_passed,
            uniqueness_gate_passed,
            coverage_gate_passed,
            stability_gate_passed,
            marine_gate_passed,
            incomplete_gate_passed,
        ]
    )

    summary: dict[str, object] = {
        "component_key": scope["component_key"],
        "component_id": scope["component_id"],
        "component_population_count": len(component_population_ids),
        "expected_direction": args.expected_direction,
        "metrics": {
            "touched_rows": touched_rows,
            "both_side_touch_rows": both_side_touch_rows,
            "candidate_rows": candidate_rows,
            "deterministic_rows": deterministic_rows,
            "ambiguous_rows": ambiguous_rows,
            "deterministic_coverage": deterministic_coverage,
            "marine_target_deterministic_rows": marine_target_deterministic_rows,
            "marine_target_ratio": marine_target_ratio,
            "sources_with_multiple_targets": sources_with_multiple_targets,
            "max_targets_per_source_observed": max_targets_per_source_observed,
            "incomplete_linkage_fallback_count": incomplete_fallback_count,
        },
        "counts": {
            "direction_counts": dict(sorted(direction_counts.items())),
            "reason_counts": dict(sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))),
            "pair_stage_counts": dict(sorted(pair_stage_counts.items(), key=lambda item: (-item[1], item[0]))),
        },
        "gates": {
            "evidence": {
                "applicable": evidence_gate_applicable,
                "passed": evidence_gate_passed,
                "min_candidate_rows": args.min_candidate_rows,
                "actual_candidate_rows": candidate_rows,
            },
            "uniqueness": {
                "passed": uniqueness_gate_passed,
                "max_ambiguous_rows": args.max_ambiguous_rows,
                "actual_ambiguous_rows": ambiguous_rows,
            },
            "coverage": {
                "passed": coverage_gate_passed,
                "min_deterministic_coverage": args.min_deterministic_coverage,
                "actual_deterministic_coverage": deterministic_coverage,
            },
            "stability": {
                "passed": stability_gate_passed,
                "max_targets_per_source": args.max_targets_per_source,
                "actual_max_targets_per_source": max_targets_per_source_observed,
                "sources_with_multiple_targets": sources_with_multiple_targets,
            },
            "marine_target": {
                "applicable": marine_gate_applicable,
                "passed": marine_gate_passed,
                "min_marine_target_ratio": args.min_marine_target_ratio,
                "actual_marine_target_ratio": marine_target_ratio,
            },
            "incomplete_linkage_fallback": {
                "applicable": incomplete_gate_applicable,
                "passed": incomplete_gate_passed,
                "threshold": incomplete_threshold,
                "actual": incomplete_fallback_count,
                "semantic_summary_json": args.semantic_summary_json or "",
            },
            "overall_passed": overall_passed,
        },
        "examples": row_outcomes[: max(args.max_example_rows, 0)],
    }

    lines: list[str] = []
    lines.append("# FWSEA Endpoint Pairing Acceptance Gate")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(f"- Component key: `{scope['component_key']}`")
    lines.append(f"- Component id: `{scope['component_id'] or 'n/a'}`")
    lines.append(f"- Component population count: {len(component_population_ids)}")
    lines.append(f"- CSV directory: `{csv_dir}`")
    lines.append(f"- Expected direction: `{args.expected_direction}`")
    lines.append("")
    lines.append("## Endpoint Metrics")
    lines.append("")
    lines.append(f"- InternalDelivery rows touching component populations: {touched_rows}")
    lines.append(f"- Rows with component populations on both sides: {both_side_touch_rows}")
    lines.append(f"- Candidate rows (single-side touch with counterpart populations): {candidate_rows}")
    lines.append(f"- Deterministic rows: {deterministic_rows}")
    lines.append(f"- Ambiguous rows: {ambiguous_rows}")
    lines.append(f"- Deterministic coverage: {deterministic_coverage:.3f}")
    lines.append(f"- Marine-target deterministic rows: {marine_target_deterministic_rows}")
    lines.append(f"- Marine-target deterministic ratio: {marine_target_ratio:.3f}")
    lines.append(f"- Max targets per source endpoint: {max_targets_per_source_observed}")
    lines.append(f"- Sources with multiple targets: {sources_with_multiple_targets}")
    if incomplete_fallback_count is not None:
        lines.append(f"- Incomplete-linkage fallback count (semantic summary): {incomplete_fallback_count}")
    lines.append("")
    lines.append("## Gate Results")
    lines.append("")
    lines.append("| Gate | Passed | Details |")
    lines.append("| --- | --- | --- |")
    lines.append(
        f"| evidence | {'YES' if evidence_gate_passed else 'NO'} | candidate_rows={candidate_rows}, min={args.min_candidate_rows} |"
    )
    lines.append(
        f"| uniqueness | {'YES' if uniqueness_gate_passed else 'NO'} | ambiguous_rows={ambiguous_rows}, max={args.max_ambiguous_rows} |"
    )
    lines.append(
        f"| coverage | {'YES' if coverage_gate_passed else 'NO'} | coverage={deterministic_coverage:.3f}, min={args.min_deterministic_coverage:.3f} |"
    )
    lines.append(
        f"| stability | {'YES' if stability_gate_passed else 'NO'} | max_targets_per_source={max_targets_per_source_observed}, max={args.max_targets_per_source} |"
    )
    if marine_gate_applicable:
        lines.append(
            f"| marine_target | {'YES' if marine_gate_passed else 'NO'} | ratio={marine_target_ratio:.3f}, min={args.min_marine_target_ratio:.3f} |"
        )
    if incomplete_gate_applicable:
        lines.append(
            f"| incomplete_linkage_fallback | {'YES' if incomplete_gate_passed else 'NO'} | actual={incomplete_fallback_count}, threshold={incomplete_threshold} |"
        )
    lines.append(f"| overall | {'PASS' if overall_passed else 'FAIL'} | endpoint pairing acceptance gate |")
    lines.append("")
    lines.append("## Direction Counts")
    lines.append("")
    for key, value in sorted(direction_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Reason Counts")
    lines.append("")
    for key, value in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Dominant Stage Pair Counts")
    lines.append("")
    for key, value in sorted(pair_stage_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {key}: {value}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote report to {output_path}")

    if args.summary_json:
        summary_path = Path(args.summary_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Wrote summary JSON to {summary_path}")

    return 1 if (args.check_gates and not overall_passed) else 0


if __name__ == "__main__":
    raise SystemExit(main())

