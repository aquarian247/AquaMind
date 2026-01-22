#!/usr/bin/env python3
# flake8: noqa
"""ETL Loader module for reading pre-extracted FishTalk CSV data.

This module provides cached access to pre-extracted CSV files for the migration scripts.
It replaces live SQL queries with in-memory DataFrame operations.

Usage:
    from scripts.migration.tools.etl_loader import ETLDataLoader
    
    # Initialize with CSV directory
    loader = ETLDataLoader("scripts/migration/data/extract/")
    
    # Get data for specific populations
    status_values = loader.get_status_values_for_populations(population_ids)
    
    # Get environmental readings for containers
    daily_readings = loader.get_daily_readings_for_containers(container_ids, start_date, end_date)

Key features:
- Lazy loading: DataFrames loaded on first access
- Caching: Each CSV loaded only once per process
- Memory efficient: Large tables can be filtered before full load
- Thread-safe: Safe for use with multiprocessing
"""

from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Iterable
import functools

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class ETLDataLoader:
    """Cached loader for pre-extracted FishTalk CSV files."""
    
    # Class-level cache for DataFrames (shared across instances)
    _cache: Dict[str, Any] = {}
    
    def __init__(self, data_dir: str | Path | None = None, *, sqlite_path: str | Path | None = None):
        """Initialize the loader with the directory containing CSV files.
        
        Args:
            data_dir: Path to directory containing extracted CSV files
        """
        self.data_dir = Path(data_dir) if data_dir is not None else None
        if self.data_dir is not None and not self.data_dir.exists():
            raise FileNotFoundError(f"ETL data directory not found: {self.data_dir}")

        self.sqlite_path = Path(sqlite_path) if sqlite_path is not None else None
        if self.sqlite_path is not None and not self.sqlite_path.exists():
            raise FileNotFoundError(f"ETL sqlite index not found: {self.sqlite_path}")

        if self.data_dir is None and self.sqlite_path is None:
            raise ValueError("Provide data_dir or sqlite_path")

        self._sqlite_conn: Optional[sqlite3.Connection] = None
    
    def _get_csv_path(self, table_name: str) -> Path:
        """Get path to a CSV file."""
        if self.data_dir is None:
            raise ValueError("CSV data_dir not configured")
        path = self.data_dir / f"{table_name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")
        return path
    
    def _load_csv_dict(self, table_name: str) -> List[Dict[str, str]]:
        """Load CSV as list of dicts (memory efficient for small tables)."""
        cache_key = f"dict:{self.data_dir}:{table_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        path = self._get_csv_path(table_name)
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        self._cache[cache_key] = data
        return data
    
    def _load_csv_pandas(self, table_name: str) -> "pd.DataFrame":
        """Load CSV as pandas DataFrame (for large tables with filtering)."""
        if not HAS_PANDAS:
            raise ImportError("pandas required for DataFrame operations")
        
        cache_key = f"df:{self.data_dir}:{table_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        path = self._get_csv_path(table_name)
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        
        self._cache[cache_key] = df
        return df
    
    def _stream_csv(self, table_name: str) -> Generator[Dict[str, str], None, None]:
        """Stream CSV rows one at a time (for very large tables)."""
        path = self._get_csv_path(table_name)
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            yield from reader

    def _ensure_sqlite(self) -> sqlite3.Connection:
        if self.sqlite_path is None:
            raise ValueError("sqlite_path not configured")
        if self._sqlite_conn is None:
            self._sqlite_conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
            self._sqlite_conn.row_factory = sqlite3.Row
        return self._sqlite_conn

    @staticmethod
    def _chunked(values: Iterable[str], size: int) -> Generator[List[str], None, None]:
        batch: List[str] = []
        for value in values:
            batch.append(value)
            if len(batch) >= size:
                yield batch
                batch = []
        if batch:
            yield batch

    def _query_sqlite_readings(
        self,
        *,
        table_name: str,
        time_column: str,
        container_ids: Set[str],
        start_value: str | None,
        end_value: str | None,
    ) -> List[Dict[str, str]]:
        if not container_ids:
            return []
        conn = self._ensure_sqlite()
        results: List[Dict[str, str]] = []
        for chunk in self._chunked(sorted(container_ids), 500):
            placeholders = ",".join("?" for _ in chunk)
            conditions = [f"ContainerID IN ({placeholders})"]
            params: List[str] = list(chunk)
            if start_value:
                conditions.append(f"{time_column} >= ?")
                params.append(start_value)
            if end_value:
                conditions.append(f"{time_column} <= ?")
                params.append(end_value)
            sql = (
                f"SELECT ContainerID, SensorID, {time_column} AS {time_column}, Reading "
                f"FROM {table_name} WHERE {' AND '.join(conditions)}"
            )
            rows = conn.execute(sql, params).fetchall()
            results.extend(dict(row) for row in rows)
        return results
    
    # ====================
    # POPULATIONS
    # ====================
    
    def get_all_populations(self) -> List[Dict[str, str]]:
        """Get all population records."""
        return self._load_csv_dict("populations")
    
    def get_populations_by_ids(self, population_ids: Set[str]) -> List[Dict[str, str]]:
        """Get populations for specific IDs."""
        all_pops = self.get_all_populations()
        return [p for p in all_pops if p.get("PopulationID") in population_ids]
    
    def get_populations_by_project(self, project_number: str, input_year: str, running_number: str) -> List[Dict[str, str]]:
        """Get populations for a specific project key."""
        all_pops = self.get_all_populations()
        return [
            p for p in all_pops
            if (p.get("ProjectNumber") == project_number and
                p.get("InputYear") == input_year and
                p.get("RunningNumber") == running_number)
        ]
    
    def get_populations_by_container(self, container_id: str) -> List[Dict[str, str]]:
        """Get populations for a specific container."""
        all_pops = self.get_all_populations()
        return [p for p in all_pops if p.get("ContainerID") == container_id]
    
    # ====================
    # POPULATION STAGES
    # ====================
    
    def get_population_stages(self, population_ids: Optional[Set[str]] = None) -> List[Dict[str, str]]:
        """Get population stage assignments."""
        all_stages = self._load_csv_dict("population_stages")
        if population_ids is None:
            return all_stages
        return [s for s in all_stages if s.get("PopulationID") in population_ids]
    
    def get_production_stages(self) -> Dict[str, str]:
        """Get production stages as ID -> Name mapping."""
        stages = self._load_csv_dict("production_stages")
        return {s.get("StageID", ""): s.get("StageName", "") for s in stages}
    
    # ====================
    # CONTAINERS
    # ====================
    
    def get_all_containers(self) -> List[Dict[str, str]]:
        """Get all container records."""
        return self._load_csv_dict("containers")
    
    def get_containers_by_ids(self, container_ids: Set[str]) -> List[Dict[str, str]]:
        """Get containers for specific IDs."""
        all_containers = self.get_all_containers()
        return [c for c in all_containers if c.get("ContainerID") in container_ids]
    
    # ====================
    # ORG UNITS
    # ====================
    
    def get_all_org_units(self) -> List[Dict[str, str]]:
        """Get all organization unit records."""
        return self._load_csv_dict("org_units")
    
    # ====================
    # STATUS VALUES
    # ====================
    
    def get_status_values_for_populations(
        self,
        population_ids: Set[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, str]]:
        """Get status values for specific populations within date range.
        
        Uses pandas for efficient filtering of large dataset.
        """
        if HAS_PANDAS:
            df = self._load_csv_pandas("status_values")
            mask = df["PopulationID"].isin(population_ids)
            
            if start_date:
                mask &= df["StatusTime"] >= start_date.strftime("%Y-%m-%d")
            if end_date:
                mask &= df["StatusTime"] <= end_date.strftime("%Y-%m-%d")
            
            return df[mask].to_dict("records")
        else:
            # Fallback to streaming for large files
            results = []
            for row in self._stream_csv("status_values"):
                if row.get("PopulationID") not in population_ids:
                    continue
                status_time = row.get("StatusTime", "")
                if start_date and status_time < start_date.strftime("%Y-%m-%d"):
                    continue
                if end_date and status_time > end_date.strftime("%Y-%m-%d"):
                    continue
                results.append(row)
            return results
    
    def get_latest_status_for_population(self, population_id: str, before_time: Optional[datetime] = None) -> Optional[Dict[str, str]]:
        """Get the most recent status value for a population."""
        if HAS_PANDAS:
            df = self._load_csv_pandas("status_values")
            mask = df["PopulationID"] == population_id
            if before_time:
                mask &= df["StatusTime"] <= before_time.strftime("%Y-%m-%d %H:%M:%S")
            
            filtered = df[mask].sort_values("StatusTime", ascending=False)
            if len(filtered) > 0:
                return filtered.iloc[0].to_dict()
            return None
        else:
            # Fallback
            latest = None
            latest_time = ""
            for row in self._stream_csv("status_values"):
                if row.get("PopulationID") != population_id:
                    continue
                status_time = row.get("StatusTime", "")
                if before_time and status_time > before_time.strftime("%Y-%m-%d %H:%M:%S"):
                    continue
                if status_time > latest_time:
                    latest_time = status_time
                    latest = row
            return latest

    def get_status_snapshot_near_time(
        self,
        population_id: str,
        at_time: datetime,
    ) -> Optional[Dict[str, str]]:
        """Get nearest status snapshot (prefer before, else after)."""
        if HAS_PANDAS:
            df = self._load_csv_pandas("status_values")
            pop_df = df[df["PopulationID"] == population_id]
            if pop_df.empty:
                return None

            ts = at_time.strftime("%Y-%m-%d %H:%M:%S")
            before_df = pop_df[pop_df["StatusTime"] <= ts]
            if not before_df.empty:
                return before_df.sort_values("StatusTime", ascending=False).iloc[0].to_dict()

            after_df = pop_df[pop_df["StatusTime"] >= ts]
            if not after_df.empty:
                return after_df.sort_values("StatusTime", ascending=True).iloc[0].to_dict()
            return None

        # Streaming fallback
        latest_before = None
        latest_before_time = ""
        earliest_after = None
        earliest_after_time = ""
        ts = at_time.strftime("%Y-%m-%d %H:%M:%S")
        for row in self._stream_csv("status_values"):
            if row.get("PopulationID") != population_id:
                continue
            status_time = row.get("StatusTime", "")
            if not status_time:
                continue
            if status_time <= ts:
                if status_time > latest_before_time:
                    latest_before_time = status_time
                    latest_before = row
            else:
                if not earliest_after_time or status_time < earliest_after_time:
                    earliest_after_time = status_time
                    earliest_after = row

        return latest_before or earliest_after

    def get_first_nonzero_status_after(
        self,
        population_id: str,
        at_time: datetime,
    ) -> Optional[Dict[str, str]]:
        """Get the earliest status snapshot after time with non-zero count/biomass."""
        ts = at_time.strftime("%Y-%m-%d %H:%M:%S")
        if HAS_PANDAS:
            df = self._load_csv_pandas("status_values")
            pop_df = df[df["PopulationID"] == population_id]
            if pop_df.empty:
                return None
            after_df = pop_df[pop_df["StatusTime"] >= ts]
            if after_df.empty:
                return None
            counts = pd.to_numeric(after_df["CurrentCount"], errors="coerce")
            biomasses = pd.to_numeric(after_df["CurrentBiomassKg"], errors="coerce")
            mask = (counts > 0) | (biomasses > 0)
            if not mask.any():
                return None
            return after_df[mask].sort_values("StatusTime", ascending=True).iloc[0].to_dict()

        earliest_after = None
        earliest_after_time = ""
        for row in self._stream_csv("status_values"):
            if row.get("PopulationID") != population_id:
                continue
            status_time = row.get("StatusTime", "")
            if not status_time or status_time < ts:
                continue
            try:
                count_val = float(row.get("CurrentCount") or 0)
            except Exception:
                count_val = 0
            try:
                bio_val = float(row.get("CurrentBiomassKg") or 0)
            except Exception:
                bio_val = 0
            if count_val <= 0 and bio_val <= 0:
                continue
            if not earliest_after_time or status_time < earliest_after_time:
                earliest_after_time = status_time
                earliest_after = row

        return earliest_after
    
    # ====================
    # ENVIRONMENTAL READINGS
    # ====================
    
    def get_daily_readings_for_containers(
        self,
        container_ids: Set[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, str]]:
        """Get daily sensor readings for specific containers.
        
        These should be imported with is_manual=True.
        """
        if self.sqlite_path is not None:
            return self._query_sqlite_readings(
                table_name="daily_sensor_readings",
                time_column="ReadingDate",
                container_ids=container_ids,
                start_value=start_date.strftime("%Y-%m-%d") if start_date else None,
                end_value=end_date.strftime("%Y-%m-%d") if end_date else None,
            )
        if HAS_PANDAS:
            df = self._load_csv_pandas("daily_sensor_readings")
            mask = df["ContainerID"].isin(container_ids)
            
            if start_date:
                mask &= df["ReadingDate"] >= start_date.strftime("%Y-%m-%d")
            if end_date:
                mask &= df["ReadingDate"] <= end_date.strftime("%Y-%m-%d")
            
            return df[mask].to_dict("records")
        else:
            results = []
            for row in self._stream_csv("daily_sensor_readings"):
                if row.get("ContainerID") not in container_ids:
                    continue
                reading_date = row.get("ReadingDate", "")
                if start_date and reading_date < start_date.strftime("%Y-%m-%d"):
                    continue
                if end_date and reading_date > end_date.strftime("%Y-%m-%d"):
                    continue
                results.append(row)
            return results
    
    def get_time_readings_for_containers(
        self,
        container_ids: Set[str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, str]]:
        """Get time-series sensor readings for specific containers.
        
        These should be imported with is_manual=False.
        """
        if self.sqlite_path is not None:
            return self._query_sqlite_readings(
                table_name="time_sensor_readings",
                time_column="ReadingTime",
                container_ids=container_ids,
                start_value=start_time.strftime("%Y-%m-%d %H:%M:%S") if start_time else None,
                end_value=end_time.strftime("%Y-%m-%d %H:%M:%S") if end_time else None,
            )
        if HAS_PANDAS:
            df = self._load_csv_pandas("time_sensor_readings")
            mask = df["ContainerID"].isin(container_ids)
            
            if start_time:
                mask &= df["ReadingTime"] >= start_time.strftime("%Y-%m-%d %H:%M:%S")
            if end_time:
                mask &= df["ReadingTime"] <= end_time.strftime("%Y-%m-%d %H:%M:%S")
            
            return df[mask].to_dict("records")
        else:
            results = []
            for row in self._stream_csv("time_sensor_readings"):
                if row.get("ContainerID") not in container_ids:
                    continue
                reading_time = row.get("ReadingTime", "")
                if start_time and reading_time < start_time.strftime("%Y-%m-%d %H:%M:%S"):
                    continue
                if end_time and reading_time > end_time.strftime("%Y-%m-%d %H:%M:%S"):
                    continue
                results.append(row)
            return results
    
    # ====================
    # MORTALITY
    # ====================
    
    def get_mortality_actions_for_populations(
        self,
        population_ids: Set[str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, str]]:
        """Get mortality actions for specific populations."""
        all_actions = self._load_csv_dict("mortality_actions")
        
        results = []
        for row in all_actions:
            if row.get("PopulationID") not in population_ids:
                continue
            # CSV uses OperationStartTime column
            action_time = row.get("OperationStartTime", "")
            if start_time and action_time < start_time.strftime("%Y-%m-%d %H:%M:%S"):
                continue
            if end_time and action_time > end_time.strftime("%Y-%m-%d %H:%M:%S"):
                continue
            results.append(row)
        
        return results
    
    # ====================
    # FEEDING
    # ====================
    
    def get_feeding_actions_for_populations(
        self,
        population_ids: Set[str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, str]]:
        """Get feeding actions for specific populations."""
        all_actions = self._load_csv_dict("feeding_actions")
        
        results = []
        for row in all_actions:
            if row.get("PopulationID") not in population_ids:
                continue
            # CSV uses FeedingTime column
            action_time = row.get("FeedingTime", "")
            if start_time and action_time < start_time.strftime("%Y-%m-%d %H:%M:%S"):
                continue
            if end_time and action_time > end_time.strftime("%Y-%m-%d %H:%M:%S"):
                continue
            results.append(row)
        
        return results
    
    def get_hand_weights_for_feedings(self, feeding_ids: Set[str]) -> List[Dict[str, str]]:
        """Get hand weight samples for specific feeding IDs."""
        all_weights = self._load_csv_dict("feeding_hand_weights")
        return [w for w in all_weights if w.get("FeedingID") in feeding_ids]
    
    # ====================
    # TRANSFERS
    # ====================
    
    def get_transfer_operations(self) -> List[Dict[str, str]]:
        """Get all transfer operations (for StageTransitionEnvironmental inference)."""
        return self._load_csv_dict("transfer_operations")
    
    def get_transfer_operations_by_ids(self, operation_ids: Set[str]) -> List[Dict[str, str]]:
        """Get transfer operations by IDs."""
        all_ops = self.get_transfer_operations()
        return [o for o in all_ops if o.get("OperationID") in operation_ids]
    
    def get_transfer_edges_for_populations(self, population_ids: Set[str]) -> List[Dict[str, str]]:
        """Get transfer edges involving any of the specified populations."""
        all_edges = self._load_csv_dict("transfer_edges")
        return [
            e for e in all_edges
            if e.get("SourcePop") in population_ids or e.get("DestPop") in population_ids
        ]
    
    # ====================
    # UTILITY
    # ====================
    
    def clear_cache(self):
        """Clear the cached data (useful for memory management)."""
        self._cache.clear()
    
    def get_available_tables(self) -> List[str]:
        """List available CSV files."""
        if self.data_dir is None:
            return []
        return [f.stem for f in self.data_dir.glob("*.csv")]
    
    def get_row_count(self, table_name: str) -> int:
        """Get row count for a table without loading it fully."""
        path = self._get_csv_path(table_name)
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f) - 1  # Subtract header


# Convenience function for creating a global loader instance
_global_loader: Optional[ETLDataLoader] = None


def get_loader(data_dir: Optional[str | Path] = None) -> ETLDataLoader:
    """Get or create a global ETL data loader instance.
    
    Args:
        data_dir: Path to CSV directory (required on first call)
        
    Returns:
        ETLDataLoader instance
    """
    global _global_loader
    
    if _global_loader is None:
        if data_dir is None:
            raise ValueError("data_dir required on first call to get_loader()")
        _global_loader = ETLDataLoader(data_dir)
    
    return _global_loader
