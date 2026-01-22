#!/usr/bin/env python3
# flake8: noqa
"""Build a SQLite index for environmental readings.

This script converts large CSV files into a SQLite database with indexes
to enable fast per-container/time queries during migration.

Usage:
    python build_environmental_sqlite.py \
      --input-dir scripts/migration/data/extract/ \
      --output-path scripts/migration/data/extract/environmental_readings.sqlite
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from pathlib import Path
from typing import Iterable, List, Tuple


def chunked(rows: Iterable[Tuple[str, ...]], size: int) -> Iterable[List[Tuple[str, ...]]]:
    batch: List[Tuple[str, ...]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build SQLite index for environmental CSV data")
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing daily_sensor_readings.csv and time_sensor_readings.csv",
    )
    parser.add_argument(
        "--output-path",
        required=True,
        help="Output SQLite database path",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50000,
        help="Insert batch size (default: 50000)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing SQLite file if present",
    )
    return parser


def create_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS daily_sensor_readings ("
        "ContainerID TEXT, SensorID TEXT, ReadingDate TEXT, Reading TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS time_sensor_readings ("
        "ContainerID TEXT, SensorID TEXT, ReadingTime TEXT, Reading TEXT)"
    )
    conn.commit()


def load_csv_into_table(
    conn: sqlite3.Connection,
    csv_path: Path,
    table_name: str,
    columns: List[str],
    batch_size: int,
) -> int:
    total = 0
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = (tuple(row.get(col, "") for col in columns) for row in reader)
        for batch in chunked(rows, batch_size):
            conn.executemany(
                f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                batch,
            )
            total += len(batch)
    conn.commit()
    return total


def create_indexes(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_daily_container_date "
        "ON daily_sensor_readings (ContainerID, ReadingDate)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_time_container_time "
        "ON time_sensor_readings (ContainerID, ReadingTime)"
    )
    conn.commit()


def main() -> int:
    args = build_parser().parse_args()
    input_dir = Path(args.input_dir)
    output_path = Path(args.output_path)

    daily_path = input_dir / "daily_sensor_readings.csv"
    time_path = input_dir / "time_sensor_readings.csv"

    if not daily_path.exists() or not time_path.exists():
        missing = [str(p) for p in (daily_path, time_path) if not p.exists()]
        print(f"Missing required CSV files: {', '.join(missing)}")
        return 1

    if output_path.exists():
        if args.replace:
            output_path.unlink()
        else:
            print(f"Output file already exists: {output_path}. Use --replace to overwrite.")
            return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(output_path)
    try:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA cache_size=200000")

        create_tables(conn)

        print("Loading daily_sensor_readings.csv...")
        daily_count = load_csv_into_table(
            conn,
            daily_path,
            "daily_sensor_readings",
            ["ContainerID", "SensorID", "ReadingDate", "Reading"],
            args.batch_size,
        )
        print(f"  Inserted {daily_count:,} rows")

        print("Loading time_sensor_readings.csv...")
        time_count = load_csv_into_table(
            conn,
            time_path,
            "time_sensor_readings",
            ["ContainerID", "SensorID", "ReadingTime", "Reading"],
            args.batch_size,
        )
        print(f"  Inserted {time_count:,} rows")

        print("Creating indexes...")
        create_indexes(conn)

        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("ANALYZE")
    finally:
        conn.close()

    print(f"SQLite index built: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
