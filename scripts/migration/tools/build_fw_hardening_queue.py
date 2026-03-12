#!/usr/bin/env python3
"""Build the FW hardening queue from current replay and repair evidence.

This tool answers one operational question:
which FW batches should be rerun for transfer replay, which need creation-side
manual reconstruction first, and which can be treated as low-priority/no-action
for the current hardening phase.

The transfer-rerun classification is derived from code, not handoffs:
- load the component member report for a batch
- load raw FishTalk SubTransfers for those populations
- compare the old raw `internal-only` edge set to the patched root-source
  expanded `internal-only` edge set

If the expanded set contains additional in-scope edges, that batch was exposed
to the sibling-leg loss bug and belongs in the transfer rerun queue.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from scripts.migration.tools.pilot_migrate_component_transfers import (
    expand_subtransfer_rows_for_source_scope,
    load_members_from_report,
    load_subtransfers_from_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCOPE_FILE = (
    PROJECT_ROOT
    / "scripts"
    / "migration"
    / "output"
    / "input_stitching"
    / "scope_fw78_fwonly_u30_mapped_faroe_fw22_fw13_batch_keys.csv"
)
DEFAULT_EXTRACT_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"
DEFAULT_BATCH_REPORT_DIR = (
    PROJECT_ROOT / "scripts" / "migration" / "output" / "input_batch_migration"
)
DEFAULT_CREATION_REPAIR_RUN = (
    PROJECT_ROOT
    / "aquamind"
    / "docs"
    / "progress"
    / "migration"
    / "analysis_reports"
    / "2026-03-06"
    / "creation_assignment_repair_run_2026-03-06.json"
)
DEFAULT_CREATION_REPAIR_GUARDED = (
    PROJECT_ROOT
    / "aquamind"
    / "docs"
    / "progress"
    / "migration"
    / "analysis_reports"
    / "2026-03-06"
    / "creation_assignment_repair_guarded_dryrun_2026-03-06.json"
)


MANUAL_RECONSTRUCTION_BATCHES = [
    {
        "batch_id": 1116,
        "batch_number": "24Q1 LHS ex-LC",
        "batch_key": "24Q1 LHS ex-LC|13|2023",
        "report_dir_name": "24Q1_LHS_ex-LC_13_2023",
        "reason": (
            "Creation actions land on Parr assignments, not Egg&Alevin; "
            "outside the narrow zeroed-egg repair class."
        ),
    },
    {
        "batch_id": 1133,
        "batch_number": "Stofnfiskur feb 2025 - Vár 2025",
        "batch_key": "Stofnfiskur feb 2025|1|2025",
        "report_dir_name": "Stofnfiskur_feb_2025_1_2025",
        "reason": (
            "Guarded creation repair still leaves the batch materially below its "
            "creation total; needs smarter FW reconstruction."
        ),
    },
    {
        "batch_id": 1329,
        "batch_number": "Benchmark Gen. Mars 2025 - Vár 2025",
        "batch_key": "Benchmark Gen. Mars 2025|1|2025",
        "report_dir_name": "Benchmark_Gen._Mars_2025_1_2025",
        "reason": (
            "Guarded creation repair still leaves the batch materially below its "
            "creation total; needs smarter FW reconstruction."
        ),
    },
    {
        "batch_id": 1330,
        "batch_number": "Gjógv/Fiskaaling mars 2023 - Heyst 2023",
        "batch_key": "Gjógv/Fiskaaling mars 2023|5|2023",
        "report_dir_name": "Gjógv_Fiskaaling_mars_2023_5_2023",
        "reason": (
            "Creation actions land on Parr assignments, not Egg&Alevin; "
            "outside the narrow zeroed-egg repair class."
        ),
    },
]

TRANSFER_RERUN_CANARIES = [
    {
        "batch_id": 1344,
        "batch_number": "Stofnfiskur Des 23 - Vár 2024",
        "batch_key": "Stofnfiskur Des 23|6|2023",
        "report_dir_name": "Stofnfiskur_Des_23_6_2023",
        "reason": (
            "Manually validated S03 cohort with missing split legs "
            "(801/802/806 -> 901/903/904) under the old replay behavior."
        ),
    },
    {
        "batch_id": 1348,
        "batch_number": "Stofnfiskur S-21 feb24 - Vár 2024",
        "batch_key": "Stofnfiskur S-21 feb24|1|2024",
        "report_dir_name": "Stofnfiskur_S-21_feb24_1_2024",
        "reason": (
            "Creation-repaired canary outside the mapped scope; transfer replay "
            "is still exposed to the old split-loss bug."
        ),
    },
    {
        "batch_id": 1349,
        "batch_number": "Stofnfiskur S-21 juni24 - Summar 2024",
        "batch_key": "Stofnfiskur S-21 juni24|2|2024",
        "report_dir_name": "Stofnfiskur_S-21_juni24_2_2024",
        "reason": (
            "Creation-repaired canary outside the mapped scope; transfer replay "
            "is still exposed to the old split-loss bug."
        ),
    },
    {
        "batch_id": 1352,
        "batch_number": "Stofnfiskur desembur 2023 - Vár 2024",
        "batch_key": "Stofnfiskur desembur 2023|4|2023",
        "report_dir_name": "Stofnfiskur_desembur_2023_4_2023",
        "reason": (
            "Creation-repaired S24 canary; egg-stage counts were fixed, but transfer "
            "replay still predates the root-source split-leg patch."
        ),
    },
]

NO_IMMEDIATE_ACTION_BATCHES = [
    {
        "batch_id": 1122,
        "batch_number": "Bakkafrost feb 2024 - Vár 2024",
        "batch_key": "Bakkafrost feb 2024|1|2024",
        "report_dir_name": "Bakkafrost_feb_2024_1_2024",
        "reason": (
            "Creation repair already applied and no internal-only split-loss "
            "exposure was detected in the transfer replay."
        ),
    }
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope-file", type=Path, default=DEFAULT_SCOPE_FILE)
    parser.add_argument("--extract-dir", type=Path, default=DEFAULT_EXTRACT_DIR)
    parser.add_argument("--batch-report-dir", type=Path, default=DEFAULT_BATCH_REPORT_DIR)
    parser.add_argument("--creation-repair-run", type=Path, default=DEFAULT_CREATION_REPAIR_RUN)
    parser.add_argument(
        "--creation-repair-guarded",
        type=Path,
        default=DEFAULT_CREATION_REPAIR_GUARDED,
    )
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    return parser.parse_args()


def sanitize_batch_key(batch_key: str) -> str:
    return batch_key.replace("|", "_").replace(" ", "_").replace("/", "_")


def load_json_map(path: Path) -> dict[int, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {int(row["batch_id"]): row for row in payload.get("batches", [])}


def analyze_transfer_exposure(report_dir: Path, extract_dir: Path) -> dict[str, Any]:
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
    missing_edges = sorted(new_internal - old_internal)
    return {
        "report_dir": str(report_dir),
        "member_count": len(population_ids),
        "raw_subtransfer_rows": len(raw_rows),
        "old_internal_edge_count": len(old_internal),
        "new_internal_edge_count": len(new_internal),
        "missing_edge_count": len(missing_edges),
        "affected": bool(missing_edges),
        "sample_missing_edges": [
            {
                "operation_id": op_id,
                "source_pop": source_pop,
                "dest_pop": dest_pop,
            }
            for op_id, source_pop, dest_pop in missing_edges[:10]
        ],
    }


def build_scope_transfer_queue(
    scope_file: Path,
    batch_report_dir: Path,
    extract_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    affected: list[dict[str, Any]] = []
    unaffected: list[dict[str, Any]] = []
    with scope_file.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            batch_key = (row.get("batch_key") or "").strip()
            if not batch_key:
                continue
            report_dir = batch_report_dir / sanitize_batch_key(batch_key)
            exposure = analyze_transfer_exposure(report_dir, extract_dir)
            item = {
                "batch_key": batch_key,
                "report_dir": exposure["report_dir"],
                "member_count": exposure["member_count"],
                "raw_subtransfer_rows": exposure["raw_subtransfer_rows"],
                "old_internal_edge_count": exposure["old_internal_edge_count"],
                "new_internal_edge_count": exposure["new_internal_edge_count"],
                "missing_edge_count": exposure["missing_edge_count"],
                "sample_missing_edges": exposure["sample_missing_edges"],
                "reason": (
                    "Mapped FW scope batch replayed before the root-source split-leg patch; "
                    "rerun transfer workflows with the patched SubTransfers expansion."
                ),
            }
            if exposure["affected"]:
                affected.append(item)
            else:
                unaffected.append(item)
    affected.sort(key=lambda item: (-item["missing_edge_count"], item["batch_key"]))
    unaffected.sort(key=lambda item: item["batch_key"])
    return affected, unaffected


def enrich_named_batches(
    rows: list[dict[str, Any]],
    *,
    batch_report_dir: Path,
    extract_dir: Path,
    creation_repair_run: dict[int, dict[str, Any]],
    creation_repair_guarded: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in rows:
        report_dir = batch_report_dir / row["report_dir_name"]
        exposure = analyze_transfer_exposure(report_dir, extract_dir)
        entry = {
            **row,
            **exposure,
        }
        batch_id = int(row["batch_id"])
        if batch_id in creation_repair_run:
            entry["creation_repair_run"] = creation_repair_run[batch_id]
        if batch_id in creation_repair_guarded:
            entry["creation_repair_guarded_dryrun"] = creation_repair_guarded[batch_id]
        enriched.append(entry)
    return enriched


def merge_no_immediate_action_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.get("batch_key") or row.get("batch_number") or row.get("report_dir")
        if key not in merged:
            merged[key] = row
            continue
        prior_reason = merged[key].get("reason") or ""
        next_reason = row.get("reason") or ""
        if next_reason and next_reason not in prior_reason:
            merged[key]["reason"] = f"{prior_reason} {next_reason}".strip()
    return sorted(
        merged.values(),
        key=lambda item: item.get("batch_key") or item.get("batch_number") or "",
    )


def render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    summary = payload["summary"]
    lines.append("# FW Hardening Queue")
    lines.append("")
    lines.append(f"Date: {summary['as_of_date']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Scope batches analyzed: `{summary['scope_batches_total']}`")
    lines.append(f"- Scope batches exposed to the old transfer split-loss bug: `{summary['scope_transfer_rerun_required']}`")
    lines.append(f"- Additional transfer-rerun canaries outside the mapped scope: `{summary['additional_transfer_rerun_canaries']}`")
    lines.append(f"- Manual reconstruction batches: `{summary['manual_reconstruction_required']}`")
    lines.append(f"- No-immediate-action batches: `{summary['no_immediate_action']}`")
    lines.append("")
    lines.append("## Wave 1: Transfer Rerun Canaries")
    lines.append("")
    lines.append("| Batch ID | Batch Number | Batch Key | Missing Split Legs | Reason |")
    lines.append("|---|---|---|---:|---|")
    for row in payload["transfer_rerun_canaries"]:
        lines.append(
            f"| `{row['batch_id']}` | `{row['batch_number']}` | `{row['batch_key']}` | "
            f"`{row['missing_edge_count']}` | {row['reason']} |"
        )
    lines.append("")
    lines.append("## Wave 2: Mapped FW Scope Transfer Reruns")
    lines.append("")
    lines.append("| Batch Key | Missing Split Legs | Member Count | Raw SubTransfers |")
    lines.append("|---|---:|---:|---:|")
    for row in payload["scope_transfer_rerun_queue"]:
        lines.append(
            f"| `{row['batch_key']}` | `{row['missing_edge_count']}` | "
            f"`{row['member_count']}` | `{row['raw_subtransfer_rows']}` |"
        )
    lines.append("")
    lines.append("## Manual Reconstruction First")
    lines.append("")
    lines.append("| Batch ID | Batch Number | Batch Key | Missing Split Legs | Creation Total Gap Signal |")
    lines.append("|---|---|---|---:|---|")
    for row in payload["manual_reconstruction_queue"]:
        guarded = row.get("creation_repair_guarded_dryrun")
        if guarded:
            gap_text = (
                f"guarded dryrun `{guarded['egg_total_before']}` -> "
                f"`{guarded['egg_total_after']}` vs creation `{guarded['creation_total']}`"
            )
        else:
            run = row.get("creation_repair_run")
            if run:
                gap_text = (
                    f"apply run `{run['egg_total_before']}` -> "
                    f"`{run['egg_total_after']}` vs creation `{run['creation_total']}`"
                )
            else:
                gap_text = "n/a"
        lines.append(
            f"| `{row['batch_id']}` | `{row['batch_number']}` | `{row['batch_key']}` | "
            f"`{row['missing_edge_count']}` | {gap_text} |"
        )
    lines.append("")
    lines.append("## No Immediate Action")
    lines.append("")
    lines.append("| Batch | Reason |")
    lines.append("|---|---|")
    for row in payload["no_immediate_action"]:
        batch_label = row.get("batch_key") or row.get("batch_number")
        lines.append(f"| `{batch_label}` | {row['reason']} |")
    lines.append("")
    lines.append("## Recommended Execution Order")
    lines.append("")
    lines.append("- Rerun transfer workflows for the Wave 1 canaries first.")
    lines.append("- If the Wave 1 canaries validate cleanly in AquaMind, rerun the 17 affected mapped-scope FW batches.")
    lines.append("- Do not bulk-rerun `1116`, `1133`, `1329`, or `1330` before their FW reconstruction strategy is decided.")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)

    creation_repair_run = load_json_map(args.creation_repair_run)
    creation_repair_guarded = load_json_map(args.creation_repair_guarded)
    scope_transfer_rerun_queue, scope_unaffected = build_scope_transfer_queue(
        args.scope_file,
        args.batch_report_dir,
        args.extract_dir,
    )
    transfer_rerun_canaries = enrich_named_batches(
        TRANSFER_RERUN_CANARIES,
        batch_report_dir=args.batch_report_dir,
        extract_dir=args.extract_dir,
        creation_repair_run=creation_repair_run,
        creation_repair_guarded=creation_repair_guarded,
    )
    manual_reconstruction_queue = enrich_named_batches(
        MANUAL_RECONSTRUCTION_BATCHES,
        batch_report_dir=args.batch_report_dir,
        extract_dir=args.extract_dir,
        creation_repair_run=creation_repair_run,
        creation_repair_guarded=creation_repair_guarded,
    )
    no_immediate_action = enrich_named_batches(
        NO_IMMEDIATE_ACTION_BATCHES,
        batch_report_dir=args.batch_report_dir,
        extract_dir=args.extract_dir,
        creation_repair_run=creation_repair_run,
        creation_repair_guarded=creation_repair_guarded,
    )
    for row in scope_unaffected:
        no_immediate_action.append(
            {
                **row,
                "reason": (
                    "Mapped-scope batch analyzed against the patched root-source expansion and "
                    "did not show additional internal split legs."
                ),
            }
        )
    no_immediate_action = merge_no_immediate_action_rows(no_immediate_action)

    payload = {
        "summary": {
            "as_of_date": "2026-03-06",
            "scope_batches_total": len(scope_transfer_rerun_queue) + len(scope_unaffected),
            "scope_transfer_rerun_required": len(scope_transfer_rerun_queue),
            "additional_transfer_rerun_canaries": len(transfer_rerun_canaries),
            "manual_reconstruction_required": len(manual_reconstruction_queue),
            "no_immediate_action": len(no_immediate_action),
        },
        "scope_transfer_rerun_queue": scope_transfer_rerun_queue,
        "transfer_rerun_canaries": transfer_rerun_canaries,
        "manual_reconstruction_queue": manual_reconstruction_queue,
        "no_immediate_action": no_immediate_action,
    }
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
