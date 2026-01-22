#!/usr/bin/env python3
# flake8: noqa
"""Bulk extract all relevant FishTalk data to CSV files.

This script extracts FishTalk data in bulk for subsequent ETL migration:
- Single Docker connection with multiple queries
- Chunked extraction for large tables (>1M rows)
- Streams directly to CSV (no full dataset in memory)
- Progress reporting with estimated completion time

Usage:
    # Extract all tables
    python bulk_extract_fishtalk.py --output scripts/migration/data/extract/
    
    # Extract specific tables only
    python bulk_extract_fishtalk.py --output scripts/migration/data/extract/ --tables daily_readings,time_readings
    
    # Dry run to estimate volumes
    python bulk_extract_fishtalk.py --output scripts/migration/data/extract/ --dry-run

Output directory structure:
    scripts/migration/data/extract/
    ├── populations.csv               # ~350K rows
    ├── population_stages.csv         # ~150K rows
    ├── containers.csv                # ~17K rows
    ├── org_units.csv                 # ~100 rows
    ├── status_values.csv             # ~8M rows
    ├── daily_sensor_readings.csv     # ~50M rows -> is_manual=True
    ├── time_sensor_readings.csv      # ~50M rows -> is_manual=False
    ├── mortality_actions.csv         # ~5M rows
    ├── feeding_actions.csv           # ~5M rows
    ├── feeding_hand_weights.csv      # ~500K rows
    ├── transfer_operations.csv       # ~50K rows (legacy PublicTransfers operations)
    ├── transfer_edges.csv            # ~100K rows (legacy PublicTransfers - broken since Jan 2023)
    ├── sub_transfers.csv             # ~205K rows (SubTransfers - active through 2025, for chain stitching)
    ├── operation_stage_changes.csv   # ~27K rows (OperationProductionStageChange for stage timeline)
    ├── production_stages.csv         # ~100 rows (reference)
    └── ext_inputs.csv                # ~350K rows (Ext_Inputs_v2 - TRUE biological batch identifier)
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")

from scripts.migration.extractors.base import BaseExtractor, ExtractionContext

# Table configurations
# Format: (name, query, headers, estimated_rows, chunk_size)
# chunk_size=0 means extract all at once
TABLE_CONFIGS = {
    "populations": {
        "query": """
            SELECT 
                CONVERT(varchar(36), PopulationID) AS PopulationID,
                CONVERT(varchar(50), ProjectNumber) AS ProjectNumber,
                CONVERT(varchar(10), InputYear) AS InputYear,
                CONVERT(varchar(10), RunningNumber) AS RunningNumber,
                CONVERT(varchar(36), ContainerID) AS ContainerID,
                CONVERT(varchar(100), Species) AS Species,
                CONVERT(varchar(19), StartTime, 120) AS StartTime,
                CONVERT(varchar(19), EndTime, 120) AS EndTime
            FROM dbo.Populations
            ORDER BY StartTime ASC
        """,
        "headers": ["PopulationID", "ProjectNumber", "InputYear", "RunningNumber", 
                   "ContainerID", "Species", "StartTime", "EndTime"],
        "estimated_rows": 350000,
        "chunk_size": 0,  # Small enough to extract at once
    },
    "population_stages": {
        "query": """
            SELECT 
                CONVERT(varchar(36), PopulationID) AS PopulationID,
                CONVERT(varchar(36), StageID) AS StageID,
                CONVERT(varchar(19), StartTime, 120) AS StartTime
            FROM dbo.PopulationProductionStages
            ORDER BY StartTime ASC
        """,
        "headers": ["PopulationID", "StageID", "StartTime"],
        "estimated_rows": 150000,
        "chunk_size": 0,
    },
    "production_stages": {
        "query": """
            SELECT 
                CONVERT(varchar(36), StageID) AS StageID,
                CONVERT(varchar(100), StageName) AS StageName
            FROM dbo.ProductionStages
        """,
        "headers": ["StageID", "StageName"],
        "estimated_rows": 100,
        "chunk_size": 0,
    },
    "containers": {
        "query": """
            SELECT 
                CONVERT(varchar(36), c.ContainerID) AS ContainerID,
                CONVERT(varchar(200), c.ContainerName) AS ContainerName,
                CONVERT(varchar(36), c.OrgUnitID) AS OrgUnitID,
                CONVERT(varchar(50), c.OfficialID) AS OfficialID,
                CONVERT(varchar(50), c.ContainerType) AS ContainerType,
                CONVERT(varchar(36), c.GroupID) AS GroupID
            FROM dbo.Containers c
        """,
        "headers": ["ContainerID", "ContainerName", "OrgUnitID", "OfficialID", "ContainerType", "GroupID"],
        "estimated_rows": 17000,
        "chunk_size": 0,
    },
    "org_units": {
        "query": """
            SELECT 
                CONVERT(varchar(36), ou.OrgUnitID) AS OrgUnitID,
                CONVERT(varchar(200), ou.Name) AS Name,
                CONVERT(varchar(20), l.Latitude) AS Latitude,
                CONVERT(varchar(20), l.Longitude) AS Longitude
            FROM dbo.OrganisationUnit ou
            LEFT JOIN dbo.Locations l ON ou.LocationID = l.LocationID
        """,
        "headers": ["OrgUnitID", "Name", "Latitude", "Longitude"],
        "estimated_rows": 100,
        "chunk_size": 0,
    },
    "status_values": {
        "query_template": """
            SELECT 
                CONVERT(varchar(36), PopulationID) AS PopulationID,
                CONVERT(varchar(19), StatusTime, 120) AS StatusTime,
                CONVERT(varchar(20), CurrentCount) AS CurrentCount,
                CONVERT(varchar(20), CurrentBiomassKg) AS CurrentBiomassKg,
                CONVERT(varchar(20), Temperature) AS Temperature
            FROM dbo.PublicStatusValues
            WHERE StatusTime >= '{start_date}' AND StatusTime < '{end_date}'
            ORDER BY StatusTime ASC
        """,
        "headers": ["PopulationID", "StatusTime", "CurrentCount", "CurrentBiomassKg", "Temperature"],
        "estimated_rows": 8000000,
        "chunk_size": 500000,
        "chunk_by": "date",
    },
    "daily_sensor_readings": {
        "query_template": """
            SELECT 
                CONVERT(varchar(36), ContainerID) AS ContainerID,
                CONVERT(varchar(36), SensorID) AS SensorID,
                CONVERT(varchar(10), Date, 120) AS ReadingDate,
                CONVERT(varchar(32), Reading) AS Reading
            FROM dbo.Ext_DailySensorReadings_v2
            WHERE Date >= '{start_date}' AND Date < '{end_date}'
            ORDER BY Date ASC
        """,
        "headers": ["ContainerID", "SensorID", "ReadingDate", "Reading"],
        "estimated_rows": 50000000,
        "chunk_size": 1000000,
        "chunk_by": "date",
    },
    "time_sensor_readings": {
        "query_template": """
            SELECT 
                CONVERT(varchar(36), ContainerID) AS ContainerID,
                CONVERT(varchar(36), SensorID) AS SensorID,
                CONVERT(varchar(19), ReadingTime, 120) AS ReadingTime,
                CONVERT(varchar(32), Reading) AS Reading
            FROM dbo.Ext_SensorReadings_v2
            WHERE ReadingTime >= '{start_date}' AND ReadingTime < '{end_date}'
            ORDER BY ReadingTime ASC
        """,
        "headers": ["ContainerID", "SensorID", "ReadingTime", "Reading"],
        "estimated_rows": 50000000,
        "chunk_size": 1000000,
        "chunk_by": "date",
    },
    "mortality_actions": {
        "query": """
            SELECT 
                CONVERT(varchar(36), m.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime,
                CONVERT(varchar(32), m.MortalityCount) AS MortalityCount,
                CONVERT(varchar(64), m.MortalityBiomass) AS MortalityBiomass,
                CONVERT(varchar(36), m.MortalityCauseID) AS MortalityCauseID,
                ISNULL(mc.DefaultText, '') AS CauseText,
                REPLACE(REPLACE(REPLACE(ISNULL(m.Comment, ''), '|', '/'), CHAR(13), ' '), CHAR(10), ' ') AS Comment
            FROM dbo.Mortality m
            JOIN dbo.Action a ON a.ActionID = m.ActionID
            JOIN dbo.Operations o ON o.OperationID = a.OperationID
            LEFT JOIN dbo.MortalityCauses mc ON mc.MortalityCausesID = m.MortalityCauseID
            ORDER BY o.StartTime ASC
        """,
        "headers": ["ActionID", "PopulationID", "OperationStartTime", "MortalityCount", 
                   "MortalityBiomass", "MortalityCauseID", "CauseText", "Comment"],
        "estimated_rows": 5000000,
        "chunk_size": 0,
    },
    "feeding_actions": {
        "query": """
            SELECT 
                CONVERT(varchar(36), f.ActionID) AS ActionID,
                CONVERT(varchar(36), a.PopulationID) AS PopulationID,
                CONVERT(varchar(23), COALESCE(o.StartTime, f.OperationStartTime), 121) AS FeedingTime,
                CONVERT(varchar(32), f.FeedAmount) AS FeedAmountG,
                CONVERT(varchar(64), f.FeedBatchID) AS FeedBatchID,
                CONVERT(varchar(64), COALESCE(f.FeedTypeID, fb.FeedTypeID)) AS FeedTypeID,
                ISNULL(ft.Name, '') AS FeedTypeName,
                REPLACE(REPLACE(REPLACE(ISNULL(o.Comment, ''), '|', '/'), CHAR(13), ' '), CHAR(10), ' ') AS OperationComment
            FROM dbo.Feeding f
            JOIN dbo.Action a ON a.ActionID = f.ActionID
            LEFT JOIN dbo.Operations o ON o.OperationID = a.OperationID
            LEFT JOIN dbo.FeedBatch fb ON fb.FeedBatchID = f.FeedBatchID
            LEFT JOIN dbo.FeedTypes ft ON ft.FeedTypeID = COALESCE(f.FeedTypeID, fb.FeedTypeID)
            ORDER BY COALESCE(o.StartTime, f.OperationStartTime) ASC
        """,
        "headers": ["ActionID", "PopulationID", "FeedingTime", "FeedAmountG", 
                   "FeedBatchID", "FeedTypeID", "FeedTypeName", "OperationComment"],
        "estimated_rows": 5000000,
        "chunk_size": 0,
    },
    "feeding_hand_weights": {
        "query": """
            SELECT 
                CONVERT(varchar(36), hw.FeedingID) AS FeedingID,
                CONVERT(varchar(36), hw.FTActionID) AS ActionID,
                CONVERT(varchar(23), hw.StartTime, 121) AS FeedingTime,
                CONVERT(varchar(32), hw.FeedAmount) AS FeedAmountG,
                CONVERT(varchar(36), hw.HWUnitID) AS HWUnitID,
                CONVERT(varchar(36), hw.HWSiloID) AS HWSiloID,
                ISNULL(hw.StopReason, '') AS StopReason
            FROM dbo.HWFeeding hw
        """,
        "headers": ["FeedingID", "ActionID", "FeedingTime", "FeedAmountG", "HWUnitID", "HWSiloID", "StopReason"],
        "estimated_rows": 0,  # Table is empty in FishTalk
        "chunk_size": 0,
    },
    "transfer_operations": {
        "query": """
            SELECT 
                CONVERT(varchar(36), o.OperationID) AS OperationID,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime,
                CONVERT(varchar(19), o.EndTime, 120) AS OperationEndTime,
                CONVERT(varchar(500), o.Comment) AS Comment
            FROM dbo.Operations o
            WHERE o.OperationID IN (SELECT DISTINCT OperationID FROM dbo.PublicTransfers)
            ORDER BY o.StartTime ASC
        """,
        "headers": ["OperationID", "OperationStartTime", "OperationEndTime", "Comment"],
        "estimated_rows": 50000,
        "chunk_size": 0,
    },
    "transfer_edges": {
        "query": """
            SELECT 
                CONVERT(varchar(36), pt.OperationID) AS OperationID,
                CONVERT(varchar(36), pt.SourcePop) AS SourcePop,
                CONVERT(varchar(36), pt.DestPop) AS DestPop,
                CONVERT(varchar(64), pt.ShareCountForward) AS ShareCountForward,
                CONVERT(varchar(64), pt.ShareBiomassForward) AS ShareBiomassForward
            FROM dbo.PublicTransfers pt
            ORDER BY pt.OperationID ASC
        """,
        "headers": ["OperationID", "SourcePop", "DestPop", "ShareCountForward", "ShareBiomassForward"],
        "estimated_rows": 100000,
        "chunk_size": 0,
    },
    # SubTransfers-based stitching tables (replaces project-based stitching)
    "sub_transfers": {
        "query": """
            SELECT 
                CONVERT(varchar(36), st.SubTransferID) AS SubTransferID,
                CONVERT(varchar(36), st.OperationID) AS OperationID,
                CONVERT(varchar(36), st.SourcePopBefore) AS SourcePopBefore,
                CONVERT(varchar(36), st.SourcePopAfter) AS SourcePopAfter,
                CONVERT(varchar(36), st.DestPopBefore) AS DestPopBefore,
                CONVERT(varchar(36), st.DestPopAfter) AS DestPopAfter,
                CONVERT(varchar(10), st.TransferType) AS TransferType,
                CONVERT(varchar(32), st.ShareCountFwd) AS ShareCountFwd,
                CONVERT(varchar(32), st.ShareBiomFwd) AS ShareBiomFwd,
                CONVERT(varchar(32), st.ShareCountBwd) AS ShareCountBwd,
                CONVERT(varchar(32), st.ShareBiomBwd) AS ShareBiomBwd,
                CONVERT(varchar(32), st.BranchedCount) AS BranchedCount,
                CONVERT(varchar(32), st.BranchedBiomass) AS BranchedBiomass,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationTime
            FROM dbo.SubTransfers st
            JOIN dbo.Operations o ON o.OperationID = st.OperationID
            ORDER BY o.StartTime ASC
        """,
        "headers": ["SubTransferID", "OperationID", "SourcePopBefore", "SourcePopAfter", 
                   "DestPopBefore", "DestPopAfter", "TransferType", "ShareCountFwd", 
                   "ShareBiomFwd", "ShareCountBwd", "ShareBiomBwd", "BranchedCount", 
                   "BranchedBiomass", "OperationTime"],
        "estimated_rows": 205000,
        "chunk_size": 0,
    },
    "operation_stage_changes": {
        "query": """
            SELECT 
                CONVERT(varchar(36), opsc.OperationID) AS OperationID,
                CONVERT(varchar(36), opsc.PPSPopID) AS PopulationID,
                CONVERT(varchar(36), opsc.PPSStageID) AS StageID,
                CONVERT(varchar(19), opsc.PPSStartTime, 120) AS StageStartTime,
                CONVERT(varchar(19), o.StartTime, 120) AS OperationTime
            FROM dbo.OperationProductionStageChange opsc
            JOIN dbo.Operations o ON o.OperationID = opsc.OperationID
            ORDER BY opsc.PPSStartTime ASC
        """,
        "headers": ["OperationID", "PopulationID", "StageID", "StageStartTime", "OperationTime"],
        "estimated_rows": 27000,
        "chunk_size": 0,
    },
    # Input-based batch identification (2026-01-22 breakthrough)
    "ext_inputs": {
        "query": """
            SELECT 
                CONVERT(varchar(36), i.PopulationID) AS PopulationID,
                ISNULL(i.InputName, '') AS InputName,
                ISNULL(CONVERT(varchar(10), i.InputNumber), '0') AS InputNumber,
                ISNULL(CONVERT(varchar(10), i.YearClass), '') AS YearClass,
                ISNULL(CONVERT(varchar(36), i.Supplier), '') AS SupplierID,
                CONVERT(varchar(19), i.StartTime, 120) AS StartTime,
                ISNULL(CONVERT(varchar(32), i.InputCount), '0') AS InputCount,
                ISNULL(CONVERT(varchar(32), i.InputBiomass), '0') AS InputBiomass,
                ISNULL(CONVERT(varchar(10), i.Species), '') AS Species,
                ISNULL(CONVERT(varchar(10), i.FishType), '') AS FishType,
                ISNULL(CONVERT(varchar(10), i.Broodstock), '') AS Broodstock,
                ISNULL(i.DeliveryID, '') AS DeliveryID,
                ISNULL(CONVERT(varchar(36), i.Transporter), '') AS Transporter
            FROM dbo.Ext_Inputs_v2 i
            ORDER BY i.StartTime ASC
        """,
        "headers": ["PopulationID", "InputName", "InputNumber", "YearClass", "SupplierID",
                   "StartTime", "InputCount", "InputBiomass", "Species", "FishType",
                   "Broodstock", "DeliveryID", "Transporter"],
        "estimated_rows": 25000,
        "chunk_size": 0,
    },
}


class BulkExtractor:
    """Bulk extractor that streams FishTalk data to CSV files."""
    
    def __init__(self, output_dir: Path, profile: str = "fishtalk_readonly"):
        self.output_dir = output_dir
        self.extractor = BaseExtractor(ExtractionContext(profile=profile))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def get_date_range(self) -> tuple[datetime, datetime]:
        """Get the overall date range from FishTalk data."""
        # Query for min/max dates
        min_rows = self.extractor._run_sqlcmd(
            query="SELECT CONVERT(varchar(10), MIN(StartTime), 120) AS MinDate FROM dbo.Populations WHERE StartTime IS NOT NULL",
            headers=["MinDate"],
        )
        max_rows = self.extractor._run_sqlcmd(
            query="SELECT CONVERT(varchar(10), MAX(EndTime), 120) AS MaxDate FROM dbo.Populations WHERE EndTime IS NOT NULL",
            headers=["MaxDate"],
        )
        
        min_date = datetime(2010, 1, 1)  # Fallback
        max_date = datetime.now()
        
        if min_rows and min_rows[0].get("MinDate"):
            try:
                min_date = datetime.strptime(min_rows[0]["MinDate"], "%Y-%m-%d")
            except (ValueError, TypeError):
                pass
                
        if max_rows and max_rows[0].get("MaxDate"):
            try:
                max_date = datetime.strptime(max_rows[0]["MaxDate"], "%Y-%m-%d")
            except (ValueError, TypeError):
                pass
                
        return min_date, max_date
    
    def count_rows(self, table_name: str) -> int:
        """Get exact row count for a table."""
        config = TABLE_CONFIGS.get(table_name)
        if not config:
            return 0
            
        # Build count query from the base query
        if "query" in config:
            base_query = config["query"]
        else:
            # For chunked tables, we need a simpler count
            table_map = {
                "status_values": "dbo.PublicStatusValues",
                "daily_sensor_readings": "dbo.Ext_DailySensorReadings_v2",
                "time_sensor_readings": "dbo.Ext_SensorReadings_v2",
            }
            if table_name in table_map:
                count_query = f"SELECT COUNT(*) AS RowCount FROM {table_map[table_name]}"
            else:
                return config.get("estimated_rows", 0)
        
        if "query" in config:
            # Extract FROM clause and wrap with COUNT
            # Simple approach: just use the config's table
            from_idx = base_query.upper().find("FROM ")
            if from_idx == -1:
                return config.get("estimated_rows", 0)
            
            from_clause = base_query[from_idx:]
            # Remove ORDER BY if present
            order_idx = from_clause.upper().find("ORDER BY")
            if order_idx != -1:
                from_clause = from_clause[:order_idx]
            
            count_query = f"SELECT COUNT(*) AS RowCount {from_clause}"
        
        try:
            rows = self.extractor._run_sqlcmd(query=count_query, headers=["RowCount"])
            if rows and rows[0].get("RowCount"):
                return int(rows[0]["RowCount"])
        except Exception as e:
            print(f"  Warning: Could not count {table_name}: {e}")
            
        return config.get("estimated_rows", 0)
    
    def extract_simple(self, table_name: str, dry_run: bool = False) -> int:
        """Extract a simple (non-chunked) table."""
        config = TABLE_CONFIGS.get(table_name)
        if not config:
            print(f"  Unknown table: {table_name}")
            return 0
            
        output_path = self.output_dir / f"{table_name}.csv"
        
        if dry_run:
            count = self.count_rows(table_name)
            print(f"  [DRY RUN] {table_name}: ~{count:,} rows -> {output_path.name}")
            return count
        
        print(f"  Extracting {table_name}...", end=" ", flush=True)
        start_time = time.time()
        
        try:
            rows = self.extractor._run_sqlcmd(
                query=config["query"],
                headers=config["headers"],
            )
        except Exception as e:
            print(f"ERROR: {e}")
            return 0
        
        # Write to CSV
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=config["headers"])
            writer.writeheader()
            writer.writerows(rows)
        
        elapsed = time.time() - start_time
        print(f"{len(rows):,} rows in {elapsed:.1f}s ({len(rows)/elapsed:.0f}/s)")
        return len(rows)
    
    def extract_chunked(self, table_name: str, dry_run: bool = False) -> int:
        """Extract a large table in date-based chunks."""
        config = TABLE_CONFIGS.get(table_name)
        if not config or "query_template" not in config:
            print(f"  Unknown chunked table: {table_name}")
            return 0
        
        output_path = self.output_dir / f"{table_name}.csv"
        
        if dry_run:
            count = self.count_rows(table_name)
            print(f"  [DRY RUN] {table_name}: ~{count:,} rows -> {output_path.name}")
            return count
        
        print(f"  Extracting {table_name} (chunked)...")
        start_time = time.time()
        total_rows = 0
        
        # Get date range
        min_date, max_date = self.get_date_range()
        
        # Calculate chunk intervals (monthly chunks for large tables)
        from dateutil.relativedelta import relativedelta
        current_date = min_date
        
        # Open file and write header
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=config["headers"])
            writer.writeheader()
            
            chunk_num = 0
            while current_date < max_date:
                next_date = current_date + relativedelta(months=1)
                if next_date > max_date:
                    next_date = max_date + relativedelta(days=1)
                
                start_str = current_date.strftime("%Y-%m-%d")
                end_str = next_date.strftime("%Y-%m-%d")
                
                query = config["query_template"].format(
                    start_date=start_str,
                    end_date=end_str,
                )
                
                try:
                    rows = self.extractor._run_sqlcmd(
                        query=query,
                        headers=config["headers"],
                    )
                except Exception as e:
                    print(f"    Chunk {chunk_num} ({start_str}): ERROR - {e}")
                    current_date = next_date
                    chunk_num += 1
                    continue
                
                if rows:
                    writer.writerows(rows)
                    total_rows += len(rows)
                
                elapsed = time.time() - start_time
                rate = total_rows / elapsed if elapsed > 0 else 0
                print(f"    Chunk {chunk_num} ({start_str}): {len(rows):,} rows, total: {total_rows:,} ({rate:.0f}/s)")
                
                current_date = next_date
                chunk_num += 1
        
        elapsed = time.time() - start_time
        print(f"  Completed {table_name}: {total_rows:,} rows in {elapsed:.1f}s")
        return total_rows
    
    def extract_table(self, table_name: str, dry_run: bool = False) -> int:
        """Extract a single table (simple or chunked)."""
        config = TABLE_CONFIGS.get(table_name)
        if not config:
            print(f"  Unknown table: {table_name}")
            return 0
        
        if "query_template" in config:
            return self.extract_chunked(table_name, dry_run)
        else:
            return self.extract_simple(table_name, dry_run)
    
    def extract_all(self, tables: Optional[List[str]] = None, dry_run: bool = False) -> Dict[str, int]:
        """Extract all (or specified) tables."""
        if tables is None:
            tables = list(TABLE_CONFIGS.keys())
        
        results = {}
        total_start = time.time()
        
        print(f"\n{'='*70}")
        print("BULK FISHTALK EXTRACTION")
        print(f"{'='*70}")
        print(f"Output directory: {self.output_dir}")
        print(f"Tables to extract: {len(tables)}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print(f"{'='*70}\n")
        
        for i, table_name in enumerate(tables, 1):
            print(f"[{i}/{len(tables)}] {table_name}")
            row_count = self.extract_table(table_name, dry_run)
            results[table_name] = row_count
        
        total_elapsed = time.time() - total_start
        total_rows = sum(results.values())
        
        print(f"\n{'='*70}")
        print("EXTRACTION SUMMARY")
        print(f"{'='*70}")
        for table, count in results.items():
            print(f"  {table}: {count:,} rows")
        print(f"{'='*70}")
        print(f"Total rows: {total_rows:,}")
        print(f"Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} minutes)")
        if total_elapsed > 0:
            print(f"Average rate: {total_rows/total_elapsed:,.0f} rows/second")
        print(f"{'='*70}")
        
        return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bulk extract FishTalk data to CSV files for ETL migration"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="scripts/migration/data/extract/",
        help="Output directory for CSV files (default: scripts/migration/data/extract/)",
    )
    parser.add_argument(
        "--tables",
        type=str,
        help="Comma-separated list of tables to extract (default: all)",
    )
    parser.add_argument(
        "--sql-profile",
        type=str,
        default="fishtalk_readonly",
        help="SQL Server profile name (default: fishtalk_readonly)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be extracted without executing",
    )
    parser.add_argument(
        "--list-tables",
        action="store_true",
        help="List available tables and exit",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    
    if args.list_tables:
        print("\nAvailable tables:")
        for name, config in TABLE_CONFIGS.items():
            chunked = "chunked" if "query_template" in config else "simple"
            est = config.get("estimated_rows", 0)
            print(f"  {name}: ~{est:,} rows ({chunked})")
        return 0
    
    output_dir = PROJECT_ROOT / args.output
    
    tables = None
    if args.tables:
        tables = [t.strip() for t in args.tables.split(",")]
        # Validate tables
        invalid = [t for t in tables if t not in TABLE_CONFIGS]
        if invalid:
            print(f"Unknown tables: {invalid}")
            print(f"Available: {list(TABLE_CONFIGS.keys())}")
            return 1
    
    extractor = BulkExtractor(output_dir, profile=args.sql_profile)
    
    try:
        results = extractor.extract_all(tables=tables, dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n\nExtraction interrupted by user")
        return 1
    except Exception as e:
        print(f"\nExtraction failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
