#!/usr/bin/env python3
# flake8: noqa
"""Detect stale or cutoff FishTalk extract inputs before migration/analysis."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CSV_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"
DEFAULT_BACKUP_HORIZON_DATE = "2026-01-22"
DEFAULT_REQUIRED_TABLES = (
    "status_values",
    "sub_transfers",
    "operation_stage_changes",
    "populations",
    "ext_inputs",
    "containers",
)
TIME_COLUMN_BY_TABLE = {
    "status_values": "StatusTime",
    "sub_transfers": "OperationTime",
    "operation_stage_changes": "OperationTime",
}


@dataclass(frozen=True)
class TableFreshness:
    table: str
    path: str
    row_count: int
    time_column: str | None
    max_time_raw: str | None
    max_time_iso: str | None
    missing: bool = False
    missing_column: bool = False


@dataclass(frozen=True)
class ExtractFreshnessResult:
    passed: bool
    failures: list[str]
    warnings: list[str]
    horizon_date: str | None
    status_subtransfer_skew_hours: float | None
    operation_stage_lag_days: float | None
    tables: dict[str, TableFreshness]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["tables"] = {
            key: asdict(value)
            for key, value in self.tables.items()
        }
        return payload


def parse_timestamp(raw: str) -> datetime | None:
    value = (raw or "").strip()
    if not value:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_horizon_date(raw: str | None) -> date | None:
    value = (raw or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def scan_table(path: Path, time_column: str | None) -> tuple[int, str | None, bool]:
    row_count = 0
    max_raw: str | None = None
    missing_column = False
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        if time_column and time_column not in fieldnames:
            missing_column = True
        for row in reader:
            row_count += 1
            if time_column and not missing_column:
                raw_value = (row.get(time_column) or "").strip()
                if raw_value and (max_raw is None or raw_value > max_raw):
                    max_raw = raw_value
    return row_count, max_raw, missing_column


def evaluate_extract_freshness(
    *,
    csv_dir: Path,
    required_tables: list[str] | tuple[str, ...] = DEFAULT_REQUIRED_TABLES,
    horizon_date: str | None = None,
    max_status_subtransfer_skew_hours: int = 24,
    max_operation_stage_lag_days: int = 14,
    enforce_operation_stage_lag: bool = True,
    fail_on_warnings: bool = False,
) -> ExtractFreshnessResult:
    tables: dict[str, TableFreshness] = {}
    failures: list[str] = []
    warnings: list[str] = []
    horizon = parse_horizon_date(horizon_date)

    for table in required_tables:
        csv_path = csv_dir / f"{table}.csv"
        time_column = TIME_COLUMN_BY_TABLE.get(table)
        if not csv_path.exists():
            tables[table] = TableFreshness(
                table=table,
                path=str(csv_path),
                row_count=0,
                time_column=time_column,
                max_time_raw=None,
                max_time_iso=None,
                missing=True,
                missing_column=False,
            )
            failures.append(f"Missing required extract file: {csv_path}")
            continue

        row_count, max_raw, missing_column = scan_table(csv_path, time_column)
        max_dt = parse_timestamp(max_raw or "")
        tables[table] = TableFreshness(
            table=table,
            path=str(csv_path),
            row_count=row_count,
            time_column=time_column,
            max_time_raw=max_raw,
            max_time_iso=max_dt.isoformat(sep=" ") if max_dt else None,
            missing=False,
            missing_column=missing_column,
        )

        if row_count <= 0:
            failures.append(f"Required extract file has no data rows: {csv_path}")
        if time_column and missing_column:
            failures.append(
                f"Required time column '{time_column}' missing in {csv_path.name}"
            )
        if time_column and row_count > 0 and max_dt is None:
            failures.append(
                f"Unable to determine max timestamp for {csv_path.name} "
                f"(column={time_column})"
            )

    status_max = parse_timestamp(
        (tables.get("status_values") or TableFreshness("", "", 0, None, None, None))
        .max_time_raw
        or ""
    )
    sub_max = parse_timestamp(
        (tables.get("sub_transfers") or TableFreshness("", "", 0, None, None, None))
        .max_time_raw
        or ""
    )
    stage_max = parse_timestamp(
        (
            tables.get("operation_stage_changes")
            or TableFreshness("", "", 0, None, None, None)
        ).max_time_raw
        or ""
    )

    status_sub_skew_hours: float | None = None
    if status_max and sub_max:
        status_sub_skew_hours = abs(
            (status_max - sub_max).total_seconds() / 3600.0
        )
        if status_sub_skew_hours > max(float(max_status_subtransfer_skew_hours), 0.0):
            failures.append(
                "status_values/sub_transfers max-time skew exceeds threshold: "
                f"{status_sub_skew_hours:.2f}h > {max_status_subtransfer_skew_hours}h"
            )

    operation_stage_lag_days: float | None = None
    if stage_max and status_max and sub_max:
        anchor = max(status_max, sub_max)
        operation_stage_lag_days = (
            anchor - stage_max
        ).total_seconds() / 86400.0
        if operation_stage_lag_days > float(max_operation_stage_lag_days):
            message = (
                "operation_stage_changes max lags status/sub anchor beyond threshold: "
                f"{operation_stage_lag_days:.2f}d > {max_operation_stage_lag_days}d"
            )
            if enforce_operation_stage_lag:
                failures.append(message)
            else:
                warnings.append(message)

    if horizon:
        if status_max and status_max.date() < horizon:
            failures.append(
                "status_values max date is before requested horizon: "
                f"{status_max.date()} < {horizon}"
            )
        if sub_max and sub_max.date() < horizon:
            failures.append(
                "sub_transfers max date is before requested horizon: "
                f"{sub_max.date()} < {horizon}"
            )
        if stage_max and stage_max.date() < horizon:
            warnings.append(
                "operation_stage_changes max date is before requested horizon: "
                f"{stage_max.date()} < {horizon}"
            )

    passed = not failures and (not warnings or not fail_on_warnings)
    return ExtractFreshnessResult(
        passed=passed,
        failures=failures,
        warnings=warnings,
        horizon_date=horizon.isoformat() if horizon else None,
        status_subtransfer_skew_hours=status_sub_skew_hours,
        operation_stage_lag_days=operation_stage_lag_days,
        tables=tables,
    )


def print_summary(result: ExtractFreshnessResult) -> None:
    print("\nExtract freshness preflight")
    print("-" * 70)
    for table in sorted(result.tables):
        row = result.tables[table]
        status = "MISSING" if row.missing else "OK"
        max_display = row.max_time_iso or row.max_time_raw or "-"
        print(
            f"{table:<24} {status:<8} rows={row.row_count:<10} max={max_display}"
        )
    if result.status_subtransfer_skew_hours is not None:
        print(
            "status/sub_transfers skew (hours): "
            f"{result.status_subtransfer_skew_hours:.2f}"
        )
    if result.operation_stage_lag_days is not None:
        print(
            "operation_stage lag vs status/sub anchor (days): "
            f"{result.operation_stage_lag_days:.2f}"
        )
    if result.horizon_date:
        print(f"required horizon date: {result.horizon_date}")

    if result.failures:
        print("\nFailures:")
        for message in result.failures:
            print(f"- {message}")
    if result.warnings:
        print("\nWarnings:")
        for message in result.warnings:
            print(f"- {message}")

    print(f"\nPreflight result: {'PASS' if result.passed else 'FAIL'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run extract freshness/cutoff guard against migration CSVs"
    )
    parser.add_argument(
        "--csv-dir",
        default=str(DEFAULT_CSV_DIR),
        help="Extract CSV directory (default: scripts/migration/data/extract)",
    )
    parser.add_argument(
        "--horizon-date",
        default=DEFAULT_BACKUP_HORIZON_DATE,
        help=(
            "Minimum horizon date (YYYY-MM-DD). "
            "status_values/sub_transfers max dates must be >= this. "
            f"(default: {DEFAULT_BACKUP_HORIZON_DATE})"
        ),
    )
    parser.add_argument(
        "--required-table",
        action="append",
        default=[],
        help=(
            "Required CSV table basename without .csv (repeatable). "
            "Defaults to critical migration tables."
        ),
    )
    parser.add_argument(
        "--max-status-subtransfer-skew-hours",
        type=int,
        default=24,
        help="Max allowed skew between status_values and sub_transfers max times.",
    )
    parser.add_argument(
        "--max-operation-stage-lag-days",
        type=int,
        default=14,
        help="Max allowed lag for operation_stage_changes behind status/sub anchor.",
    )
    lag_group = parser.add_mutually_exclusive_group()
    lag_group.add_argument(
        "--enforce-operation-stage-lag",
        dest="enforce_operation_stage_lag",
        action="store_true",
        help=(
            "Treat operation_stage_changes lag threshold breaches as failures "
            "(default)."
        ),
    )
    lag_group.add_argument(
        "--allow-operation-stage-lag",
        dest="enforce_operation_stage_lag",
        action="store_false",
        help=(
            "Downgrade operation_stage_changes lag threshold breaches to warnings."
        ),
    )
    parser.set_defaults(enforce_operation_stage_lag=True)
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Fail preflight when warnings exist.",
    )
    parser.add_argument(
        "--output-json",
        help="Optional JSON output path for machine-readable preflight result.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    csv_dir = Path(args.csv_dir)
    required = tuple(args.required_table) if args.required_table else DEFAULT_REQUIRED_TABLES
    result = evaluate_extract_freshness(
        csv_dir=csv_dir,
        required_tables=required,
        horizon_date=args.horizon_date,
        max_status_subtransfer_skew_hours=args.max_status_subtransfer_skew_hours,
        max_operation_stage_lag_days=args.max_operation_stage_lag_days,
        enforce_operation_stage_lag=args.enforce_operation_stage_lag,
        fail_on_warnings=args.fail_on_warnings,
    )
    print_summary(result)

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result.to_dict(), indent=2),
            encoding="utf-8",
        )
        print(f"Wrote JSON report: {out_path}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
