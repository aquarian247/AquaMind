#!/usr/bin/env python3
"""Dump SQL Server schema metadata (FishTalk, AVEVA, etc.) for migration planning."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

CONFIG_MODULE_PATH = SCRIPT_DIR / 'config.py'
spec = importlib.util.spec_from_file_location('migration_config_module', CONFIG_MODULE_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Unable to load migration config helper at {CONFIG_MODULE_PATH}")
config_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = config_module
spec.loader.exec_module(config_module)
get_sqlserver_config = config_module.get_sqlserver_config

TABLE_HEADERS = ['schema_name', 'table_name', 'row_count']
COLUMN_HEADERS = [
    'schema_name', 'table_name', 'column_name', 'data_type',
    'is_nullable', 'char_max_length', 'numeric_precision',
    'numeric_scale', 'column_default'
]

TABLE_COUNT_QUERY = """
SELECT
    s.name AS schema_name,
    t.name AS table_name,
    SUM(p.rows) AS row_count
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0,1)
GROUP BY s.name, t.name
ORDER BY s.name, t.name
"""

COLUMN_QUERY = """
SELECT
    c.TABLE_SCHEMA AS schema_name,
    c.TABLE_NAME AS table_name,
    c.COLUMN_NAME AS column_name,
    c.DATA_TYPE AS data_type,
    c.IS_NULLABLE AS is_nullable,
    c.CHARACTER_MAXIMUM_LENGTH AS char_max_length,
    c.NUMERIC_PRECISION AS numeric_precision,
    c.NUMERIC_SCALE AS numeric_scale,
    c.COLUMN_DEFAULT AS column_default
FROM INFORMATION_SCHEMA.COLUMNS c
ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
"""


def _run_sqlcmd(query: str, headers: List[str], int_fields: List[str], profile: str, database: str, container: str) -> List[Dict[str, Any]]:
    sql = f"SET NOCOUNT ON; {query}"
    sql_config = get_sqlserver_config(profile)
    exec_port = sql_config.container_port or sql_config.port
    cmd = [
        'docker', 'exec', container, '/opt/mssql-tools18/bin/sqlcmd',
        '-C',
        '-S', f"{sql_config.server},{exec_port}",
        '-U', sql_config.uid,
        '-P', sql_config.pwd,
        '-d', database,
        '-h', '-1',
        '-W',
        '-w', '65535',
        '-s', '|',
        '-Q', sql,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    rows: List[Dict[str, Any]] = []
    for raw_line in proc.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [chunk.strip() for chunk in line.split('|')]
        if len(parts) != len(headers):  # skip spurious lines
            continue
        row = dict(zip(headers, parts))
        for field in int_fields:
            value = row.get(field)
            if value in (None, ''):
                row[field] = None
            else:
                try:
                    row[field] = int(value)
                except ValueError:
                    row[field] = None
        rows.append(row)
    return rows


def dump_schema(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    table_rows = _run_sqlcmd(TABLE_COUNT_QUERY, TABLE_HEADERS, ['row_count'], args.profile, args.database, args.container)
    column_rows = _run_sqlcmd(
        COLUMN_QUERY,
        COLUMN_HEADERS,
        ['char_max_length', 'numeric_precision', 'numeric_scale'],
        args.profile,
        args.database,
        args.container,
    )

    timestamp = datetime.now(timezone.utc).isoformat()

    table_path = output_dir / f'{args.label}_table_counts.csv'
    column_path = output_dir / f'{args.label}_columns.csv'
    snapshot_path = output_dir / f'{args.label}_schema_snapshot.json'

    _write_csv(table_path, TABLE_HEADERS, table_rows)
    _write_csv(column_path, COLUMN_HEADERS, column_rows)

    snapshot = {
        'generated_at': timestamp,
        'table_counts': table_rows,
        'columns': column_rows,
    }
    snapshot_path.write_text(json.dumps(snapshot, indent=2) + '\n', encoding='utf-8')

    print(f"📁 Wrote {table_path}")
    print(f"📁 Wrote {column_path}")
    print(f"📁 Wrote {snapshot_path}")


def _write_csv(path: Path, headers: List[str], rows: List[Dict[str, Any]]) -> None:
    import csv

    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in headers})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Dump FishTalk schema metadata.')
    parser.add_argument('--profile', default='fishtalk_readonly', help='Migration config profile to use (default: fishtalk_readonly)')
    parser.add_argument('--database', default='FishTalk', help='SQL Server database name (default: FishTalk)')
    parser.add_argument('--container', default='sqlserver', help='Docker container name running SQL Server (default: sqlserver)')
    parser.add_argument('--output-dir', default='aquamind/docs/database/migration/schema_snapshots', help='Where to write the schema snapshots')
    parser.add_argument('--label', default='fishtalk', help='Prefix label for the output files (default: fishtalk)')
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        dump_schema(args)
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"❌ sqlcmd failed: {exc.stderr or exc.stdout}")
        return 1
    except Exception as exc:
        print(f"❌ Schema dump failed: {exc}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
