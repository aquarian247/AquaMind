#!/usr/bin/env python3
"""Empirically map Operations.OperationType to domain tables with OperationID."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migration.extractors.base import BaseExtractor, ExtractionContext


SCHEMA_PATH = PROJECT_ROOT / "aquamind/docs/database/migration/schema_snapshots/fishtalk_schema_snapshot.json"
DEFAULT_EXTRACT_DIR = PROJECT_ROOT / "scripts/migration/data/extract"

DEFAULT_EXCLUDE = {
    "Operations",
    "Action",
}


def load_schema_operation_tables(schema_path: Path, exclude: set[str]) -> list[str]:
    with schema_path.open() as handle:
        data = json.load(handle)
    tables = set()
    for col in data["columns"]:
        if col["column_name"] == "OperationID":
            tables.add(col["table_name"])
    return sorted(t for t in tables if t not in exclude)


def chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def fetch_operation_ids(extractor: BaseExtractor, table: str, limit: int) -> list[str]:
    query = f"""
        SELECT TOP ({limit})
            CONVERT(varchar(36), OperationID) AS OperationID
        FROM dbo.{table}
        WHERE OperationID IS NOT NULL
    """
    rows = extractor._run_sqlcmd(query=query, headers=["OperationID"])
    return [row["OperationID"] for row in rows if row.get("OperationID")]


def fetch_operation_types(extractor: BaseExtractor, operation_ids: list[str]) -> dict[str, str]:
    op_types: dict[str, str] = {}
    for chunk in chunked(operation_ids, 500):
        in_list = ", ".join(f"'{oid}'" for oid in chunk)
        query = f"""
            SELECT
                CONVERT(varchar(36), OperationID) AS OperationID,
                CONVERT(varchar(10), OperationType) AS OperationType
            FROM dbo.Operations
            WHERE OperationID IN ({in_list})
        """
        rows = extractor._run_sqlcmd(query=query, headers=["OperationID", "OperationType"])
        for row in rows:
            op_types[row["OperationID"]] = row.get("OperationType", "")
    return op_types


def load_public_operation_types(extract_dir: Path) -> dict[str, str]:
    path = extract_dir / "public_operation_types.csv"
    if not path.exists():
        return {}
    mapping: dict[str, str] = {}
    with path.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            mapping[str(row["OperationType"])] = row.get("Text", "")
    return mapping


def render_markdown(
    table_counts: dict[str, Counter],
    op_counts: dict[str, Counter],
    op_text: dict[str, str],
    weight_sample_counts: Counter | None,
    limit: int,
) -> str:
    lines = [
        "# OperationType Mapping (Empirical Sample)",
        "",
        f"Sample size per table: {limit}",
        "",
        "## Table → OperationType counts",
        "",
        "| Table | OperationType counts |",
        "|---|---|",
    ]
    for table in sorted(table_counts):
        parts = []
        for op_type, count in table_counts[table].most_common():
            label = op_text.get(op_type, "")
            suffix = f" ({label})" if label else ""
            parts.append(f"{op_type}:{count}{suffix}")
        lines.append(f"| `{table}` | {', '.join(parts) or 'No matches'} |")

    lines.extend([
        "",
        "## OperationType → Tables",
        "",
        "| OperationType | Tables (count) |",
        "|---|---|",
    ])
    for op_type in sorted(op_counts, key=lambda x: (x is None, x)):
        entries = ", ".join(
            f"`{table}`:{count}" for table, count in op_counts[op_type].most_common()
        )
        label = op_text.get(op_type, "")
        label_text = f" ({label})" if label else ""
        lines.append(f"| {op_type}{label_text} | {entries} |")

    if weight_sample_counts is not None:
        lines.extend([
            "",
            "## Ext_WeightSamples_v2 OperationType counts",
            "",
            "Source: `ext_weight_samples_v2.csv` (no OperationID, but OperationType present).",
            "",
            "| OperationType | Count |",
            "|---|---|",
        ])
        for op_type, count in weight_sample_counts.most_common():
            label = op_text.get(op_type, "")
            label_text = f" ({label})" if label else ""
            lines.append(f"| {op_type}{label_text} | {count} |")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Map OperationType to domain tables by sampling OperationIDs")
    parser.add_argument("--sql-profile", default="fishtalk_readonly")
    parser.add_argument("--schema-path", default=str(SCHEMA_PATH))
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--include", action="append", default=[], help="Explicit table include (repeatable)")
    parser.add_argument("--exclude", action="append", default=[], help="Explicit table exclude (repeatable)")
    parser.add_argument("--output", required=True, help="Markdown output path")
    parser.add_argument("--extract-dir", default=str(DEFAULT_EXTRACT_DIR))
    parser.add_argument("--skip-weight-samples", action="store_true")
    args = parser.parse_args()

    exclude = set(DEFAULT_EXCLUDE) | set(args.exclude)
    tables = args.include or load_schema_operation_tables(Path(args.schema_path), exclude)

    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))
    op_text = load_public_operation_types(Path(args.extract_dir))

    table_operation_ids: dict[str, list[str]] = {}
    all_operation_ids: list[str] = []
    for table in tables:
        ids = fetch_operation_ids(extractor, table, args.limit)
        if not ids:
            continue
        table_operation_ids[table] = ids
        all_operation_ids.extend(ids)

    if not all_operation_ids:
        raise SystemExit("No OperationIDs sampled from the selected tables.")

    op_types = fetch_operation_types(extractor, sorted(set(all_operation_ids)))

    table_counts: dict[str, Counter] = {}
    op_counts: dict[str, Counter] = defaultdict(Counter)
    for table, ids in table_operation_ids.items():
        counts = Counter(op_types.get(oid, "") for oid in ids if oid in op_types)
        table_counts[table] = counts
        for op_type, count in counts.items():
            op_counts[op_type][table] += count

    weight_sample_counts: Counter | None = None
    if not args.skip_weight_samples:
        weight_path = Path(args.extract_dir) / "ext_weight_samples_v2.csv"
        if weight_path.exists():
            weight_sample_counts = Counter()
            with weight_path.open() as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    op_type = str(row.get("OperationType", "")).strip()
                    if op_type:
                        weight_sample_counts[op_type] += 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_markdown(table_counts, op_counts, op_text, weight_sample_counts, args.limit),
        encoding="utf-8",
    )
    print(f"Wrote mapping report to {output_path}")


if __name__ == "__main__":
    main()
