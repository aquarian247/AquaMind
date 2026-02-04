#!/usr/bin/env python3
"""Empirically map Action.ActionType to domain tables by sampling ActionID sets."""

from __future__ import annotations

import argparse
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

DEFAULT_EXCLUDE = {
    "Action",
    "ActionMetaData",
    "PlanAction",
    "PlanActionMetaData",
    "ActionDocument",
}


def load_schema_action_tables(schema_path: Path, exclude: set[str]) -> list[str]:
    with schema_path.open() as handle:
        data = json.load(handle)
    tables = set()
    for col in data["columns"]:
        if col["column_name"] == "ActionID":
            tables.add(col["table_name"])
    return sorted(t for t in tables if t not in exclude)


def chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def fetch_action_ids(extractor: BaseExtractor, table: str, limit: int) -> list[str]:
    query = f"""
        SELECT TOP ({limit})
            CONVERT(varchar(36), ActionID) AS ActionID
        FROM dbo.{table}
        WHERE ActionID IS NOT NULL
    """
    rows = extractor._run_sqlcmd(query=query, headers=["ActionID"])
    return [row["ActionID"] for row in rows if row.get("ActionID")]


def fetch_action_types(extractor: BaseExtractor, action_ids: list[str]) -> dict[str, str]:
    action_types: dict[str, str] = {}
    for chunk in chunked(action_ids, 500):
        in_list = ", ".join(f"'{aid}'" for aid in chunk)
        query = f"""
            SELECT
                CONVERT(varchar(36), ActionID) AS ActionID,
                CONVERT(varchar(10), ActionType) AS ActionType
            FROM dbo.Action
            WHERE ActionID IN ({in_list})
        """
        rows = extractor._run_sqlcmd(query=query, headers=["ActionID", "ActionType"])
        for row in rows:
            action_types[row["ActionID"]] = row.get("ActionType", "")
    return action_types


def render_markdown(
    table_counts: dict[str, Counter],
    actiontype_counts: dict[str, Counter],
    limit: int,
) -> str:
    lines = [
        "# ActionType Mapping (Empirical Sample)",
        "",
        f"Sample size per table: {limit}",
        "",
        "## Table → ActionType counts",
        "",
        "| Table | ActionType counts |",
        "|---|---|",
    ]
    for table in sorted(table_counts):
        counts = ", ".join(f"{atype}:{count}" for atype, count in table_counts[table].most_common())
        lines.append(f"| `{table}` | {counts or 'No matches'} |")

    lines.extend([
        "",
        "## ActionType → Tables",
        "",
        "| ActionType | Tables (count) |",
        "|---|---|",
    ])
    for atype in sorted(actiontype_counts, key=lambda x: (x is None, x)):
        entries = ", ".join(
            f"`{table}`:{count}" for table, count in actiontype_counts[atype].most_common()
        )
        lines.append(f"| {atype} | {entries} |")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Map ActionType to domain tables by sampling ActionIDs")
    parser.add_argument("--sql-profile", default="fishtalk_readonly")
    parser.add_argument("--schema-path", default=str(SCHEMA_PATH))
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--include", action="append", default=[], help="Explicit table include (repeatable)")
    parser.add_argument("--exclude", action="append", default=[], help="Explicit table exclude (repeatable)")
    parser.add_argument("--output", required=True, help="Markdown output path")
    args = parser.parse_args()

    exclude = set(DEFAULT_EXCLUDE) | set(args.exclude)
    tables = args.include or load_schema_action_tables(Path(args.schema_path), exclude)

    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))

    table_action_ids: dict[str, list[str]] = {}
    all_action_ids: list[str] = []
    for table in tables:
        ids = fetch_action_ids(extractor, table, args.limit)
        if not ids:
            continue
        table_action_ids[table] = ids
        all_action_ids.extend(ids)

    if not all_action_ids:
        raise SystemExit("No ActionIDs sampled from the selected tables.")

    action_types = fetch_action_types(extractor, sorted(set(all_action_ids)))

    table_counts: dict[str, Counter] = {}
    actiontype_counts: dict[str, Counter] = defaultdict(Counter)
    for table, ids in table_action_ids.items():
        counts = Counter(action_types.get(aid, "") for aid in ids if aid in action_types)
        table_counts[table] = counts
        for atype, count in counts.items():
            actiontype_counts[atype][table] += count

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(table_counts, actiontype_counts, args.limit), encoding="utf-8")
    print(f"Wrote mapping report to {output_path}")


if __name__ == "__main__":
    main()
