#!/usr/bin/env python3
"""Targeted extraction for Action + ActionMetaData by OperationID, population, or date window.

This avoids full-table extraction by scoping to known OperationIDs, known
PopulationIDs, or a bounded Operations.StartTime range.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migration.extractors.base import BaseExtractor, ExtractionContext


DEFAULT_EXTRACT_DIR = PROJECT_ROOT / "scripts/migration/data/extract"
DEFAULT_OUTPUT_DIR = DEFAULT_EXTRACT_DIR / "targeted_actions"

DEFAULT_CSV_SOURCES = [
    ("sub_transfers.csv", "OperationID"),
    ("population_links.csv", "OperationID"),
    ("transfer_edges.csv", "OperationID"),
    ("transfer_operations.csv", "OperationID"),
    ("internal_delivery_operations.csv", "OperationID"),
]


def chunked(items: Sequence[str], size: int) -> Iterator[List[str]]:
    for i in range(0, len(items), size):
        yield list(items[i:i + size])


def load_ids_from_csv(path: Path, column: str) -> set[str]:
    if not path.exists():
        return set()
    with path.open() as handle:
        reader = csv.DictReader(handle)
        return {row.get(column, "").strip() for row in reader if row.get(column, "").strip()}


def parse_id_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [chunk.strip() for chunk in raw.split(",") if chunk.strip()]


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace(" ", "T"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value


def load_input_project_ids(extract_dir: Path, project_name: str | None, year_class: str | None) -> list[str]:
    if not project_name:
        return []
    input_projects_path = extract_dir / "input_projects.csv"
    if not input_projects_path.exists():
        return []
    target_name = project_name.strip().lower()
    target_year = (year_class or "").strip()
    project_ids: list[str] = []
    with input_projects_path.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("ProjectName") or "").strip().lower()
            if name != target_name:
                continue
            if year_class and (row.get("YearClass") or "").strip() != target_year:
                continue
            pid = (row.get("InputProjectID") or "").strip()
            if pid:
                project_ids.append(pid)
    return project_ids


def load_population_ids_from_projects(extract_dir: Path, project_ids: list[str]) -> set[str]:
    if not project_ids:
        return set()
    fish_group_path = extract_dir / "fish_group_history.csv"
    if not fish_group_path.exists():
        return set()
    wanted = set(project_ids)
    population_ids: set[str] = set()
    with fish_group_path.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if (row.get("InputProjectID") or "").strip() not in wanted:
                continue
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id:
                population_ids.add(pop_id)
    return population_ids


def load_population_ids_from_ext_inputs(extract_dir: Path, input_name: str, year_class: str | None) -> set[str]:
    ext_inputs_path = extract_dir / "ext_inputs.csv"
    if not ext_inputs_path.exists():
        return set()
    target_name = input_name.strip().lower()
    target_year = (year_class or "").strip()
    population_ids: set[str] = set()
    with ext_inputs_path.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("InputName") or "").strip().lower()
            if name != target_name:
                continue
            if year_class and (row.get("YearClass") or "").strip() != target_year:
                continue
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id:
                population_ids.add(pop_id)
    return population_ids


def fetch_operation_ids_by_date(extractor: BaseExtractor, since: str | None, until: str | None) -> list[str]:
    filters = []
    if since:
        filters.append(f"o.StartTime >= '{since}'")
    if until:
        filters.append(f"o.StartTime < '{until}'")
    if not filters:
        return []
    where_clause = " AND ".join(filters)
    query = f"""
        SELECT CONVERT(varchar(36), o.OperationID) AS OperationID
        FROM dbo.Operations o
        WHERE {where_clause}
    """
    rows = extractor._run_sqlcmd(query=query, headers=["OperationID"])
    return [row["OperationID"] for row in rows if row.get("OperationID")]


def write_rows(path: Path, headers: list[str], rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def fetch_actions_by_population(
    extractor: BaseExtractor,
    population_ids: set[str],
    since: str | None,
    until: str | None,
    chunk_size: int,
) -> tuple[list[dict], list[str], set[str]]:
    action_headers = ["ActionID", "OperationID", "PopulationID", "ActionType", "ActionOrder"]
    action_rows: list[dict] = []
    action_ids: list[str] = []
    operation_ids: set[str] = set()

    for chunk in chunked(sorted(population_ids), chunk_size):
        in_list = ", ".join(f"'{pid}'" for pid in chunk)
        if since or until:
            filters = [f"a.PopulationID IN ({in_list})"]
            if since:
                filters.append(f"o.StartTime >= '{since}'")
            if until:
                filters.append(f"o.StartTime < '{until}'")
            where_clause = " AND ".join(filters)
            query = f"""
                SELECT
                    CONVERT(varchar(36), a.ActionID) AS ActionID,
                    CONVERT(varchar(36), a.OperationID) AS OperationID,
                    CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                    CONVERT(varchar(10), a.ActionType) AS ActionType,
                    CONVERT(varchar(10), a.ActionOrder) AS ActionOrder
                FROM dbo.Action a
                JOIN dbo.Operations o ON a.OperationID = o.OperationID
                WHERE {where_clause}
            """
        else:
            query = f"""
                SELECT
                    CONVERT(varchar(36), a.ActionID) AS ActionID,
                    CONVERT(varchar(36), a.OperationID) AS OperationID,
                    CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                    CONVERT(varchar(10), a.ActionType) AS ActionType,
                    CONVERT(varchar(10), a.ActionOrder) AS ActionOrder
                FROM dbo.Action a
                WHERE a.PopulationID IN ({in_list})
            """
        rows = extractor._run_sqlcmd(query=query, headers=action_headers)
        for row in rows:
            action_rows.append(row)
            if row.get("ActionID"):
                action_ids.append(row["ActionID"])
            if row.get("OperationID"):
                operation_ids.add(row["OperationID"])

    return action_rows, action_ids, operation_ids


def fetch_actions_by_operation(
    extractor: BaseExtractor,
    operation_ids: list[str],
    chunk_size: int,
) -> tuple[list[dict], list[str]]:
    action_headers = ["ActionID", "OperationID", "PopulationID", "ActionType", "ActionOrder"]
    action_rows: list[dict] = []
    action_ids: list[str] = []

    for chunk in chunked(operation_ids, chunk_size):
        in_list = ", ".join(f"'{op}'" for op in chunk)
        query = f"""
            SELECT
                CONVERT(varchar(36), a.ActionID) AS ActionID,
                CONVERT(varchar(36), a.OperationID) AS OperationID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(10), a.ActionType) AS ActionType,
                CONVERT(varchar(10), a.ActionOrder) AS ActionOrder
            FROM dbo.Action a
            WHERE a.OperationID IN ({in_list})
        """
        rows = extractor._run_sqlcmd(query=query, headers=action_headers)
        for row in rows:
            action_rows.append(row)
            if row.get("ActionID"):
                action_ids.append(row["ActionID"])

    return action_rows, action_ids


def fetch_operations(
    extractor: BaseExtractor,
    operation_ids: list[str],
    chunk_size: int,
) -> list[dict]:
    operations_headers = [
        "OperationID",
        "StartTime",
        "EndTime",
        "OperationType",
        "Comment",
        "RegistrationTime",
    ]
    op_rows: list[dict] = []
    for chunk in chunked(operation_ids, chunk_size):
        in_list = ", ".join(f"'{op}'" for op in chunk)
        query = f"""
            SELECT
                CONVERT(varchar(36), o.OperationID) AS OperationID,
                CONVERT(varchar(32), o.StartTime, 120) AS StartTime,
                CONVERT(varchar(32), o.EndTime, 120) AS EndTime,
                CONVERT(varchar(10), o.OperationType) AS OperationType,
                CONVERT(varchar(max), o.Comment) AS Comment,
                CONVERT(varchar(32), o.RegistrationTime, 120) AS RegistrationTime
            FROM dbo.Operations o
            WHERE o.OperationID IN ({in_list})
        """
        rows = extractor._run_sqlcmd(query=query, headers=operations_headers)
        op_rows.extend(rows)
    return op_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Targeted extract of Action + ActionMetaData")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--extract-dir", default=str(DEFAULT_EXTRACT_DIR))
    parser.add_argument("--sql-profile", default="fishtalk_readonly")
    parser.add_argument("--operation-ids", help="Comma-separated OperationIDs")
    parser.add_argument("--operation-ids-file", help="File with OperationID per line")
    parser.add_argument("--population-ids", help="Comma-separated PopulationIDs")
    parser.add_argument("--population-ids-file", help="File with PopulationID per line")
    parser.add_argument("--input-project-id", help="InputProjects.InputProjectID")
    parser.add_argument("--input-project-name", help="InputProjects.ProjectName")
    parser.add_argument("--year-class", help="Optional YearClass filter for input project or input name")
    parser.add_argument("--input-name", help="Ext_Inputs_v2.InputName")
    parser.add_argument(
        "--from-csv",
        action="append",
        default=[],
        help="CSV source in the form path:column (repeatable)",
    )
    parser.add_argument(
        "--use-default-csv",
        action="store_true",
        help=(
            "Load OperationIDs from default extract CSVs "
            "(sub_transfers, population_links, transfer_edges, "
            "transfer_operations, internal_delivery_operations)"
        ),
    )
    parser.add_argument("--since", help="Operations.StartTime >= (YYYY-MM-DD or ISO datetime)")
    parser.add_argument("--until", help="Operations.StartTime < (YYYY-MM-DD or ISO datetime)")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--skip-metadata", action="store_true", help="Skip ActionMetaData extraction")
    parser.add_argument("--include-operations", action="store_true", help="Write operations_targeted.csv")
    args = parser.parse_args()

    extract_dir = Path(args.extract_dir)
    output_dir = Path(args.output_dir)

    operation_ids: set[str] = set(parse_id_list(args.operation_ids))
    population_ids: set[str] = set(parse_id_list(args.population_ids))

    if args.operation_ids_file:
        path = Path(args.operation_ids_file)
        if path.exists():
            with path.open() as handle:
                operation_ids.update(line.strip() for line in handle if line.strip())

    if args.population_ids_file:
        path = Path(args.population_ids_file)
        if path.exists():
            with path.open() as handle:
                population_ids.update(line.strip() for line in handle if line.strip())

    if args.input_project_id:
        population_ids.update(load_population_ids_from_projects(extract_dir, [args.input_project_id.strip()]))
    elif args.input_project_name:
        project_ids = load_input_project_ids(extract_dir, args.input_project_name, args.year_class)
        population_ids.update(load_population_ids_from_projects(extract_dir, project_ids))

    if args.input_name:
        population_ids.update(load_population_ids_from_ext_inputs(extract_dir, args.input_name, args.year_class))

    if args.use_default_csv:
        for filename, column in DEFAULT_CSV_SOURCES:
            operation_ids.update(load_ids_from_csv(extract_dir / filename, column))

    for entry in args.from_csv:
        if ":" not in entry:
            raise SystemExit(f"--from-csv must be path:column (got {entry})")
        path_str, column = entry.split(":", 1)
        path = Path(path_str)
        if not path.is_absolute():
            path = extract_dir / path
        operation_ids.update(load_ids_from_csv(path, column))

    since = parse_date(args.since)
    until = parse_date(args.until)

    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))

    action_rows: list[dict] = []
    action_ids: list[str] = []

    if population_ids:
        action_rows, action_ids, op_ids = fetch_actions_by_population(
            extractor, population_ids, since, until, args.chunk_size
        )
        operation_ids.update(op_ids)
    else:
        if not operation_ids and not (since or until):
            raise SystemExit("Provide OperationIDs, PopulationIDs, or a --since/--until date window.")

        if since or until:
            dated_ids = set(fetch_operation_ids_by_date(extractor, since, until))
            if operation_ids:
                operation_ids = operation_ids & dated_ids
            else:
                operation_ids = dated_ids

        operation_list = sorted(operation_ids)
        if not operation_list:
            raise SystemExit("No OperationIDs found after applying filters.")

        action_rows, action_ids = fetch_actions_by_operation(extractor, operation_list, args.chunk_size)

    action_headers = ["ActionID", "OperationID", "PopulationID", "ActionType", "ActionOrder"]
    actions_out = output_dir / "actions_targeted.csv"
    action_count = write_rows(actions_out, action_headers, action_rows)
    print(f"Wrote {action_count} actions to {actions_out}")

    if args.include_operations and operation_ids:
        operations = fetch_operations(extractor, sorted(operation_ids), args.chunk_size)
        ops_out = output_dir / "operations_targeted.csv"
        ops_headers = [
            "OperationID",
            "StartTime",
            "EndTime",
            "OperationType",
            "Comment",
            "RegistrationTime",
        ]
        write_rows(ops_out, ops_headers, operations)
        print(f"Wrote {len(operations)} operations to {ops_out}")

    if args.skip_metadata:
        return

    if not action_ids:
        print("No ActionIDs found; skipping ActionMetaData.")
        return

    metadata_headers = [
        "ActionID",
        "ParameterID",
        "ParameterString",
        "ParameterValue",
        "ParameterDate",
        "ParameterGuid",
    ]
    metadata_out = output_dir / "action_metadata_targeted.csv"
    metadata_rows: list[dict] = []

    for chunk in chunked(sorted(set(action_ids)), args.chunk_size):
        in_list = ", ".join(f"'{aid}'" for aid in chunk)
        query = f"""
            SELECT
                CONVERT(varchar(36), m.ActionID) AS ActionID,
                CONVERT(varchar(10), m.ParameterID) AS ParameterID,
                ISNULL(m.ParameterString, '') AS ParameterString,
                ISNULL(CONVERT(varchar(64), m.ParameterValue), '') AS ParameterValue,
                CONVERT(varchar(19), m.ParameterDate, 120) AS ParameterDate,
                ISNULL(CONVERT(varchar(36), m.ParameterGuid), '') AS ParameterGuid
            FROM dbo.ActionMetaData m
            WHERE m.ActionID IN ({in_list})
        """
        rows = extractor._run_sqlcmd(query=query, headers=metadata_headers)
        metadata_rows.extend(rows)

    write_rows(metadata_out, metadata_headers, metadata_rows)
    print(f"Wrote {len(metadata_rows)} action metadata rows to {metadata_out}")


if __name__ == "__main__":
    main()
