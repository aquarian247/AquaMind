#!/usr/bin/env python3
"""Run a transfer-only rerun queue with per-batch logs and a summary."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EXTRACT_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"
TRANSFER_SCRIPT = PROJECT_ROOT / "scripts" / "migration" / "tools" / "pilot_migrate_component_transfers.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--extract-dir", type=Path, default=DEFAULT_EXTRACT_DIR)
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--limit", type=int, help="Optional max rows to run")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue after failures instead of stopping at the first failure.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Write the plan without executing.")
    return parser.parse_args()


def sanitize_batch_key(batch_key: str) -> str:
    return batch_key.replace("|", "_").replace(" ", "_").replace("/", "_")


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = args.output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    with args.queue_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if args.limit is not None:
        rows = rows[: args.limit]

    started_at = datetime.now(timezone.utc)
    results: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    for index, row in enumerate(rows, start=1):
        batch_key = (row.get("batch_key") or "").strip()
        component_key = (row.get("component_key") or "").strip()
        report_dir = (row.get("report_dir") or "").strip()
        if not batch_key or not component_key or not report_dir:
            raise SystemExit(f"Queue row {index} is missing batch_key/component_key/report_dir.")

        log_path = logs_dir / f"{index:03d}_{sanitize_batch_key(batch_key)}.log"
        command = [
            args.python_executable,
            str(TRANSFER_SCRIPT),
            "--component-key",
            component_key,
            "--report-dir",
            report_dir,
            "--use-subtransfers",
            "--transfer-edge-scope",
            "source-in-scope",
            "--workflow-grouping",
            "stage-bucket",
            "--use-csv",
            str(args.extract_dir),
        ]

        started = time.monotonic()
        if args.dry_run:
            exit_code = 0
            stdout = ""
            stderr = ""
        else:
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
            )
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
            log_path.write_text(stdout + stderr, encoding="utf-8")
        duration_sec = round(time.monotonic() - started, 3)

        result = {
            "index": index,
            "batch_key": batch_key,
            "component_key": component_key,
            "report_dir": report_dir,
            "log_path": str(log_path),
            "duration_sec": duration_sec,
            "exit_code": exit_code,
            "success": exit_code == 0,
            "command": command,
        }
        results.append(result)
        status = "OK" if exit_code == 0 else "FAIL"
        print(f"[{index}/{len(rows)}] {status} {batch_key} ({duration_sec:.3f}s)")

        if exit_code != 0:
            failures.append(result)
            if not args.continue_on_error:
                break

    finished_at = datetime.now(timezone.utc)
    summary = {
        "queue_csv": str(args.queue_csv),
        "extract_dir": str(args.extract_dir),
        "dry_run": args.dry_run,
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "attempted": len(results),
        "succeeded": sum(1 for item in results if item["success"]),
        "failed": len(failures),
        "failed_batch_keys": [item["batch_key"] for item in failures],
    }
    summary_json = args.output_dir / "run_summary.json"
    summary_csv = args.output_dir / "run_summary.csv"
    summary_json.write_text(
        json.dumps(
            {
                "summary": summary,
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "index",
                "batch_key",
                "component_key",
                "report_dir",
                "log_path",
                "duration_sec",
                "exit_code",
                "success",
            ],
        )
        writer.writeheader()
        for row in results:
            writer.writerow(
                {
                    "index": row["index"],
                    "batch_key": row["batch_key"],
                    "component_key": row["component_key"],
                    "report_dir": row["report_dir"],
                    "log_path": row["log_path"],
                    "duration_sec": row["duration_sec"],
                    "exit_code": row["exit_code"],
                    "success": row["success"],
                }
            )

    print(json.dumps(summary, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
