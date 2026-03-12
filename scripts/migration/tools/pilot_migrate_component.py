#!/usr/bin/env python3
# flake8: noqa
"""Pilot migrate a stitched FishTalk population component into AquaMind.

This script supports two stitching approaches:
1. **SubTransfers-based (legacy)**: Use --chain-id with output from
   scripts/migration/legacy/tools/subtransfer_chain_stitching.py
2. **Project-based (legacy)**: Use --component-key with population_members.csv

SubTransfers-based stitching traces actual fish movements and produces
single-geography batches. Project-based stitching groups by cost center
and may produce multi-geography anomalies.

It is meant for a dry-run against aquamind_db_migr_dev only.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from itertools import groupby
from dataclasses import dataclass
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")

from scripts.migration.safety import (  # noqa: E402
    assert_default_db_is_migration_db,
    configure_migration_environment,
)

configure_migration_environment()

import django  # noqa: E402

django.setup()
assert_default_db_is_migration_db()

from django.db import transaction  # noqa: E402
from django.db.models import Count, Q  # noqa: E402

from apps.batch.models import (  # noqa: E402
    Batch,
    BatchTransferWorkflow,
    LifeCycleStage,
    Species,
    BatchCreationWorkflow,
    CreationAction,
)
from apps.batch.models.assignment import BatchContainerAssignment  # noqa: E402
from apps.broodstock.models import EggSupplier  # noqa: E402
from apps.infrastructure.models import (  # noqa: E402
    Area,
    AreaGroup,
    Container,
    ContainerType,
    FreshwaterStation,
    Geography,
    Hall,
)
from apps.migration_support.models import ExternalIdMap  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

from scripts.migration.extractors.base import (  # noqa: E402
    BaseExtractor,
    ExtractionContext,
)
from scripts.migration.history import save_with_history, get_or_create_with_history  # noqa: E402
from scripts.migration.tools.etl_loader import ETLDataLoader, HAS_PANDAS  # noqa: E402
from scripts.migration.tools.migration_profiles import (  # noqa: E402
    MIGRATION_PROFILE_NAMES,
    STAGE_SELECTION_FRONTIER,
    STAGE_SELECTION_LATEST_MEMBER,
    get_migration_profile,
)
from scripts.migration.tools.population_assignment_mapping import (  # noqa: E402
    ASSIGNMENT_SCOPED_SOURCE_MODEL,
    LEGACY_ASSIGNMENT_SOURCE_MODEL,
    build_component_population_identifier,
    extract_population_id,
    get_assignment_external_map,
    get_component_assignment_maps,
    upsert_assignment_external_maps,
)


class DataSource:
    """Unified data source abstraction for SQL or CSV data."""
    
    def __init__(self, csv_dir: str | None = None, sql_profile: str = "fishtalk_readonly"):
        self.use_csv = csv_dir is not None
        self.csv_dir = Path(csv_dir) if csv_dir else None
        if self.use_csv:
            self.loader = ETLDataLoader(csv_dir)
            self.extractor = None
        else:
            self.loader = None
            self.extractor = BaseExtractor(ExtractionContext(profile=sql_profile))
        # Cache latest non-zero status holder per source container id.
        self._latest_nonzero_holder_by_container: dict[str, tuple[str, datetime] | None] = {}
        self._container_latest_nonzero_holder_index: dict[str, tuple[str, datetime]] | None = None
    
    def get_global_latest_status_time(self) -> datetime | None:
        """Get the latest status time across all populations."""
        if self.use_csv:
            # Read from status_values CSV - get max StatusTime
            import pandas as pd
            df = self.loader._load_csv_pandas("status_values")
            max_time = df["StatusTime"].max()
            return parse_dt(max_time) if max_time else None
        else:
            rows = self.extractor._run_sqlcmd(
                query="SELECT TOP 1 StatusTime FROM dbo.PublicStatusValues ORDER BY StatusTime DESC",
                headers=["StatusTime"],
            )
            return parse_dt(rows[0].get("StatusTime", "")) if rows else None
    
    def get_latest_status_by_population(self, population_ids: list[str]) -> dict[str, datetime]:
        """Get latest status time for each population."""
        result = {}
        if self.use_csv:
            pop_set = set(population_ids)
            for pid in pop_set:
                status = self.loader.get_latest_status_for_population(pid)
                if status and status.get("StatusTime"):
                    dt = parse_dt(status["StatusTime"])
                    if dt:
                        result[pid] = dt
        else:
            pop_clause = ",".join(f"'{pid}'" for pid in population_ids)
            rows = self.extractor._run_sqlcmd(
                query=(
                    "SELECT PopulationID, MAX(StatusTime) AS MaxStatusTime "
                    "FROM dbo.PublicStatusValues "
                    f"WHERE PopulationID IN ({pop_clause}) "
                    "GROUP BY PopulationID"
                ),
                headers=["PopulationID", "MaxStatusTime"],
            )
            for row in rows:
                dt = parse_dt(row.get("MaxStatusTime", ""))
                if dt:
                    result[row["PopulationID"]] = dt
        return result
    
    def get_containers(self, container_ids: list[str]) -> list[dict]:
        """Get container data for specified IDs."""
        if self.use_csv:
            return self.loader.get_containers_by_ids(set(container_ids))
        else:
            in_clause = ",".join(f"'{cid}'" for cid in container_ids)
            return self.extractor._run_sqlcmd(
                query=(
                    "SELECT "
                    "c.ContainerID, "
                    "c.ContainerName, "
                    "c.OrgUnitID, "
                    "c.OfficialID, "
                    "CONVERT(varchar(32), cp.OverriddenVolumeM3) AS OverriddenVolumeM3 "
                    "FROM dbo.Containers c "
                    "OUTER APPLY ("
                    "  SELECT TOP 1 h.PhysicsID "
                    "  FROM dbo.ContainerPhysicsHistory h "
                    "  WHERE h.ContainerID = c.ContainerID "
                    "  ORDER BY "
                    "    CASE WHEN h.EndTime IS NULL THEN 0 ELSE 1 END, "
                    "    h.EndTime DESC, "
                    "    h.StartTime DESC"
                    ") ph "
                    "OUTER APPLY ("
                    "  SELECT MAX(CASE WHEN p.ParameterID = 6 THEN p.ParameterValue END) AS OverriddenVolumeM3 "
                    "  FROM dbo.ContainerPhysics p "
                    "  WHERE p.PhysicsID = ph.PhysicsID"
                    ") cp "
                    f"WHERE c.ContainerID IN ({in_clause})"
                ),
                headers=["ContainerID", "ContainerName", "OrgUnitID", "OfficialID", "OverriddenVolumeM3"],
            )
    
    def get_container_grouping(self, container_ids: list[str]) -> list[dict]:
        """Get container grouping/organization data."""
        if self.use_csv:
            try:
                return self.loader.get_grouped_organisation_by_container_ids(set(container_ids))
            except FileNotFoundError:
                # Container grouping not extracted - fall back to OrgUnit-based grouping
                return []
        else:
            in_clause = ",".join(f"'{cid}'" for cid in container_ids)
            return self.extractor._run_sqlcmd(
                query=(
                    "SELECT CONVERT(varchar(36), ContainerID) AS ContainerID, "
                    "Site, SiteGroup, Company, ProdStage, ContainerGroup, ContainerGroupID, StandName, StandID "
                    "FROM dbo.Ext_GroupedOrganisation_v2 "
                    f"WHERE ContainerID IN ({in_clause})"
                ),
                headers=[
                    "ContainerID", "Site", "SiteGroup", "Company", "ProdStage",
                    "ContainerGroup", "ContainerGroupID", "StandName", "StandID",
                ],
            )

    def get_input_counts(self, population_ids: list[str]) -> dict[str, float]:
        """Get InputCount per population from Ext_Inputs_v2."""
        if not population_ids:
            return {}
        if self.use_csv:
            return self.loader.get_input_counts_by_population(set(population_ids))
        in_clause = ",".join(f"'{pid}'" for pid in population_ids)
        rows = self.extractor._run_sqlcmd(
            query=(
                "SELECT CONVERT(varchar(36), PopulationID) AS PopulationID, "
                "ISNULL(CONVERT(varchar(32), InputCount), '0') AS InputCount "
                "FROM dbo.Ext_Inputs_v2 "
                f"WHERE PopulationID IN ({in_clause})"
            ),
            headers=["PopulationID", "InputCount"],
        )
        results: dict[str, float] = {}
        for row in rows:
            pop_id = row.get("PopulationID") or ""
            try:
                count = float(row.get("InputCount") or 0)
            except Exception:
                count = 0.0
            results[pop_id] = results.get(pop_id, 0.0) + count
        return results

    def get_input_supplier_ids(self, population_ids: list[str]) -> dict[str, set[str]]:
        """Get SupplierID set per population from Ext_Inputs_v2."""
        if not population_ids:
            return {}

        if self.use_csv:
            return self.loader.get_input_suppliers_by_population(set(population_ids))

        in_clause = ",".join(f"'{pid}'" for pid in population_ids)
        rows = self.extractor._run_sqlcmd(
            query=(
                "SELECT CONVERT(varchar(36), PopulationID) AS PopulationID, "
                "CONVERT(varchar(36), SupplierID) AS SupplierID "
                "FROM dbo.Ext_Inputs_v2 "
                f"WHERE PopulationID IN ({in_clause})"
            ),
            headers=["PopulationID", "SupplierID"],
        )

        results: dict[str, set[str]] = {}
        for row in rows:
            pop_id = (row.get("PopulationID") or "").strip()
            supplier_id = (row.get("SupplierID") or "").strip()
            if not pop_id or not supplier_id:
                continue
            results.setdefault(pop_id, set()).add(supplier_id)
        return results

    def get_input_rows(self, population_ids: list[str]) -> dict[str, list[dict]]:
        """Get Ext_Inputs_v2 rows keyed by PopulationID."""
        if not population_ids:
            return {}

        if self.use_csv:
            return self.loader.get_input_rows_by_population(set(population_ids))

        in_clause = ",".join(f"'{pid}'" for pid in population_ids)
        rows: list[dict] = []
        try:
            rows = self.extractor._run_sqlcmd(
                query=(
                    "SELECT CONVERT(varchar(36), PopulationID) AS PopulationID, "
                    "CONVERT(varchar(19), StartTime, 120) AS StartTime, "
                    "ISNULL(CONVERT(varchar(32), InputCount), '0') AS InputCount, "
                    "CONVERT(varchar(36), SupplierID) AS SupplierID, "
                    "CONVERT(varchar(36), DeliveryID) AS DeliveryID "
                    "FROM dbo.Ext_Inputs_v2 "
                    f"WHERE PopulationID IN ({in_clause})"
                ),
                headers=["PopulationID", "StartTime", "InputCount", "SupplierID", "DeliveryID"],
            )
        except Exception:
            try:
                rows = self.extractor._run_sqlcmd(
                    query=(
                        "SELECT CONVERT(varchar(36), PopulationID) AS PopulationID, "
                        "CONVERT(varchar(19), StartTime, 120) AS StartTime, "
                        "ISNULL(CONVERT(varchar(32), InputCount), '0') AS InputCount, "
                        "CONVERT(varchar(36), SupplierID) AS SupplierID, "
                        "'' AS DeliveryID "
                        "FROM dbo.Ext_Inputs_v2 "
                        f"WHERE PopulationID IN ({in_clause})"
                    ),
                    headers=["PopulationID", "StartTime", "InputCount", "SupplierID", "DeliveryID"],
                )
            except Exception:
                rows = self.extractor._run_sqlcmd(
                    query=(
                        "SELECT CONVERT(varchar(36), PopulationID) AS PopulationID, "
                        "'' AS StartTime, "
                        "ISNULL(CONVERT(varchar(32), InputCount), '0') AS InputCount, "
                        "CONVERT(varchar(36), SupplierID) AS SupplierID, "
                        "'' AS DeliveryID "
                        "FROM dbo.Ext_Inputs_v2 "
                        f"WHERE PopulationID IN ({in_clause})"
                    ),
                    headers=["PopulationID", "StartTime", "InputCount", "SupplierID", "DeliveryID"],
                )

        results: dict[str, list[dict]] = {}
        for row in rows:
            pop_id = (row.get("PopulationID") or "").strip()
            if not pop_id:
                continue
            results.setdefault(pop_id, []).append(row)
        return results

    def get_subtransfers(self, population_ids: set[str]) -> list[dict]:
        """Load SubTransfers rows involving the given population IDs."""
        if not population_ids:
            return []
        if self.use_csv:
            if not self.csv_dir:
                return []
            path = self.csv_dir / "sub_transfers.csv"
            if not path.exists():
                return []
            import csv

            rows: list[dict] = []
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    src_before = row.get("SourcePopBefore", "")
                    src_after = row.get("SourcePopAfter", "")
                    dst_before = row.get("DestPopBefore", "")
                    dst_after = row.get("DestPopAfter", "")
                    if (
                        src_before in population_ids
                        or src_after in population_ids
                        or dst_before in population_ids
                        or dst_after in population_ids
                    ):
                        rows.append(row)
            return rows

        in_clause = ",".join(f"'{pid}'" for pid in population_ids)
        return self.extractor._run_sqlcmd(
            query=(
                "SELECT "
                "CONVERT(varchar(36), st.SubTransferID) AS SubTransferID, "
                "CONVERT(varchar(36), st.OperationID) AS OperationID, "
                "CONVERT(varchar(36), st.SourcePopBefore) AS SourcePopBefore, "
                "CONVERT(varchar(36), st.SourcePopAfter) AS SourcePopAfter, "
                "CONVERT(varchar(36), st.DestPopBefore) AS DestPopBefore, "
                "CONVERT(varchar(36), st.DestPopAfter) AS DestPopAfter, "
                "CONVERT(varchar(32), st.ShareCountFwd) AS ShareCountFwd, "
                "CONVERT(varchar(32), st.ShareBiomFwd) AS ShareBiomFwd, "
                "CONVERT(varchar(19), o.StartTime, 120) AS OperationTime "
                "FROM dbo.SubTransfers st "
                "JOIN dbo.Operations o ON o.OperationID = st.OperationID "
                f"WHERE st.SourcePopBefore IN ({in_clause}) "
                f"OR st.SourcePopAfter IN ({in_clause}) "
                f"OR st.DestPopBefore IN ({in_clause}) "
                f"OR st.DestPopAfter IN ({in_clause}) "
                "ORDER BY o.StartTime ASC"
                ),
                headers=[
                    "SubTransferID",
                    "OperationID",
                    "SourcePopBefore",
                "SourcePopAfter",
                "DestPopBefore",
                "DestPopAfter",
                "ShareCountFwd",
                "ShareBiomFwd",
                "OperationTime",
                ],
            )

    def get_population_site_map(self, population_ids: set[str]) -> dict[str, str]:
        """Resolve population -> grouped-organisation site when available."""
        if not population_ids:
            return {}

        if self.use_csv:
            pop_rows = self.loader.get_populations_by_ids(population_ids)
            container_ids = {
                (row.get("ContainerID") or "").strip() for row in pop_rows if row.get("ContainerID")
            }
            if not container_ids:
                return {}
            try:
                grouped_rows = self.loader.get_grouped_organisation_by_container_ids(container_ids)
            except FileNotFoundError:
                return {}
            site_by_container = {
                (row.get("ContainerID") or "").strip(): (row.get("Site") or "").strip()
                for row in grouped_rows
            }
            resolved: dict[str, str] = {}
            for row in pop_rows:
                pop_id = (row.get("PopulationID") or "").strip()
                container_id = (row.get("ContainerID") or "").strip()
                if not pop_id or not container_id:
                    continue
                site = site_by_container.get(container_id)
                if site:
                    resolved[pop_id] = site
            return resolved

        resolved: dict[str, str] = {}
        for chunk in self._chunk_population_ids(population_ids):
            if not chunk:
                continue
            in_clause = ",".join(f"'{pid}'" for pid in chunk)
            rows = self.extractor._run_sqlcmd(
                query=(
                    "SELECT "
                    "CONVERT(varchar(36), p.PopulationID) AS PopulationID, "
                    "go.Site AS Site "
                    "FROM dbo.Populations p "
                    "LEFT JOIN dbo.Ext_GroupedOrganisation_v2 go ON go.ContainerID = p.ContainerID "
                    f"WHERE p.PopulationID IN ({in_clause})"
                ),
                headers=["PopulationID", "Site"],
            )
            for row in rows:
                pop_id = (row.get("PopulationID") or "").strip()
                site = (row.get("Site") or "").strip()
                if pop_id and site:
                    resolved[pop_id] = site
        return resolved

    def get_internal_delivery_links_for_input_populations(
        self, population_ids: set[str]
    ) -> dict[str, list[dict]]:
        """Return InternalDelivery sales/input operation links keyed by input population."""
        pop_set = {pid for pid in population_ids if pid}
        if not pop_set:
            return {}

        results: dict[str, list[dict]] = defaultdict(list)

        if self.use_csv:
            try:
                delivery_rows = self.loader._load_csv_dict("internal_delivery")
                action_rows = self.loader._load_csv_dict("internal_delivery_actions")
                operation_rows = self.loader._load_csv_dict("internal_delivery_operations")
            except FileNotFoundError:
                return {}

            populations_by_operation: dict[str, set[str]] = defaultdict(set)
            for row in action_rows:
                op_id = (row.get("OperationID") or "").strip()
                pop_id = (row.get("PopulationID") or "").strip()
                if op_id and pop_id:
                    populations_by_operation[op_id].add(pop_id)

            start_by_operation = {
                (row.get("OperationID") or "").strip(): (row.get("StartTime") or "").strip()
                for row in operation_rows
                if row.get("OperationID")
            }

            for row in delivery_rows:
                sales_op = (row.get("SalesOperationID") or "").strip()
                input_op = (row.get("InputOperationID") or "").strip()
                if not sales_op or not input_op:
                    continue
                input_pops = populations_by_operation.get(input_op, set())
                matched = input_pops & pop_set
                if not matched:
                    continue
                link = {
                    "SalesOperationID": sales_op,
                    "InputOperationID": input_op,
                    "InputSiteID": (row.get("InputSiteID") or "").strip(),
                    "PlannedActivityID": (row.get("PlannedActivityID") or "").strip(),
                    "SalesStartTime": start_by_operation.get(sales_op, ""),
                    "InputStartTime": start_by_operation.get(input_op, ""),
                    "sales_population_ids": set(populations_by_operation.get(sales_op, set())),
                    "input_population_ids": set(input_pops),
                }
                for pop_id in matched:
                    results[pop_id].append(link)
            return dict(results)

        try:
            pair_rows: list[dict] = []
            for chunk in self._chunk_population_ids(pop_set):
                if not chunk:
                    continue
                in_clause = ",".join(f"'{pid}'" for pid in chunk)
                pair_rows.extend(
                    self.extractor._run_sqlcmd(
                        query=(
                            "SELECT "
                            "CONVERT(varchar(36), id.SalesOperationID) AS SalesOperationID, "
                            "CONVERT(varchar(36), id.InputOperationID) AS InputOperationID, "
                            "CONVERT(varchar(36), id.InputSiteID) AS InputSiteID, "
                            "CONVERT(varchar(36), id.PlannedActivityID) AS PlannedActivityID, "
                            "CONVERT(varchar(19), so.StartTime, 120) AS SalesStartTime, "
                            "CONVERT(varchar(19), io.StartTime, 120) AS InputStartTime, "
                            "CONVERT(varchar(36), ia.PopulationID) AS InputPopulationID "
                            "FROM dbo.InternalDelivery id "
                            "JOIN dbo.Action ia ON ia.OperationID = id.InputOperationID "
                            "LEFT JOIN dbo.Operations so ON so.OperationID = id.SalesOperationID "
                            "LEFT JOIN dbo.Operations io ON io.OperationID = id.InputOperationID "
                            f"WHERE ia.PopulationID IN ({in_clause})"
                        ),
                        headers=[
                            "SalesOperationID",
                            "InputOperationID",
                            "InputSiteID",
                            "PlannedActivityID",
                            "SalesStartTime",
                            "InputStartTime",
                            "InputPopulationID",
                        ],
                    )
                )
            if not pair_rows:
                return {}

            pair_map: dict[
                tuple[str, str, str, str, str, str],
                set[str],
            ] = defaultdict(set)
            operation_ids: set[str] = set()
            for row in pair_rows:
                sales_op = (row.get("SalesOperationID") or "").strip()
                input_op = (row.get("InputOperationID") or "").strip()
                key = (
                    sales_op,
                    input_op,
                    (row.get("InputSiteID") or "").strip(),
                    (row.get("PlannedActivityID") or "").strip(),
                    (row.get("SalesStartTime") or "").strip(),
                    (row.get("InputStartTime") or "").strip(),
                )
                input_pop = (row.get("InputPopulationID") or "").strip()
                if input_pop:
                    pair_map[key].add(input_pop)
                if sales_op:
                    operation_ids.add(sales_op)
                if input_op:
                    operation_ids.add(input_op)

            populations_by_operation: dict[str, set[str]] = defaultdict(set)
            for op_chunk in self._chunk_population_ids(operation_ids, chunk_size=400):
                in_clause = ",".join(f"'{op_id}'" for op_id in op_chunk)
                action_rows = self.extractor._run_sqlcmd(
                    query=(
                        "SELECT "
                        "CONVERT(varchar(36), OperationID) AS OperationID, "
                        "CONVERT(varchar(36), PopulationID) AS PopulationID "
                        "FROM dbo.Action "
                        f"WHERE OperationID IN ({in_clause})"
                    ),
                    headers=["OperationID", "PopulationID"],
                )
                for action in action_rows:
                    op_id = (action.get("OperationID") or "").strip()
                    pop_id = (action.get("PopulationID") or "").strip()
                    if op_id and pop_id:
                        populations_by_operation[op_id].add(pop_id)

            for (
                sales_op,
                input_op,
                input_site_id,
                planned_activity_id,
                sales_start_time,
                input_start_time,
            ), input_pops in pair_map.items():
                link = {
                    "SalesOperationID": sales_op,
                    "InputOperationID": input_op,
                    "InputSiteID": input_site_id,
                    "PlannedActivityID": planned_activity_id,
                    "SalesStartTime": sales_start_time,
                    "InputStartTime": input_start_time,
                    "sales_population_ids": set(populations_by_operation.get(sales_op, set())),
                    "input_population_ids": set(populations_by_operation.get(input_op, set())),
                }
                matched = input_pops & pop_set
                for pop_id in matched:
                    results[pop_id].append(link)
        except Exception:
            return {}

        return dict(results)

    def get_removal_counts_by_population(self, population_ids: set[str]) -> dict[str, int]:
        """Return total known removals (mortality+culling+escapes) per population."""
        if not population_ids:
            return {}

        totals: defaultdict[str, int] = defaultdict(int)

        def add_rows(rows: list[dict], count_field: str) -> None:
            for row in rows:
                pop_id = (row.get("PopulationID") or "").strip()
                if not pop_id or pop_id not in population_ids:
                    continue
                raw = row.get(count_field)
                try:
                    value = int(round(float(raw or 0)))
                except Exception:
                    value = 0
                if value > 0:
                    totals[pop_id] += value

        if self.use_csv:
            add_rows(self.loader.get_mortality_actions_for_populations(population_ids), "MortalityCount")
            add_rows(self.loader.get_culling_actions_for_populations(population_ids), "CullingCount")
            add_rows(self.loader.get_escape_actions_for_populations(population_ids), "EscapeCount")
            return dict(totals)

        for chunk in self._chunk_population_ids(population_ids):
            in_clause = ",".join(f"'{pid}'" for pid in chunk)
            rows = self.extractor._run_sqlcmd(
                query=(
                    "SELECT CONVERT(varchar(36), a.PopulationID) AS PopulationID, "
                    "SUM(ISNULL(m.MortalityCount, 0)) AS TotalCount "
                    "FROM dbo.Mortality m "
                    "JOIN dbo.Action a ON a.ActionID = m.ActionID "
                    f"WHERE a.PopulationID IN ({in_clause}) "
                    "GROUP BY a.PopulationID"
                ),
                headers=["PopulationID", "TotalCount"],
            )
            add_rows(rows, "TotalCount")

            rows = self.extractor._run_sqlcmd(
                query=(
                    "SELECT CONVERT(varchar(36), a.PopulationID) AS PopulationID, "
                    "SUM(ISNULL(c.CullingCount, 0)) AS TotalCount "
                    "FROM dbo.Culling c "
                    "JOIN dbo.Action a ON a.ActionID = c.ActionID "
                    f"WHERE a.PopulationID IN ({in_clause}) "
                    "GROUP BY a.PopulationID"
                ),
                headers=["PopulationID", "TotalCount"],
            )
            add_rows(rows, "TotalCount")

            rows = self.extractor._run_sqlcmd(
                query=(
                    "SELECT CONVERT(varchar(36), a.PopulationID) AS PopulationID, "
                    "SUM(ISNULL(e.EscapeCount, 0)) AS TotalCount "
                    "FROM dbo.Escapes e "
                    "JOIN dbo.Action a ON a.ActionID = e.ActionID "
                    f"WHERE a.PopulationID IN ({in_clause}) "
                    "GROUP BY a.PopulationID"
                ),
                headers=["PopulationID", "TotalCount"],
            )
            add_rows(rows, "TotalCount")

        return dict(totals)

    def get_culling_counts_by_population(self, population_ids: set[str]) -> dict[str, int]:
        """Return total FishTalk culling count per population."""
        if not population_ids:
            return {}

        totals: defaultdict[str, int] = defaultdict(int)

        def add_rows(rows: list[dict], count_field: str) -> None:
            for row in rows:
                pop_id = (row.get("PopulationID") or "").strip()
                if not pop_id or pop_id not in population_ids:
                    continue
                raw = row.get(count_field)
                try:
                    value = int(round(float(raw or 0)))
                except Exception:
                    value = 0
                if value > 0:
                    totals[pop_id] += value

        if self.use_csv:
            add_rows(self.loader.get_culling_actions_for_populations(population_ids), "CullingCount")
            return dict(totals)

        for chunk in self._chunk_population_ids(population_ids):
            in_clause = ",".join(f"'{pid}'" for pid in chunk)
            rows = self.extractor._run_sqlcmd(
                query=(
                    "SELECT CONVERT(varchar(36), a.PopulationID) AS PopulationID, "
                    "SUM(ISNULL(c.CullingCount, 0)) AS TotalCount "
                    "FROM dbo.Culling c "
                    "JOIN dbo.Action a ON a.ActionID = c.ActionID "
                    f"WHERE a.PopulationID IN ({in_clause}) "
                    "GROUP BY a.PopulationID"
                ),
                headers=["PopulationID", "TotalCount"],
            )
            add_rows(rows, "TotalCount")

        return dict(totals)

    @staticmethod
    def _chunk_population_ids(population_ids: set[str], chunk_size: int = 500) -> list[list[str]]:
        ordered = sorted(pid for pid in population_ids if pid)
        return [ordered[i : i + chunk_size] for i in range(0, len(ordered), chunk_size)]

    def get_operational_activity_population_ids(
        self,
        population_ids: set[str],
        *,
        include_culling: bool = True,
    ) -> set[str]:
        """Return populations that have non-transfer operational events."""
        pop_set = {pid for pid in population_ids if pid}
        if not pop_set:
            return set()

        observed: set[str] = set()

        def collect(rows: list[dict]) -> None:
            for row in rows:
                pid = (row.get("PopulationID") or "").strip()
                if pid in pop_set:
                    observed.add(pid)

        if self.use_csv:
            csv_collectors = [
                self.loader.get_feeding_actions_for_populations,
                self.loader.get_mortality_actions_for_populations,
                self.loader.get_escape_actions_for_populations,
                self.loader.get_treatments_for_populations,
                self.loader.get_harvest_results_for_populations,
                self.loader.get_weight_samples_for_populations,
                self.loader.get_user_sample_sessions,
            ]
            if include_culling:
                csv_collectors.insert(2, self.loader.get_culling_actions_for_populations)
            for collector in csv_collectors:
                try:
                    collect(collector(pop_set))
                except FileNotFoundError:
                    continue
            try:
                lice_rows, _, _ = self.loader.get_lice_samples_for_populations(pop_set)
                collect(lice_rows)
            except FileNotFoundError:
                pass
            return observed

        def collect_sql_direct(table: str, column: str, extra_where: str | None = None) -> None:
            for chunk in self._chunk_population_ids(pop_set):
                in_clause = ",".join(f"'{pid}'" for pid in chunk)
                where_parts = [f"{column} IN ({in_clause})"]
                if extra_where:
                    where_parts.append(extra_where)
                rows = self.extractor._run_sqlcmd(
                    query=(
                        "SELECT DISTINCT "
                        f"CONVERT(varchar(36), {column}) AS PopulationID "
                        f"FROM {table} "
                        f"WHERE {' AND '.join(where_parts)}"
                    ),
                    headers=["PopulationID"],
                )
                collect(rows)

        def collect_sql_action(table: str, alias: str, extra_where: str | None = None) -> None:
            for chunk in self._chunk_population_ids(pop_set):
                in_clause = ",".join(f"'{pid}'" for pid in chunk)
                where_parts = [f"a.PopulationID IN ({in_clause})"]
                if extra_where:
                    where_parts.append(extra_where)
                rows = self.extractor._run_sqlcmd(
                    query=(
                        "SELECT DISTINCT "
                        "CONVERT(varchar(36), a.PopulationID) AS PopulationID "
                        f"FROM {table} {alias} "
                        f"JOIN dbo.Action a ON a.ActionID = {alias}.ActionID "
                        f"WHERE {' AND '.join(where_parts)}"
                    ),
                    headers=["PopulationID"],
                )
                collect(rows)

        collect_sql_action("dbo.Feeding", "f")
        collect_sql_action("dbo.Mortality", "m")
        if include_culling:
            collect_sql_action("dbo.Culling", "c")
        collect_sql_action("dbo.Escapes", "e")
        collect_sql_action("dbo.Treatment", "t")
        collect_sql_action("dbo.HarvestResult", "h")
        collect_sql_action("dbo.UserSample", "us")
        collect_sql_direct("dbo.PublicLiceSamples", "PopulationID")
        try:
            collect_sql_direct("dbo.Ext_WeightSamples_v2", "PopulationID", "OperationType = 10")
        except Exception:
            collect_sql_direct("dbo.PublicWeightSamples", "PopulationID")
        return observed
    
    def get_org_units(self, org_unit_ids: list[str]) -> list[dict]:
        """Get organization unit data."""
        if self.use_csv:
            all_org_units = self.loader.get_all_org_units()
            id_set = set(org_unit_ids)
            return [o for o in all_org_units if o.get("OrgUnitID") in id_set]
        else:
            in_clause = ",".join(f"'{oid}'" for oid in org_unit_ids)
            return self.extractor._run_sqlcmd(
                query=(
                    "SELECT ou.OrgUnitID, ou.Name, l.Latitude, l.Longitude "
                    "FROM dbo.OrganisationUnit ou "
                    "LEFT JOIN dbo.Locations l ON l.LocationID = ou.LocationID "
                    f"WHERE ou.OrgUnitID IN ({in_clause})"
                ),
                headers=["OrgUnitID", "Name", "Latitude", "Longitude"],
            )
    
    def get_status_snapshot(self, population_id: str, at_time: datetime) -> dict | None:
        """Get population status snapshot near a given time."""
        if self.use_csv:
            snapshot = self.loader.get_status_snapshot_near_time(population_id, at_time)
            if snapshot and self._has_nonzero_status(snapshot):
                return snapshot
            fallback = self.loader.get_first_nonzero_status_after(population_id, at_time)
            return fallback or snapshot
        else:
            ts = at_time.strftime("%Y-%m-%d %H:%M:%S")
            rows = self.extractor._run_sqlcmd(
                query=(
                    "SELECT TOP 1 StatusTime, CurrentCount, CurrentBiomassKg "
                    "FROM dbo.PublicStatusValues "
                    f"WHERE PopulationID = '{population_id}' AND StatusTime <= '{ts}' "
                    "ORDER BY "
                    "StatusTime DESC, "
                    "CASE WHEN ISNULL(CurrentCount, 0) > 0 OR ISNULL(CurrentBiomassKg, 0) > 0 THEN 1 ELSE 0 END DESC, "
                    "CurrentCount DESC, "
                    "CurrentBiomassKg DESC"
                ),
                headers=["StatusTime", "CurrentCount", "CurrentBiomassKg"],
            )
            if not rows:
                # Try future snapshot
                rows = self.extractor._run_sqlcmd(
                    query=(
                        "SELECT TOP 1 StatusTime, CurrentCount, CurrentBiomassKg "
                        "FROM dbo.PublicStatusValues "
                        f"WHERE PopulationID = '{population_id}' AND StatusTime >= '{ts}' "
                    "ORDER BY "
                    "StatusTime ASC, "
                    "CASE WHEN ISNULL(CurrentCount, 0) > 0 OR ISNULL(CurrentBiomassKg, 0) > 0 THEN 1 ELSE 0 END DESC, "
                    "CurrentCount DESC, "
                    "CurrentBiomassKg DESC"
                    ),
                    headers=["StatusTime", "CurrentCount", "CurrentBiomassKg"],
                )
            return rows[0] if rows else None

    def get_status_snapshot_exact_time(self, population_id: str, at_time: datetime) -> dict | None:
        """Get status snapshot exactly at the requested time (if present)."""
        ts = at_time.strftime("%Y-%m-%d %H:%M:%S")
        if self.use_csv:
            if HAS_PANDAS:
                df = self.loader._load_csv_pandas("status_values")
                exact_df = df[(df["PopulationID"] == population_id) & (df["StatusTime"] == ts)]
                if exact_df.empty:
                    return None
                return self.loader._pick_best_status_row_df(exact_df, time_ascending=False)

            best_row = None
            for row in self.loader._stream_csv("status_values"):
                if row.get("PopulationID") != population_id:
                    continue
                if (row.get("StatusTime") or "") != ts:
                    continue
                if best_row is None or self.loader._prefer_status_row(row, best_row):
                    best_row = row
            return best_row

        rows = self.extractor._run_sqlcmd(
            query=(
                "SELECT TOP 1 StatusTime, CurrentCount, CurrentBiomassKg "
                "FROM dbo.PublicStatusValues "
                f"WHERE PopulationID = '{population_id}' AND StatusTime = '{ts}' "
                "ORDER BY "
                "CASE WHEN ISNULL(CurrentCount, 0) > 0 OR ISNULL(CurrentBiomassKg, 0) > 0 THEN 1 ELSE 0 END DESC, "
                "CurrentCount DESC, "
                "CurrentBiomassKg DESC"
            ),
            headers=["StatusTime", "CurrentCount", "CurrentBiomassKg"],
        )
        return rows[0] if rows else None

    def _build_container_latest_nonzero_holder_index_csv(self) -> dict[str, tuple[str, datetime]]:
        """Build container -> latest non-zero holder index for CSV mode."""
        if self._container_latest_nonzero_holder_index is not None:
            return self._container_latest_nonzero_holder_index

        index: dict[str, tuple[str, datetime]] = {}
        if not HAS_PANDAS:
            self._container_latest_nonzero_holder_index = index
            return index

        try:
            import pandas as pd

            populations_df = self.loader._load_csv_pandas("populations")[["PopulationID", "ContainerID"]]
            status_df = self.loader._load_csv_pandas("status_values")[
                ["PopulationID", "StatusTime", "CurrentCount", "CurrentBiomassKg"]
            ]
            status_df = status_df[status_df["StatusTime"] != ""]
            if status_df.empty:
                self._container_latest_nonzero_holder_index = index
                return index

            counts = pd.to_numeric(status_df["CurrentCount"], errors="coerce").fillna(0)
            biomass = pd.to_numeric(status_df["CurrentBiomassKg"], errors="coerce").fillna(0)
            nonzero_df = status_df[(counts > 0) | (biomass > 0)]
            if nonzero_df.empty:
                self._container_latest_nonzero_holder_index = index
                return index

            latest_by_population = (
                nonzero_df.sort_values("StatusTime")
                .groupby("PopulationID", as_index=False)
                .tail(1)[["PopulationID", "StatusTime"]]
            )
            merged = latest_by_population.merge(populations_df, on="PopulationID", how="left")
            merged = merged[merged["ContainerID"] != ""]
            if merged.empty:
                self._container_latest_nonzero_holder_index = index
                return index

            latest_by_container = (
                merged.sort_values("StatusTime")
                .groupby("ContainerID", as_index=False)
                .tail(1)[["ContainerID", "PopulationID", "StatusTime"]]
            )
            for row in latest_by_container.to_dict("records"):
                container_id = (row.get("ContainerID") or "").strip()
                pop_id = (row.get("PopulationID") or "").strip()
                status_time = parse_dt(row.get("StatusTime") or "")
                if container_id and pop_id and status_time:
                    index[container_id] = (pop_id, status_time)
        except Exception as exc:
            print(f"Warning: failed to build CSV latest-holder index: {exc}")
            index = {}

        self._container_latest_nonzero_holder_index = index
        return index

    def get_latest_nonzero_status_holder_for_container(
        self,
        container_id: str,
    ) -> tuple[str, datetime] | None:
        """Return latest non-zero status holder for a source container.

        Returns:
            tuple(population_id, status_time) when evidence exists, else None.
        """
        key = (container_id or "").strip()
        if not key:
            return None
        if key in self._latest_nonzero_holder_by_container:
            return self._latest_nonzero_holder_by_container[key]

        holder: tuple[str, datetime] | None = None

        if self.use_csv:
            index = self._build_container_latest_nonzero_holder_index_csv()
            holder = index.get(key)
        else:
            rows = self.extractor._run_sqlcmd(
                query=(
                    "SELECT TOP 1 "
                    "CONVERT(varchar(36), p.PopulationID) AS PopulationID, "
                    "CONVERT(varchar(19), sv.StatusTime, 120) AS StatusTime "
                    "FROM dbo.Populations p "
                    "JOIN dbo.PublicStatusValues sv ON sv.PopulationID = p.PopulationID "
                    f"WHERE p.ContainerID = '{key}' "
                    "AND (ISNULL(sv.CurrentCount, 0) > 0 OR ISNULL(sv.CurrentBiomassKg, 0) > 0) "
                    "ORDER BY sv.StatusTime DESC"
                ),
                headers=["PopulationID", "StatusTime"],
            )
            if rows:
                pop_id = (rows[0].get("PopulationID") or "").strip()
                status_time = parse_dt(rows[0].get("StatusTime") or "")
                if pop_id and status_time:
                    holder = (pop_id, status_time)

        self._latest_nonzero_holder_by_container[key] = holder
        return holder

    @staticmethod
    def _has_nonzero_status(snapshot: dict) -> bool:
        try:
            count = float(snapshot.get("CurrentCount") or 0)
        except Exception:
            count = 0
        try:
            biomass = float(snapshot.get("CurrentBiomassKg") or 0)
        except Exception:
            biomass = 0
        return count > 0 or biomass > 0

User = get_user_model()


REPORT_DIR_DEFAULT = PROJECT_ROOT / "scripts" / "migration" / "output" / "population_stitching"


SEA_STAGE_MARKERS = ("ONGROW", "GROWER", "GRILSE")
SITE_CODE_RE = re.compile(r"\b([A-Za-z]+[0-9]{1,3})\b")
FAROE_SITEGROUPS = {"WEST", "NORTH", "SOUTH"}
SCOTLAND_SITES_FRESHWATER_ARCHIVE = {
    "BRS1 LANGASS",
    "BUCKIEBURN SMOLT UNIT",
    "DUNBLANE LOCH",
    "HO HATCHERY",
    "HSU",
    "FW11 BARVAS",
    "FW12 AMHUINNSUIDHE",
    "FW14 HARRIS LOCHS",
    "FW22 RUSSEL BURN",
    "FW23 LOCH DAMPH SOUTH",
    "LANGASS OLD TO SUMMER 15",
    "LOCH GEIREAN",
    "LOCH TORMASAD",
    "TULLICH",
}
SCOTLAND_SITES_FRESHWATER = {
    "FW13 GEOCRAB",
    "FW21 COULDORAN",
    "FW22 APPLECROSS",
    "FW24 KINLOCHMOIDART",
}
SCOTLAND_SITES_BROODSTOCK = {
    "BRS2 LANGASS",
    "BRS3 GEOCRAB",
}
FAROE_SITES_LAND = {
    "S03 NORÐTOFTIR",
    "S04 HÚSAR",
    "S08 GJÓGV",
    "S10 SVÍNOY",
    "S16 GLYVRADALUR",
    "S21 VIÐAREIÐI",
    "S24 STROND",
}
FAROE_SITES_DROPPED_H = {
    "H01 SVÍNOY",
    "H125 GLYVRAR",
}
FAROE_SITES_LIVFISKUR = {
    "L01 VIÐ ÁIR",
    "L02 SKOPUN",
}

def stage_bucket(stage_name: str) -> str | None:
    if not stage_name:
        return None
    upper = stage_name.upper()
    if any(marker in upper for marker in SEA_STAGE_MARKERS):
        return "sea"
    if "SMOLT" in upper or "PARR" in upper or "FRY" in upper or "ALEVIN" in upper or "EGG" in upper:
        return "freshwater"
    return None


def parse_site_code(site_name: str | None) -> str:
    label = normalize_label(site_name)
    if not label:
        return ""
    match = SITE_CODE_RE.search(label)
    return match.group(1).upper() if match else ""


def infer_geography_from_site_code(site_name: str | None) -> tuple[str, str]:
    code = parse_site_code(site_name)
    if not code:
        return "", ""
    match = re.match(r"^([A-Z]+)(\d{1,3})$", code)
    if not match:
        return "", ""
    prefix, digits = match.groups()
    if prefix == "A":
        return "Faroe Islands", "SITECODE_A"
    if prefix in {"L", "H"}:
        return "Faroe Islands", f"SITECODE_{prefix}"
    if prefix == "S":
        if len(digits) <= 2:
            return "Faroe Islands", "SITECODE_S_FAROE"
        return "Scotland", "SITECODE_S_SCOTLAND"
    if prefix in {"N", "FW", "BRS"}:
        return "Scotland", f"SITECODE_{prefix}"
    return "", ""


def normalize_label(value: str | None) -> str:
    if not value:
        return ""
    raw = " ".join(value.split()).strip()
    upper = raw.upper()
    if upper.startswith("FT "):
        raw = raw[3:].strip()
    elif upper.startswith("FT-"):
        raw = raw[3:].strip()
    if upper.endswith(" FW"):
        raw = raw[:-3].strip()
    if upper.endswith(" SEA"):
        raw = raw[:-4].strip()
    return raw


def normalize_key(value: str | None) -> str:
    return normalize_label(value).upper()


def resolve_site_grouping(site: str | None, site_group: str | None) -> tuple[str, str]:
    site_group_key = normalize_key(site_group)
    site_key = normalize_key(site)
    if site_group_key in FAROE_SITEGROUPS:
        return "Faroe Islands", f"SITEGROUP_{site_group_key}"
    if site_group_key:
        return "Scotland", f"SITEGROUP_{site_group_key}"
    if site_key in SCOTLAND_SITES_FRESHWATER_ARCHIVE:
        return "Scotland", "SCOTLAND_FRESHWATER_ARCHIVE"
    if site_key in SCOTLAND_SITES_FRESHWATER:
        return "Scotland", "SCOTLAND_FRESHWATER"
    if site_key in SCOTLAND_SITES_BROODSTOCK:
        return "Scotland", "SCOTLAND_BROODSTOCK"
    if site_key in FAROE_SITES_LAND:
        return "Faroe Islands", "FAROE_LAND"
    if site_key in FAROE_SITES_DROPPED_H:
        return "Faroe Islands", "FAROE_DROPPED_H"
    if site_key in FAROE_SITES_LIVFISKUR:
        return "Faroe Islands", "FAROE_LIVFISKUR"
    geo_name, reason = infer_geography_from_site_code(site)
    if geo_name:
        return geo_name, reason
    return "", ""


def bucket_from_prod_stage(prod_stage: str | None) -> str | None:
    upper = normalize_key(prod_stage)
    if not upper:
        return None
    if "MARINE" in upper or "SEA" in upper:
        return "sea"
    if any(token in upper for token in ("HATCH", "FRESH", "SMOLT", "PARR", "FRY", "ALEVIN", "EGG", "BROOD")):
        return "freshwater"
    return None


def infer_bucket_from_grouping(site: str | None, prod_stage: str | None) -> str | None:
    """Infer infra bucket from grouped-organisation signals.

    Priority:
    1) explicit production stage,
    2) curated site lists,
    3) strict site-code guard (`A*` is always marine area).
    """
    if is_dropped_h_site(site):
        return None

    explicit = bucket_from_prod_stage(prod_stage)
    if explicit:
        return explicit

    site_key = normalize_key(site)
    if (
        site_key in FAROE_SITES_LAND
        or site_key in FAROE_SITES_LIVFISKUR
        or site_key in SCOTLAND_SITES_FRESHWATER_ARCHIVE
        or site_key in SCOTLAND_SITES_FRESHWATER
        or site_key in SCOTLAND_SITES_BROODSTOCK
    ):
        return "freshwater"

    site_code = parse_site_code(site)
    if site_code.startswith("A") or site_code.startswith("N"):
        return "sea"
    if site_code.startswith("S"):
        match = re.match(r"^S([0-9]{1,3})$", site_code)
        if match:
            return "freshwater" if len(match.group(1)) <= 2 else "sea"
    if site_code.startswith("L"):
        return "freshwater"
    if site_code.startswith("FW") or site_code.startswith("BRS"):
        return "freshwater"
    return None


def is_dropped_h_site(site_name: str | None) -> bool:
    site_key = normalize_key(site_name)
    if site_key in FAROE_SITES_DROPPED_H:
        return True
    site_code = parse_site_code(site_name)
    return site_code.startswith("H")


def infer_station_type(site_name: str | None) -> str:
    site_code = parse_site_code(site_name)
    if site_code.startswith("L") or site_code.startswith("BRS"):
        return "BROODSTOCK"
    return "FRESHWATER"


def normalize_area_group(site_group: str | None) -> str:
    return normalize_label(site_group)


def hall_label_from_group(group_name: str | None) -> str:
    return normalize_label(group_name)


def hall_label_from_official(official_id: str | None) -> str:
    if not official_id:
        return ""
    prefix = official_id.split(";")[0].strip()
    return hall_label_from_group(prefix)


def fishtalk_stage_to_aquamind(stage_name: str) -> str | None:
    upper = (stage_name or "").upper()
    if any(token in upper for token in ("EGG", "ALEVIN", "SAC")):
        return "Egg&Alevin"
    if "FRY" in upper:
        return "Fry"
    if "PARR" in upper:
        return "Parr"
    if "SMOLT" in upper and ("POST" in upper or "LARGE" in upper):
        return "Post-Smolt"
    if "SMOLT" in upper:
        return "Smolt"
    if any(token in upper for token in ("ONGROW", "GROWER", "GRILSE")):
        return "Adult"
    return None


STAGE_ORDER = ["Egg&Alevin", "Fry", "Parr", "Smolt", "Post-Smolt", "Adult"]
STAGE_INDEX = {name: idx for idx, name in enumerate(STAGE_ORDER)}

S24_HALL_STAGE_MAP = {
    "A HØLL": "Egg&Alevin",
    "B HØLL": "Fry",
    "C HØLL": "Parr",
    "D HØLL": "Parr",
    "E HØLL": "Smolt",
    "F HØLL": "Smolt",
    "G HØLL": "Post-Smolt",
    "H HØLL": "Post-Smolt",
    "I HØLL": "Post-Smolt",
    "J HØLL": "Post-Smolt",
}

S03_HALL_STAGE_MAP = {
    "KLEKING": "Egg&Alevin",
    "5 M HØLL": "Fry",
    "11 HØLL A": "Smolt",
    "11 HØLL B": "Smolt",
    "18 HØLL A": "Post-Smolt",
    "18 HØLL B": "Post-Smolt",
    "800 HØLL": "Parr",
    "900 HØLL": "Parr",
}

S08_HALL_STAGE_MAP = {
    "KLEKING": "Egg&Alevin",
    "STARTFÓÐRING": "Fry",
    "T-HØLL": "Post-Smolt",
}

S16_HALL_STAGE_MAP = {
    "A HØLL": "Egg&Alevin",
    "B HØLL": "Fry",
    "C HØLL": "Parr",
    "D HØLL": "Smolt",
    "E1 HØLL": "Post-Smolt",
    "E2 HØLL": "Post-Smolt",
    "KLEKIHØLL": "Egg&Alevin",
    "STARTFÓÐRINGSHØLL": "Fry",
}

S21_HALL_STAGE_MAP = {
    "5M": "Fry",
    # S21 operational flow moves 5M fry into A/BA/BB as parr.
    "A": "Parr",
    "BA": "Parr",
    "BB": "Parr",
    "C": "Smolt",
    "D": "Smolt",
    "E": "Post-Smolt",
    "F": "Post-Smolt",
    "ROGN": "Egg&Alevin",
}

HALL_STAGE_PRIORITY_SITES = {
    "S24 STROND",
    "S03 NORÐTOFTIR",
    "S08 GJÓGV",
    "S16 GLYVRADALUR",
    "S21 VIÐAREIÐI",
    "FW22 APPLECROSS",
}

SITE_STAGE_FALLBACK_MAP = {
    # S04 cohorts can arrive without hall metadata in grouped organisation.
    # Token evidence across S04 hatchery members is overwhelmingly Fry, so we
    # use this as the deterministic fallback when hall-based resolution is
    # unavailable.
    "S04 HÚSAR": "Fry",
}

FW22_APPLECROSS_HALL_STAGE_MAP = {
    "A1": "Egg&Alevin",
    "A2": "Egg&Alevin",
    "B1": "Fry",
    "B2": "Fry",
    "C1": "Parr",
    "C2": "Parr",
    "D1": "Smolt",
    "D2": "Smolt",
    "E1": "Post-Smolt",
    "E2": "Post-Smolt",
}


def stage_from_hall(site: str | None, container_group: str | None) -> str | None:
    site_key = normalize_key(site)
    hall_key = normalize_key(container_group)
    if site_key == "S24 STROND" and hall_key in S24_HALL_STAGE_MAP:
        return S24_HALL_STAGE_MAP[hall_key]
    if site_key == "S03 NORÐTOFTIR" and hall_key in S03_HALL_STAGE_MAP:
        return S03_HALL_STAGE_MAP[hall_key]
    if site_key == "S08 GJÓGV" and hall_key in S08_HALL_STAGE_MAP:
        return S08_HALL_STAGE_MAP[hall_key]
    if site_key == "S16 GLYVRADALUR" and hall_key in S16_HALL_STAGE_MAP:
        return S16_HALL_STAGE_MAP[hall_key]
    if site_key == "S21 VIÐAREIÐI" and hall_key in S21_HALL_STAGE_MAP:
        return S21_HALL_STAGE_MAP[hall_key]
    if site_key == "FW22 APPLECROSS" and hall_key in FW22_APPLECROSS_HALL_STAGE_MAP:
        return FW22_APPLECROSS_HALL_STAGE_MAP[hall_key]
    return None


def extract_station_code(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"\bS[-\s]?(\d{2})\b", text.upper())
    if not match:
        return None
    return f"S{match.group(1)}"


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_decimal(value: str | None) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def resolve_container_volume_m3(container_row: dict | None) -> Decimal:
    if not container_row:
        return Decimal("0.00")
    raw_value = container_row.get("OverriddenVolumeM3")
    if raw_value in (None, ""):
        return Decimal("0.00")
    try:
        volume = Decimal(str(raw_value)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")
    if volume <= 0:
        return Decimal("0.00")
    return volume


def clamp_decimal(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    if value < low:
        return low
    if value > high:
        return high
    return value


def build_conserved_population_counts(
    members: list["ComponentMember"],
    data_source: DataSource,
    stage_by_pop: dict[str, str | None],
) -> tuple[dict[str, int], set[str]]:
    """Build population counts using SubTransfers propagation (conservation-based).

    Returns conserved counts and a set of populations superseded by same-stage transfers.
    """
    population_ids = {m.population_id for m in members if m.population_id}
    if not population_ids:
        return {}, set()

    input_counts = data_source.get_input_counts(list(population_ids))
    sub_transfers = data_source.get_subtransfers(population_ids)
    if not sub_transfers:
        return {}, set()

    member_by_id = {m.population_id: m for m in members}

    def row_time(row: dict) -> datetime:
        return parse_dt(row.get("OperationTime") or "") or datetime.min

    sub_transfers.sort(
        key=lambda r: (
            row_time(r),
            (r.get("OperationID") or ""),
            r.get("SubTransferID", ""),
        )
    )

    counts_at_start: dict[str, Decimal] = {}
    current_counts: dict[str, Decimal] = {}
    status_cache: dict[str, Decimal] = {}

    def seed_population(pop_id: str) -> Decimal:
        if pop_id in counts_at_start:
            return counts_at_start[pop_id]

        if pop_id in input_counts:
            count = Decimal(str(input_counts.get(pop_id) or 0))
            counts_at_start[pop_id] = count
            current_counts[pop_id] = count
            return count

        member = member_by_id.get(pop_id)
        if not member:
            # Keep zero-valued placeholders for intermediary populations so
            # SubTransfers chains can continue propagating counts back into
            # in-component destinations.
            count = Decimal("0")
            counts_at_start[pop_id] = count
            current_counts[pop_id] = count
            return count
        if pop_id not in status_cache:
            snapshot = data_source.get_status_snapshot(pop_id, member.start_time)
            count = Decimal("0")
            if snapshot:
                try:
                    count = Decimal(str(snapshot.get("CurrentCount") or 0))
                except Exception:
                    count = Decimal("0")
            status_cache[pop_id] = count
        count = status_cache[pop_id]
        counts_at_start[pop_id] = count
        current_counts[pop_id] = count
        return count

    superseded_same_stage: set[str] = set()
    for row in sub_transfers:
        src_before = (row.get("SourcePopBefore") or "").strip()
        src_after = (row.get("SourcePopAfter") or "").strip()
        dst_before = (row.get("DestPopBefore") or "").strip()
        dst_after = (row.get("DestPopAfter") or "").strip()

        stage_src = stage_by_pop.get(src_before)
        stage_src_after = stage_by_pop.get(src_after)
        stage_dst_after = stage_by_pop.get(dst_after)
        if src_before and stage_src:
            if src_after and stage_src_after and stage_src_after == stage_src:
                superseded_same_stage.add(src_before)
            if dst_after and stage_dst_after and stage_dst_after == stage_src:
                superseded_same_stage.add(src_before)

        stage_dst_before = stage_by_pop.get(dst_before)
        stage_dst_after = stage_by_pop.get(dst_after)
        if dst_before and stage_dst_before and stage_dst_after and stage_dst_before == stage_dst_after:
            superseded_same_stage.add(dst_before)

    # Seed any InputCount populations up-front (helps order-independent transfers)
    for pop_id in input_counts:
        if pop_id in population_ids:
            seed_population(pop_id)

    def apply_transfer_row(row: dict) -> None:
        src_before = (row.get("SourcePopBefore") or "").strip()
        src_after = (row.get("SourcePopAfter") or "").strip()
        dst_before = (row.get("DestPopBefore") or "").strip()
        dst_after = (row.get("DestPopAfter") or "").strip()
        share = clamp_decimal(parse_decimal(row.get("ShareCountFwd")), Decimal("0"), Decimal("1"))

        moved_count = None

        if src_before and src_before not in current_counts:
            seed_population(src_before)

        if src_before in current_counts:
            src_count = current_counts.get(src_before, Decimal("0"))
            moved_count = (src_count * share).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            remaining = src_count - moved_count

            if src_after:
                if src_after in population_ids:
                    counts_at_start.setdefault(src_after, remaining)
                current_counts[src_after] = remaining

            current_counts.pop(src_before, None)

        if dst_before and dst_before not in current_counts:
            seed_population(dst_before)

        dest_before_count = None
        if dst_before in current_counts:
            dest_before_count = current_counts.pop(dst_before)

        if dst_after:
            dest_count = Decimal("0")
            if dest_before_count is not None:
                dest_count += dest_before_count
            if moved_count is not None:
                dest_count += moved_count
            if dst_after in population_ids:
                counts_at_start.setdefault(dst_after, dest_count)
            current_counts[dst_after] = dest_count

    for _, op_rows_iter in groupby(
        sub_transfers,
        key=lambda r: (
            row_time(r),
            (r.get("OperationID") or ""),
        ),
    ):
        pending = list(op_rows_iter)
        while pending:
            source_after_candidates = {
                (row.get("SourcePopAfter") or "").strip()
                for row in pending
                if (row.get("SourcePopAfter") or "").strip()
            }
            progressed = False
            next_pending: list[dict] = []
            for row in pending:
                src_before = (row.get("SourcePopBefore") or "").strip()
                if (
                    src_before
                    and src_before not in current_counts
                    and src_before not in input_counts
                    and src_before not in member_by_id
                    and src_before in source_after_candidates
                ):
                    # Defer this edge until the same-operation row that produces
                    # src_before has been processed.
                    next_pending.append(row)
                    continue
                apply_transfer_row(row)
                progressed = True

            if not next_pending:
                break
            if not progressed:
                # Fallback: unresolved dependencies likely originate fully outside
                # this component chain, so process remaining rows with zero seeding.
                for row in next_pending:
                    apply_transfer_row(row)
                break
            pending = next_pending

    # Seed remaining populations that were never touched by transfers.
    for pop_id in population_ids:
        if pop_id not in counts_at_start:
            seed_population(pop_id)

    return {
        pop_id: int(round(count))
        for pop_id, count in counts_at_start.items()
        if pop_id in population_ids
    }, superseded_same_stage


def identify_external_mixing_populations(
    population_ids: set[str],
    sub_transfers: list[dict],
) -> set[str]:
    """Return in-component populations participating in edges to outside populations."""
    if not population_ids or not sub_transfers:
        return set()

    mixed: set[str] = set()
    for row in sub_transfers:
        endpoints = {
            (row.get("SourcePopBefore") or "").strip(),
            (row.get("SourcePopAfter") or "").strip(),
            (row.get("DestPopBefore") or "").strip(),
            (row.get("DestPopAfter") or "").strip(),
        }
        endpoints.discard("")
        if not endpoints:
            continue

        in_component = {pop_id for pop_id in endpoints if pop_id in population_ids}
        if not in_component:
            continue
        has_outside = any(pop_id not in population_ids for pop_id in endpoints)
        if has_outside:
            mixed.update(in_component)

    return mixed


def get_external_map(
    source_model: str,
    source_identifier: str,
    *,
    component_key: str | None = None,
    allow_legacy_fallback: bool = True,
) -> ExternalIdMap | None:
    if source_model == "Populations":
        return get_assignment_external_map(
            str(source_identifier),
            component_key=component_key,
            allow_legacy_fallback=allow_legacy_fallback,
        )
    return ExternalIdMap.objects.filter(
        source_system="FishTalk", source_model=source_model, source_identifier=str(source_identifier)
    ).first()


def get_or_create_egg_supplier(name: str, *, history_user: User | None, history_reason: str | None) -> EggSupplier:
    supplier = EggSupplier.objects.filter(name=name).first()
    if not supplier:
        supplier = EggSupplier(
            name=name,
            contact_details="Unknown (FishTalk migration)",
            certifications="",
        )
        save_with_history(supplier, user=history_user, reason=history_reason)
    ExternalIdMap.objects.update_or_create(
        source_system="FishTalk",
        source_model="EggSupplier",
        source_identifier=name,
        defaults={
            "target_app_label": supplier._meta.app_label,
            "target_model": supplier._meta.model_name,
            "target_object_id": supplier.pk,
        },
    )
    return supplier


def build_creation_workflow_number(batch_number: str, component_key: str) -> str:
    base = f"CRT-{batch_number}"
    if len(base) <= 50:
        return base
    suffix = (component_key or "")[:8]
    reserved = len("CRT-") + 1 + len(suffix)
    trimmed = batch_number[: max(0, 50 - reserved)]
    if suffix:
        return f"CRT-{trimmed}-{suffix}"
    return f"CRT-{trimmed}"[:50]


def remove_component_creation_workflow(component_key: str) -> dict[str, int]:
    """Remove synthetic creation workflow/maps for a component key."""
    workflow_map = get_external_map("PopulationComponentCreationWorkflow", component_key)
    workflow_ids: set[int] = set()
    action_ids: set[int] = set()
    if workflow_map:
        workflow_ids.add(int(workflow_map.target_object_id))

    if workflow_ids:
        action_ids.update(
            CreationAction.objects.filter(workflow_id__in=workflow_ids).values_list("id", flat=True)
        )
        CreationAction.objects.filter(id__in=list(action_ids)).delete()
        BatchCreationWorkflow.objects.filter(id__in=list(workflow_ids)).delete()

    maps_deleted = 0
    deleted, _ = ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model="PopulationComponentCreationWorkflow",
        source_identifier=str(component_key),
    ).delete()
    maps_deleted += int(deleted)

    if action_ids:
        action_map_qs = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="PopulationCreationAction",
            target_app_label="batch",
            target_model="creationaction",
            target_object_id__in=list(action_ids),
        )
    else:
        action_map_qs = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="PopulationCreationAction",
            metadata__component_key=component_key,
        )
    deleted, _ = action_map_qs.delete()
    maps_deleted += int(deleted)

    return {
        "workflows_deleted": len(workflow_ids),
        "actions_deleted": len(action_ids),
        "external_maps_deleted": maps_deleted,
    }


@dataclass(frozen=True)
class ComponentMember:
    population_id: str
    population_name: str
    container_id: str
    start_time: datetime
    end_time: datetime | None
    first_stage: str
    last_stage: str


def load_members_from_report(report_dir: Path, *, component_id: int | None, component_key: str | None) -> list[ComponentMember]:
    import csv

    path = report_dir / "population_members.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing report file: {path}")

    members: list[ComponentMember] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if component_id is not None and row.get("component_id") != str(component_id):
                continue
            if component_key is not None and row.get("component_key") != component_key:
                continue
            start = parse_dt(row.get("start_time", ""))
            if start is None:
                continue
            end = parse_dt(row.get("end_time", ""))
            members.append(
                ComponentMember(
                    population_id=row.get("population_id", ""),
                    population_name=row.get("population_name", ""),
                    container_id=row.get("container_id", ""),
                    start_time=start,
                    end_time=end,
                    first_stage=row.get("first_stage", ""),
                    last_stage=row.get("last_stage", ""),
                )
            )

    members.sort(key=lambda m: m.start_time)
    return members


def load_members_from_existing_component_map(
    component_key: str,
    *,
    csv_dir: str | None,
    sql_profile: str,
) -> list[ComponentMember]:
    """Fallback loader for reruns when report membership is stale or partial.

    Uses existing ExternalIdMap population mappings for this component key and
    reconstructs ComponentMember rows from extracted Populations data (or SQL).
    """
    mapping_rows = get_component_assignment_maps(component_key)
    if not mapping_rows:
        return []

    population_ids = [
        extract_population_id(row.source_model, row.source_identifier)
        for row in mapping_rows
        if row.source_identifier
    ]
    population_ids = [pid for pid in population_ids if pid]
    if not population_ids:
        return []

    population_data_by_id: dict[str, dict] = {}
    if csv_dir:
        loader = ETLDataLoader(csv_dir)
        for row in loader.get_populations_by_ids(set(population_ids)):
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id:
                population_data_by_id[pop_id] = row
    else:
        extractor = BaseExtractor(ExtractionContext(profile=sql_profile))
        for i in range(0, len(population_ids), 1000):
            batch = population_ids[i : i + 1000]
            in_clause = ",".join(f"'{pid}'" for pid in batch)
            rows = extractor._run_sqlcmd(
                query=(
                    "SELECT "
                    "CONVERT(varchar(36), p.PopulationID) AS PopulationID, "
                    "CONVERT(varchar(36), p.ContainerID) AS ContainerID, "
                    "CONVERT(varchar(19), p.StartTime, 120) AS StartTime, "
                    "CONVERT(varchar(19), p.EndTime, 120) AS EndTime "
                    "FROM dbo.Populations p "
                    f"WHERE p.PopulationID IN ({in_clause})"
                ),
                headers=["PopulationID", "ContainerID", "StartTime", "EndTime"],
            )
            for row in rows:
                pop_id = (row.get("PopulationID") or "").strip()
                if pop_id:
                    population_data_by_id[pop_id] = row

    assignment_by_id = {
        assignment.id: assignment
        for assignment in BatchContainerAssignment.objects.filter(
            id__in=[row.target_object_id for row in mapping_rows if row.target_object_id]
        )
    }

    members: list[ComponentMember] = []
    for mapping in mapping_rows:
        pop_id = extract_population_id(mapping.source_model, mapping.source_identifier)
        if not pop_id:
            continue
        metadata = mapping.metadata or {}
        assignment = assignment_by_id.get(mapping.target_object_id)
        pop_data = population_data_by_id.get(pop_id, {})

        container_id = (
            (pop_data.get("ContainerID") or "").strip()
            or (metadata.get("container_id") or "").strip()
        )
        if not container_id and assignment:
            container_map = ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="Containers",
                target_app_label="infrastructure",
                target_model="container",
                target_object_id=assignment.container_id,
            ).first()
            if container_map:
                container_id = container_map.source_identifier

        start_time = parse_dt(pop_data.get("StartTime") or "")
        if start_time is None and assignment and assignment.assignment_date:
            start_time = datetime.combine(assignment.assignment_date, datetime.min.time())
        if start_time is None:
            continue

        end_time = parse_dt(pop_data.get("EndTime") or "")
        if end_time is None and assignment and assignment.departure_date:
            end_time = datetime.combine(assignment.departure_date, datetime.min.time())

        members.append(
            ComponentMember(
                population_id=pop_id,
                population_name=metadata.get("population_name") or "",
                container_id=container_id,
                start_time=start_time,
                end_time=end_time,
                first_stage="",
                last_stage="",
            )
        )

    members.sort(key=lambda m: m.start_time)
    return members


def prune_stale_component_assignment_state(
    *,
    batch: Batch,
    component_key: str,
    members: list[ComponentMember],
) -> dict[str, int]:
    """Prune stale assignment state for deterministic component reruns.

    Reruns can narrow member selection as stitching improves. Any assignment
    rows previously mapped to this component but no longer present in the
    current member set must be removed to avoid population double counting and
    impossible lifecycle chronology.
    """
    normalized_member_population_ids = {
        str(member.population_id or "").strip()
        for member in members
        if str(member.population_id or "").strip()
    }

    mapping_rows = get_component_assignment_maps(component_key)
    if not mapping_rows:
        return {
            "stale_population_ids": 0,
            "stale_assignments_deleted": 0,
            "protected_dependents_deleted": 0,
            "orphan_transfer_workflows_deleted": 0,
            "orphan_creation_workflows_deleted": 0,
            "external_maps_deleted": 0,
        }

    stale_population_ids: set[str] = set()
    mapped_assignment_ids: set[int] = set()
    for mapping in mapping_rows:
        pop_id = extract_population_id(mapping.source_model, mapping.source_identifier)
        if pop_id and pop_id in normalized_member_population_ids:
            continue
        if pop_id:
            stale_population_ids.add(pop_id)
        if mapping.target_object_id:
            mapped_assignment_ids.add(int(mapping.target_object_id))

    stale_assignment_ids = set(
        BatchContainerAssignment.objects.filter(
            id__in=mapped_assignment_ids,
            batch=batch,
        ).values_list("id", flat=True)
    )

    if not stale_population_ids and not stale_assignment_ids:
        return {
            "stale_population_ids": 0,
            "stale_assignments_deleted": 0,
            "protected_dependents_deleted": 0,
            "orphan_transfer_workflows_deleted": 0,
            "orphan_creation_workflows_deleted": 0,
            "external_maps_deleted": 0,
        }

    protected_dependents_deleted = 0
    external_map_cleanup_targets: defaultdict[tuple[str, str], set[int]] = defaultdict(set)

    if stale_assignment_ids:
        stale_assignment_ids_list = list(stale_assignment_ids)
        for relation in BatchContainerAssignment._meta.related_objects:
            rel_field = relation.field
            on_delete = getattr(rel_field.remote_field, "on_delete", None)
            if getattr(on_delete, "__name__", "") != "PROTECT":
                continue

            rel_model = relation.related_model
            related_ids = list(
                rel_model.objects.filter(
                    **{f"{rel_field.name}_id__in": stale_assignment_ids_list}
                ).values_list("id", flat=True)
            )
            if not related_ids:
                continue

            rel_model.objects.filter(id__in=related_ids).delete()
            protected_dependents_deleted += len(related_ids)
            external_map_cleanup_targets[
                (rel_model._meta.app_label, rel_model._meta.model_name)
            ].update(related_ids)

    stale_assignment_ids_list = list(stale_assignment_ids)
    if stale_assignment_ids_list:
        BatchContainerAssignment.objects.filter(
            batch=batch,
            id__in=stale_assignment_ids_list,
        ).delete()
        external_map_cleanup_targets[
            (BatchContainerAssignment._meta.app_label, BatchContainerAssignment._meta.model_name)
        ].update(stale_assignment_ids_list)

    orphan_transfer_workflow_ids = list(
        BatchTransferWorkflow.objects.filter(batch=batch)
        .annotate(action_count=Count("actions"))
        .filter(action_count=0)
        .values_list("id", flat=True)
    )
    if orphan_transfer_workflow_ids:
        BatchTransferWorkflow.objects.filter(id__in=orphan_transfer_workflow_ids).delete()
        external_map_cleanup_targets[
            (BatchTransferWorkflow._meta.app_label, BatchTransferWorkflow._meta.model_name)
        ].update(orphan_transfer_workflow_ids)

    orphan_creation_workflow_ids = list(
        BatchCreationWorkflow.objects.filter(batch=batch)
        .annotate(action_count=Count("actions"))
        .filter(action_count=0)
        .values_list("id", flat=True)
    )
    if orphan_creation_workflow_ids:
        BatchCreationWorkflow.objects.filter(id__in=orphan_creation_workflow_ids).delete()
        external_map_cleanup_targets[
            (BatchCreationWorkflow._meta.app_label, BatchCreationWorkflow._meta.model_name)
        ].update(orphan_creation_workflow_ids)

    external_maps_deleted = 0
    for (target_app_label, target_model), object_ids in external_map_cleanup_targets.items():
        if not object_ids:
            continue
        deleted, _ = ExternalIdMap.objects.filter(
            target_app_label=target_app_label,
            target_model=target_model,
            target_object_id__in=list(object_ids),
        ).delete()
        external_maps_deleted += int(deleted)

    if stale_population_ids:
        scoped_identifiers = [
            build_component_population_identifier(component_key, pop_id)
            for pop_id in stale_population_ids
        ]
        deleted, _ = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model=ASSIGNMENT_SCOPED_SOURCE_MODEL,
            source_identifier__in=scoped_identifiers,
            target_app_label="batch",
            target_model="batchcontainerassignment",
        ).delete()
        external_maps_deleted += int(deleted)

    if stale_population_ids or stale_assignment_ids_list:
        legacy_assignment_qs = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model=LEGACY_ASSIGNMENT_SOURCE_MODEL,
            target_app_label="batch",
            target_model="batchcontainerassignment",
        )
        legacy_assignment_qs = legacy_assignment_qs.filter(
            (Q(metadata__component_key=component_key) & Q(source_identifier__in=list(stale_population_ids)))
            | Q(target_object_id__in=stale_assignment_ids_list)
        )
        deleted, _ = legacy_assignment_qs.delete()
        external_maps_deleted += int(deleted)

    return {
        "stale_population_ids": len(stale_population_ids),
        "stale_assignments_deleted": len(stale_assignment_ids_list),
        "protected_dependents_deleted": protected_dependents_deleted,
        "orphan_transfer_workflows_deleted": len(orphan_transfer_workflow_ids),
        "orphan_creation_workflows_deleted": len(orphan_creation_workflow_ids),
        "external_maps_deleted": external_maps_deleted,
    }


def delete_component_assignment_state_by_ids(
    *,
    batch: Batch,
    assignment_ids: set[int] | list[int],
) -> dict[str, int]:
    """Delete assignment rows and protected dependents for targeted reroute cases."""
    assignment_id_list = sorted({int(assignment_id) for assignment_id in assignment_ids if assignment_id})
    if not assignment_id_list:
        return {
            "assignments_deleted": 0,
            "protected_dependents_deleted": 0,
            "orphan_transfer_workflows_deleted": 0,
            "orphan_creation_workflows_deleted": 0,
            "external_maps_deleted": 0,
        }

    protected_dependents_deleted = 0
    external_map_cleanup_targets: defaultdict[tuple[str, str], set[int]] = defaultdict(set)

    for relation in BatchContainerAssignment._meta.related_objects:
        rel_field = relation.field
        on_delete = getattr(rel_field.remote_field, "on_delete", None)
        if getattr(on_delete, "__name__", "") != "PROTECT":
            continue

        rel_model = relation.related_model
        related_ids = list(
            rel_model.objects.filter(
                **{f"{rel_field.name}_id__in": assignment_id_list}
            ).values_list("id", flat=True)
        )
        if not related_ids:
            continue

        rel_model.objects.filter(id__in=related_ids).delete()
        protected_dependents_deleted += len(related_ids)
        external_map_cleanup_targets[
            (rel_model._meta.app_label, rel_model._meta.model_name)
        ].update(related_ids)

    deleted_assignments = list(
        BatchContainerAssignment.objects.filter(
            batch=batch,
            id__in=assignment_id_list,
        ).values_list("id", flat=True)
    )
    if deleted_assignments:
        BatchContainerAssignment.objects.filter(
            batch=batch,
            id__in=deleted_assignments,
        ).delete()
        external_map_cleanup_targets[
            (BatchContainerAssignment._meta.app_label, BatchContainerAssignment._meta.model_name)
        ].update(deleted_assignments)

    orphan_transfer_workflow_ids = list(
        BatchTransferWorkflow.objects.filter(batch=batch)
        .annotate(action_count=Count("actions"))
        .filter(action_count=0)
        .values_list("id", flat=True)
    )
    if orphan_transfer_workflow_ids:
        BatchTransferWorkflow.objects.filter(id__in=orphan_transfer_workflow_ids).delete()
        external_map_cleanup_targets[
            (BatchTransferWorkflow._meta.app_label, BatchTransferWorkflow._meta.model_name)
        ].update(orphan_transfer_workflow_ids)

    orphan_creation_workflow_ids = list(
        BatchCreationWorkflow.objects.filter(batch=batch)
        .annotate(action_count=Count("actions"))
        .filter(action_count=0)
        .values_list("id", flat=True)
    )
    if orphan_creation_workflow_ids:
        BatchCreationWorkflow.objects.filter(id__in=orphan_creation_workflow_ids).delete()
        external_map_cleanup_targets[
            (BatchCreationWorkflow._meta.app_label, BatchCreationWorkflow._meta.model_name)
        ].update(orphan_creation_workflow_ids)

    external_maps_deleted = 0
    for (target_app_label, target_model), object_ids in external_map_cleanup_targets.items():
        if not object_ids:
            continue
        deleted, _ = ExternalIdMap.objects.filter(
            target_app_label=target_app_label,
            target_model=target_model,
            target_object_id__in=list(object_ids),
        ).delete()
        external_maps_deleted += int(deleted)

    return {
        "assignments_deleted": len(deleted_assignments),
        "protected_dependents_deleted": protected_dependents_deleted,
        "orphan_transfer_workflows_deleted": len(orphan_transfer_workflow_ids),
        "orphan_creation_workflows_deleted": len(orphan_creation_workflow_ids),
        "external_maps_deleted": external_maps_deleted,
    }


def load_members_from_chain(chain_dir: Path, *, chain_id: str) -> tuple[list[ComponentMember], str]:
    """Load members from SubTransfers-based chain stitching output.
    
    Args:
        chain_dir: Directory containing batch_chains.csv from scripts/migration/legacy/tools/subtransfer_chain_stitching.py (deprecated)
        chain_id: Chain ID (e.g., "CHAIN-00001")
    
    Returns:
        Tuple of (list of ComponentMember, geography string)
    """
    import csv

    path = chain_dir / "batch_chains.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing chain file: {path}")

    members: list[ComponentMember] = []
    geography = None
    
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("chain_id") != chain_id:
                continue
            
            # Capture geography from first row
            if geography is None:
                geography = row.get("geography", "Unknown")
            
            # Parse start_time (ISO format from chain stitching)
            start_str = row.get("start_time", "")
            start = None
            if start_str:
                try:
                    # Handle ISO format with T separator
                    start = datetime.fromisoformat(start_str)
                except ValueError:
                    start = parse_dt(start_str)
            
            if start is None:
                continue
            
            # Parse end_time
            end_str = row.get("end_time", "")
            end = None
            if end_str:
                try:
                    end = datetime.fromisoformat(end_str)
                except ValueError:
                    end = parse_dt(end_str)
            
            # Parse stages (semicolon-separated)
            stages = row.get("stages", "").split(";") if row.get("stages") else []
            first_stage = stages[0] if stages else ""
            last_stage = stages[-1] if stages else ""
            
            members.append(
                ComponentMember(
                    population_id=row.get("population_id", ""),
                    population_name=row.get("population_name", ""),
                    container_id=row.get("container_id", ""),
                    start_time=start,
                    end_time=end,
                    first_stage=first_stage,
                    last_stage=last_stage,
                )
            )

    members.sort(key=lambda m: m.start_time)
    return members, geography or "Unknown"


def load_members_from_linked_batch(chain_dir: Path, *, batch_id: str, csv_dir: Path = None, sql_extractor=None) -> tuple[list[ComponentMember], str]:
    """Load members from linked batch output (full lifecycle batch).
    
    Args:
        chain_dir: Directory containing linked_batches.csv from scripts/migration/legacy/tools/subtransfer_chain_stitching.py --link-by-project (deprecated)
        batch_id: Linked batch ID (e.g., "BATCH-00013")
        csv_dir: Optional directory containing populations.csv for container lookup
        sql_extractor: Optional SQL extractor for container lookup
    
    Returns:
        Tuple of (list of ComponentMember, geography string)
    """
    import csv

    path = chain_dir / "linked_batches.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing linked batches file: {path}")

    # Load container mapping from populations.csv if available
    pop_to_container: dict[str, str] = {}
    if csv_dir:
        pop_csv = csv_dir / "populations.csv"
        if pop_csv.exists():
            with pop_csv.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pop_to_container[row.get("PopulationID", "")] = row.get("ContainerID", "")

    members: list[ComponentMember] = []
    geography = None
    seen_pop_ids = set()  # Avoid duplicates
    
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("batch_id") != batch_id:
                continue
            
            pop_id = row.get("population_id", "")
            if pop_id in seen_pop_ids:
                continue
            seen_pop_ids.add(pop_id)
            
            # Capture geography from first non-Unknown row
            row_geo = row.get("geography", "Unknown")
            if geography is None or (geography == "Unknown" and row_geo != "Unknown"):
                geography = row_geo
            
            # Parse start_time (ISO format)
            start_str = row.get("start_time", "")
            start = None
            if start_str:
                try:
                    start = datetime.fromisoformat(start_str)
                except ValueError:
                    start = parse_dt(start_str)
            
            if start is None:
                continue
            
            # Parse end_time
            end_str = row.get("end_time", "")
            end = None
            if end_str:
                try:
                    end = datetime.fromisoformat(end_str)
                except ValueError:
                    end = parse_dt(end_str)
            
            # Parse stages (semicolon-separated)
            stages = row.get("stages", "").split(";") if row.get("stages") else []
            first_stage = stages[0] if stages else ""
            last_stage = stages[-1] if stages else ""
            
            members.append(
                ComponentMember(
                    population_id=pop_id,
                    population_name="",
                    container_id="",  # Filled in later
                    start_time=start,
                    end_time=end,
                    first_stage=first_stage,
                    last_stage=last_stage,
                )
            )
    
    # Get container IDs from CSV or SQL
    pop_ids = [m.population_id for m in members]
    
    if csv_dir:
        # Already loaded above
        pass
    elif sql_extractor and pop_ids:
        # Query SQL for containers
        in_clause = ",".join(f"'{pid}'" for pid in pop_ids[:1000])  # Batch to avoid huge IN clause
        rows = sql_extractor._run_sqlcmd(
            query=f"SELECT CONVERT(varchar(36), PopulationID) AS PopulationID, CONVERT(varchar(36), ContainerID) AS ContainerID FROM dbo.Populations WHERE PopulationID IN ({in_clause})",
            headers=["PopulationID", "ContainerID"],
        )
        for row in rows:
            pop_to_container[row.get("PopulationID", "")] = row.get("ContainerID", "")
        
        # Handle remaining populations in batches
        for i in range(1000, len(pop_ids), 1000):
            batch_ids = pop_ids[i:i+1000]
            in_clause = ",".join(f"'{pid}'" for pid in batch_ids)
            rows = sql_extractor._run_sqlcmd(
                query=f"SELECT CONVERT(varchar(36), PopulationID) AS PopulationID, CONVERT(varchar(36), ContainerID) AS ContainerID FROM dbo.Populations WHERE PopulationID IN ({in_clause})",
                headers=["PopulationID", "ContainerID"],
            )
            for row in rows:
                pop_to_container[row.get("PopulationID", "")] = row.get("ContainerID", "")
    
    # Update members with container IDs
    updated_members = []
    for m in members:
        container_id = pop_to_container.get(m.population_id, "")
        updated_members.append(
            ComponentMember(
                population_id=m.population_id,
                population_name=m.population_name,
                container_id=container_id,
                start_time=m.start_time,
                end_time=m.end_time,
                first_stage=m.first_stage,
                last_stage=m.last_stage,
            )
        )

    updated_members.sort(key=lambda m: m.start_time)
    return updated_members, geography or "Unknown"


def get_chain_info(chain_dir: Path, chain_id: str) -> dict | None:
    """Get summary info for a chain from batch_summary.csv."""
    import csv
    
    path = chain_dir / "batch_summary.csv"
    if not path.exists():
        return None
    
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("chain_id") == chain_id:
                return row
    return None


CHAIN_DIR_DEFAULT = PROJECT_ROOT / "scripts" / "migration" / "output" / "chain_stitching"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pilot migrate one stitched FishTalk population component",
        epilog="""
Stitching approaches:
  SubTransfers-based (recommended):
    --chain-id CHAIN-00001 --chain-dir scripts/migration/output/chain_stitching/
    
  Project-based (legacy):
    --component-key <uuid> --report-dir scripts/migration/output/population_stitching/
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # SubTransfers-based stitching (recommended)
    chain_group = parser.add_argument_group("SubTransfers-based stitching (recommended)")
    chain_group.add_argument(
        "--batch-id",
        help="Linked batch ID from scripts/migration/legacy/tools/subtransfer_chain_stitching.py --link-by-project (deprecated)",
    )
    chain_group.add_argument(
        "--chain-id",
        help="Single chain ID from scripts/migration/legacy/tools/subtransfer_chain_stitching.py (deprecated)",
    )
    chain_group.add_argument(
        "--chain-dir",
        default=str(CHAIN_DIR_DEFAULT),
        help="Directory containing batch_chains.csv or linked_batches.csv",
    )
    
    # Project-based stitching (legacy)
    legacy_group = parser.add_argument_group("Project-based stitching (legacy)")
    legacy_group.add_argument("--component-id", type=int, help="Component id from components.csv")
    legacy_group.add_argument("--component-key", help="Stable component_key from components.csv")
    legacy_group.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    legacy_group.add_argument(
        "--prefer-existing-component-map",
        action="store_true",
        help=(
            "Opt in to replacing report members with existing component-mapped "
            "assignment members when the existing map is larger."
        ),
    )
    legacy_group.add_argument(
        "--merge-existing-component-map",
        action="store_true",
        help=(
            "Union report members with existing component-mapped assignment members "
            "to avoid destructive rerun pruning while still applying new members."
        ),
    )
    legacy_group.add_argument(
        "--allow-component-membership-shrink",
        action="store_true",
        help=(
            "Allow rerun pruning when existing component-mapped membership is larger "
            "than report membership. Default is safety abort."
        ),
    )
    
    # Common options
    parser.add_argument("--geography", default="Faroe Islands", help="Target geography name (auto-detected for chain-based)")
    parser.add_argument("--batch-number", help="Override batch_number")
    parser.add_argument(
        "--expected-site",
        help=(
            "Optional strict site guard (substring match, normalized). "
            "Example: 'S21 Viðareiði' or 'FW22 Applecross'."
        ),
    )
    parser.add_argument(
        "--migration-profile",
        default="fw_default",
        choices=MIGRATION_PROFILE_NAMES,
        help=(
            "Migration profile preset to apply (default: fw_default). "
            "Profiles allow cohort-family behavior without forking scripts."
        ),
    )
    parser.add_argument(
        "--active-window-days",
        type=int,
        default=365,
        help="Days back from latest FishTalk status to consider active (default: 365)",
    )
    parser.add_argument(
        "--assignment-active-window-days",
        type=int,
        default=365,
        help="Days back from latest FishTalk status to treat assignments as active (default: 365)",
    )
    parser.add_argument(
        "--creation-window-days",
        type=int,
        default=60,
        help="Days from batch start to include in creation workflow (default: 60)",
    )
    parser.add_argument(
        "--allow-sea-only-creation-workflow",
        action="store_true",
        help=(
            "Allow synthetic batch-creation workflow for sea-only components. "
            "Default behavior skips creation workflows for sea-only components "
            "to keep sea population migration as continuation of FW lineage."
        ),
    )
    parser.add_argument(
        "--scoped-assignment-maps-only",
        action="store_true",
        help=(
            "Resolve FishTalk population assignments only via component-scoped "
            "external maps and never through legacy global Populations maps. "
            "Use this for targeted/manual continuation cases that overlap "
            "population IDs already present in other migrated batches."
        ),
    )
    parser.add_argument(
        "--lifecycle-frontier-window-hours",
        type=int,
        default=None,
        help=(
            "Override profile value: when stage selection mode is frontier, "
            "consider latest per-container non-zero holders within this many "
            "hours of the component frontier timestamp and pick the most "
            "advanced stage among candidates."
        ),
    )
    parser.add_argument(
        "--same-stage-supersede-max-hours",
        type=int,
        default=None,
        help=(
            "Override profile value: zero only short-lived same-stage "
            "superseded populations whose lifespan is <= this many hours."
        ),
    )
    parser.add_argument(
        "--external-mixing-status-multiplier",
        type=float,
        default=10.0,
        help=(
            "When a population has transfer-edge evidence to outside-component populations, "
            "prefer status count over conserved count if status >= conserved * multiplier "
            "(default: 10.0)."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    parser.add_argument("--sql-profile", default="fishtalk_readonly", help="FishTalk SQL Server profile")
    parser.add_argument(
        "--use-csv",
        type=str,
        metavar="CSV_DIR",
        help="Use pre-extracted CSV files from this directory instead of live SQL",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    migration_profile = get_migration_profile(args.migration_profile)
    lifecycle_frontier_window_hours = (
        int(args.lifecycle_frontier_window_hours)
        if args.lifecycle_frontier_window_hours is not None
        else int(migration_profile.lifecycle_frontier_window_hours)
    )
    same_stage_supersede_max_hours = (
        int(args.same_stage_supersede_max_hours)
        if args.same_stage_supersede_max_hours is not None
        else int(migration_profile.same_stage_supersede_max_hours)
    )
    stage_selection_mode = migration_profile.stage_selection_mode
    enforce_latest_holder_consistency = (
        migration_profile.enforce_latest_container_holder_consistency
    )
    suppress_orphan_zero_assignments = (
        migration_profile.suppress_orphan_zero_assignments
    )
    print(
        "Migration profile selected: "
        f"{migration_profile.name} "
        f"(stage_mode={stage_selection_mode}, "
        f"frontier_window_h={lifecycle_frontier_window_hours}, "
        f"supersede_max_h={same_stage_supersede_max_hours}, "
        f"latest_holder_consistency={enforce_latest_holder_consistency}, "
        f"suppress_orphan_zero={suppress_orphan_zero_assignments})"
    )
    
    # Determine which stitching approach to use
    use_linked_batch = args.batch_id is not None
    use_chain_stitching = args.chain_id is not None
    use_project_stitching = args.component_id is not None or args.component_key is not None
    
    if not use_linked_batch and not use_chain_stitching and not use_project_stitching:
        raise SystemExit(
            "Provide one of:\n"
            "  Linked batch (full lifecycle): --batch-id BATCH-00013\n"
            "  Single chain: --chain-id CHAIN-00001\n"
            "  Project-based (legacy): --component-id or --component-key"
        )
    
    if sum([use_linked_batch, use_chain_stitching, use_project_stitching]) > 1:
        raise SystemExit("Cannot use multiple stitching approaches at once")
    
    # Load members based on stitching approach
    detected_geography = args.geography
    
    if use_linked_batch:
        # Full lifecycle linked batch (recommended)
        chain_dir = Path(args.chain_dir)
        csv_dir = Path(args.use_csv) if args.use_csv else None
        
        # Create SQL extractor if not using CSV
        sql_extractor = None
        if not csv_dir:
            from scripts.migration.extractors.base import BaseExtractor, ExtractionContext
            sql_extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))
        
        members, detected_geography = load_members_from_linked_batch(
            chain_dir, batch_id=args.batch_id, csv_dir=csv_dir, sql_extractor=sql_extractor
        )
        if not members:
            raise SystemExit(f"No members found for linked batch {args.batch_id}")
        
        # Use batch_id as component_key for ExternalIdMap
        component_key = f"linked:{args.batch_id}"
        
        print(f"Linked batch {args.batch_id}: {len(members)} populations, geography={detected_geography}")
    elif use_chain_stitching:
        # SubTransfers-based single chain
        chain_dir = Path(args.chain_dir)
        members, detected_geography = load_members_from_chain(chain_dir, chain_id=args.chain_id)
        if not members:
            raise SystemExit(f"No members found for chain {args.chain_id}")
        
        # Use chain_id as component_key for ExternalIdMap
        component_key = f"chain:{args.chain_id}"
        
        # Get chain summary info
        chain_info = get_chain_info(chain_dir, args.chain_id)
        if chain_info:
            print(f"Chain {args.chain_id}: {chain_info.get('population_count', '?')} populations, "
                  f"geography={chain_info.get('geography', '?')}, stages={chain_info.get('stages', '?')}")
            if chain_info.get("is_valid") == "False":
                print(f"WARNING: Chain {args.chain_id} is flagged as multi-geography anomaly!")
    else:
        # Project-based stitching (legacy)
        report_dir = Path(args.report_dir)
        members = load_members_from_report(report_dir, component_id=args.component_id, component_key=args.component_key)

        component_key = args.component_key
        if not component_key:
            # Derive component_key from the first matching row in the report.
            import csv

            with (report_dir / "population_members.csv").open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    if row.get("component_id") == str(args.component_id):
                        component_key = row.get("component_key")
                        break
        if not component_key:
            raise SystemExit("Unable to resolve component_key from report")

        fallback_members = load_members_from_existing_component_map(
            component_key,
            csv_dir=args.use_csv,
            sql_profile=args.sql_profile,
        )
        if not members and fallback_members:
            print(
                "Using existing component-mapped members fallback because "
                f"report has no rows for {component_key}."
            )
            members = fallback_members
        elif args.merge_existing_component_map and fallback_members:
            merged_members = {
                str(member.population_id).strip(): member
                for member in fallback_members
                if str(member.population_id or "").strip()
            }
            report_member_count = len(members)
            for member in members:
                member_key = str(member.population_id or "").strip()
                if not member_key:
                    continue
                merged_members[member_key] = member
            members = sorted(merged_members.values(), key=lambda m: m.start_time)
            print(
                "Merged report members with existing component-mapped fallback for "
                f"{component_key}: report={report_member_count} rows, "
                f"fallback={len(fallback_members)} rows, merged={len(members)} rows."
            )
        elif (
            args.prefer_existing_component_map
            and fallback_members
            and len(fallback_members) > len(members)
        ):
            print(
                "Using existing component-mapped members fallback for "
                f"{component_key}: report={len(members)} rows, fallback={len(fallback_members)} rows"
            )
            members = fallback_members
        elif fallback_members and len(fallback_members) > len(members):
            if not args.allow_component_membership_shrink:
                raise SystemExit(
                    "[ERROR] Destructive component membership shrink blocked for "
                    f"{component_key}: report={len(members)} rows, "
                    f"fallback={len(fallback_members)} rows. "
                    "Use --merge-existing-component-map (recommended), "
                    "--prefer-existing-component-map, or "
                    "--allow-component-membership-shrink."
                )
            print(
                "Proceeding with component membership shrink for "
                f"{component_key} (report={len(members)} rows, "
                f"fallback={len(fallback_members)} rows) because "
                "--allow-component-membership-shrink is set."
            )

        if not members:
            raise SystemExit("No members found for the selected component")

    representative = next((m.population_name for m in members if "TRANSPORTPOP" not in m.population_name.upper()), members[0].population_name)
    component_start_time = min(m.start_time for m in members)
    batch_start = component_start_time.date()
    creation_window_end_date = batch_start + timedelta(days=args.creation_window_days)
    creation_window_seed_stages = {"Egg&Alevin", "Fry", "Parr", "Smolt"}

    # Initialize data source (CSV or SQL)
    data_source = DataSource(csv_dir=args.use_csv, sql_profile=args.sql_profile)
    # Keep extractor reference for compatibility with existing code paths
    extractor = data_source.extractor

    container_ids = sorted({m.container_id for m in members if m.container_id})

    # Load container grouping early so stage resolution can use hall mappings
    grouping_rows = data_source.get_container_grouping(container_ids)
    container_grouping: dict[str, dict[str, str]] = {}
    for row in grouping_rows:
        container_id = row.get("ContainerID")
        if not container_id:
            continue
        site = normalize_label(row.get("Site"))
        site_group = normalize_label(row.get("SiteGroup"))
        company = normalize_label(row.get("Company"))
        prod_stage = normalize_label(row.get("ProdStage"))
        container_group = normalize_label(row.get("ContainerGroup"))
        container_group_id = normalize_label(row.get("ContainerGroupID"))
        stand_name = normalize_label(row.get("StandName"))
        stand_id = normalize_label(row.get("StandID"))
        geo_name, bucket = resolve_site_grouping(site, site_group)
        container_grouping[container_id] = {
            "site": site,
            "site_code": parse_site_code(site),
            "site_group": site_group,
            "company": company,
            "prod_stage": prod_stage,
            "container_group": container_group,
            "container_group_id": container_group_id,
            "stand_name": stand_name,
            "stand_id": stand_id,
            "geography": geo_name,
            "grouping_bucket": bucket,
        }

    member_sites = sorted(
        {
            (container_grouping.get(member.container_id, {}).get("site") or "").strip()
            for member in members
            if member.container_id
        }
    )
    member_sites = [site for site in member_sites if site]
    normalized_member_sites = {normalize_key(site) for site in member_sites}

    if args.expected_site:
        expected_site_key = normalize_key(args.expected_site)
        if expected_site_key not in normalized_member_sites:
            raise SystemExit(
                "Site guard failed: expected site "
                f"'{args.expected_site}' not found in component sites {member_sites}."
            )

    name_station_code = extract_station_code(args.batch_number or representative)
    if name_station_code:
        marine_area_sites = [
            site for site in member_sites if parse_site_code(site).startswith("A")
        ]
        if member_sites and len(marine_area_sites) == len(member_sites):
            print(
                "[INFO] Station-code guard bypassed for marine-area component sites: "
                f"{member_sites}"
            )
        else:
            station_matches = [
                site for site in member_sites
                if name_station_code in normalize_key(site).replace(" ", "")
            ]
            if not station_matches:
                raise SystemExit(
                    "Station-code guard failed: batch name suggests "
                    f"{name_station_code} but component sites are {member_sites}. "
                    "Use --expected-site to override if this is intentional."
                )

    # Deterministic fallback for unmapped halls: if every token-mapped member in a
    # site/hall tuple resolves to the same lifecycle stage, reuse that stage.
    hall_stage_observations: defaultdict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for member in members:
        group_meta = container_grouping.get(member.container_id, {})
        site_key = normalize_key(group_meta.get("site"))
        hall_key = normalize_key(group_meta.get("container_group"))
        if not site_key or not hall_key:
            continue
        token_stage = fishtalk_stage_to_aquamind(member.last_stage or member.first_stage)
        if not token_stage:
            continue
        hall_stage_observations[(site_key, hall_key)][token_stage] += 1

    hall_stage_hints: dict[tuple[str, str], str] = {}
    for key, stage_counter in hall_stage_observations.items():
        if len(stage_counter) != 1:
            continue
        hall_stage_hints[key] = next(iter(stage_counter))

    if hall_stage_hints:
        print("Derived hall-stage fallback hints from component stage tokens:")
        for (site_key, hall_key), stage_name in sorted(hall_stage_hints.items()):
            stage_counter = hall_stage_observations[(site_key, hall_key)]
            observed = stage_counter.get(stage_name, 0)
            total = sum(stage_counter.values())
            print(
                f"  {site_key} / {hall_key} -> {stage_name} "
                f"({observed}/{total} token-mapped rows)"
            )

    # S08 R-Høll contains both Parr and Smolt segments for some cohorts.
    # Deterministic rule: first placement into a given R-Høll container is Parr;
    # subsequent in-hall redistributions in that container are Smolt.
    S08_R_HOLL_HALL_KEYS = {"R-HØLL", "HALL R-"}
    # Avoid selecting micro bridge rows (seconds-long handoff fragments) as the
    # "first placement" for dual-stage classification.
    S08_R_HOLL_INITIAL_MIN_DURATION_SECONDS = 6 * 60 * 60
    s08_r_holl_initial_population_ids: set[str] = set()
    s08_r_holl_initial_by_container: dict[str, str] = {}
    s08_r_holl_initial_rank_by_container: dict[str, tuple[datetime, float, str]] = {}
    s08_r_holl_material_by_container: dict[str, str] = {}
    s08_r_holl_material_rank_by_container: dict[str, tuple[datetime, float, str]] = {}
    for member in members:
        if not member.population_id or not member.container_id:
            continue
        group_meta = container_grouping.get(member.container_id, {})
        site_key = normalize_key(group_meta.get("site"))
        hall_key = normalize_key(group_meta.get("container_group"))
        if site_key != "S08 GJÓGV" or hall_key not in S08_R_HOLL_HALL_KEYS:
            continue
        duration_seconds = (
            float("inf")
            if member.end_time is None
            else max((member.end_time - member.start_time).total_seconds(), 0.0)
        )
        # Rank by earliest start; if tied, prefer longest-lived member.
        rank = (member.start_time, -duration_seconds, member.population_id)
        current_rank = s08_r_holl_initial_rank_by_container.get(member.container_id)
        if current_rank is None or rank < current_rank:
            s08_r_holl_initial_rank_by_container[member.container_id] = rank
            s08_r_holl_initial_by_container[member.container_id] = member.population_id
        is_material_row = (
            duration_seconds == float("inf")
            or duration_seconds >= S08_R_HOLL_INITIAL_MIN_DURATION_SECONDS
        )
        if is_material_row:
            current_material_rank = s08_r_holl_material_rank_by_container.get(member.container_id)
            if current_material_rank is None or rank < current_material_rank:
                s08_r_holl_material_rank_by_container[member.container_id] = rank
                s08_r_holl_material_by_container[member.container_id] = member.population_id
    s08_r_holl_initial_population_by_container = {
        container_id: s08_r_holl_material_by_container.get(container_id, pop_id)
        for container_id, pop_id in s08_r_holl_initial_by_container.items()
    }
    s08_r_holl_initial_population_ids = set(s08_r_holl_initial_population_by_container.values())
    if s08_r_holl_initial_population_ids:
        print(
            "Applied S08 R-Høll dual-stage override "
            f"(Parr-first populations: {len(s08_r_holl_initial_population_ids)}, "
            f"material-min-duration-h={S08_R_HOLL_INITIAL_MIN_DURATION_SECONDS // 3600})"
        )

    def resolve_stage_name(member: ComponentMember) -> str | None:
        group_meta = container_grouping.get(member.container_id, {})
        site_key = normalize_key(group_meta.get("site"))
        hall_key = normalize_key(group_meta.get("container_group"))
        token_stage = fishtalk_stage_to_aquamind(member.last_stage or member.first_stage)
        hall_stage = stage_from_hall(group_meta.get("site"), group_meta.get("container_group"))
        if site_key == "S08 GJÓGV" and hall_key in S08_R_HOLL_HALL_KEYS:
            if member.population_id in s08_r_holl_initial_population_ids:
                return "Parr"
            return "Smolt"
        # Qualified hall-stage mappings are authoritative for these sites and
        # should override per-population stage tokens when present.
        if hall_stage and site_key in HALL_STAGE_PRIORITY_SITES:
            return hall_stage
        if token_stage:
            return token_stage
        if hall_stage:
            return hall_stage
        hint_stage = hall_stage_hints.get(
            (
                site_key,
                normalize_key(group_meta.get("container_group")),
            )
        )
        if hint_stage:
            return hint_stage
        site_stage_fallback = SITE_STAGE_FALLBACK_MAP.get(site_key)
        if site_stage_fallback:
            return site_stage_fallback
        prod_stage = (group_meta.get("prod_stage") or "").upper()
        if prod_stage:
            if "MARINE" in prod_stage or "BROOD" in prod_stage:
                return "Adult"
            if "SMOLT" in prod_stage:
                return "Smolt"
        return token_stage

    population_ids = [m.population_id for m in members if m.population_id]
    member_by_population_id = {m.population_id: m for m in members if m.population_id}
    stage_by_pop = {m.population_id: resolve_stage_name(m) for m in members if m.population_id}
    input_rows_by_population = data_source.get_input_rows(population_ids)
    input_rows_by_population_start: dict[tuple[str, datetime], list[dict]] = defaultdict(list)
    for population_id, rows in input_rows_by_population.items():
        for row in rows:
            start_time = parse_dt((row.get("StartTime") or "").strip())
            if not start_time:
                continue
            input_rows_by_population_start[(population_id, start_time)].append(row)

    delayed_status_input_max_lag = timedelta(hours=24)
    delayed_status_input_min_cluster_size = 8
    delayed_status_input_egg_token_min_cluster_size = 4
    delayed_status_input_no_internal_bucket2_min_cluster_size = 2

    def get_member_input_rows_at_start(member: ComponentMember) -> list[dict]:
        return input_rows_by_population_start.get((member.population_id, member.start_time), [])

    def input_row_has_source_link(row: dict) -> bool:
        delivery_id = (row.get("DeliveryID") or "").strip()
        source_container_id = (row.get("SourceContainerID") or "").strip()
        return bool(delivery_id or source_container_id)

    input_suppliers_by_population = data_source.get_input_supplier_ids(population_ids)
    component_start_supplier_ids: set[str] = set()
    for member in members:
        if member.start_time != component_start_time:
            continue
        component_start_supplier_ids.update(
            input_suppliers_by_population.get(member.population_id, set())
        )
    if component_start_supplier_ids:
        print(
            "Resolved component-start input supplier IDs: "
            f"{len(component_start_supplier_ids)}"
        )
    delayed_input_start_cluster_sizes: Counter[datetime] = Counter()
    for member in members:
        if not member.population_id or member.end_time is None:
            continue
        if member.start_time <= component_start_time:
            continue
        if not (batch_start <= member.start_time.date() <= creation_window_end_date):
            continue
        lifecycle_name = stage_by_pop.get(member.population_id) or resolve_stage_name(member)
        if lifecycle_name not in creation_window_seed_stages:
            continue
        member_input_rows_at_start = get_member_input_rows_at_start(member)
        if not member_input_rows_at_start:
            continue
        try:
            member_input_count_at_start = sum(
                float(row.get("InputCount") or 0) for row in member_input_rows_at_start
            )
        except Exception:
            member_input_count_at_start = 0.0
        if member_input_count_at_start <= 0:
            continue
        if any(input_row_has_source_link(row) for row in member_input_rows_at_start):
            continue
        member_input_supplier_ids = input_suppliers_by_population.get(member.population_id, set())
        if (
            not component_start_supplier_ids
            or not member_input_supplier_ids
            or member_input_supplier_ids.isdisjoint(component_start_supplier_ids)
        ):
            continue
        delayed_input_start_cluster_sizes[member.start_time] += 1
    delayed_input_large_cluster_count = sum(
        1
        for size in delayed_input_start_cluster_sizes.values()
        if size >= delayed_status_input_min_cluster_size
    )
    if delayed_input_large_cluster_count:
        print(
            "Resolved delayed-input same-supplier start clusters "
            f"(size>={delayed_status_input_min_cluster_size}): {delayed_input_large_cluster_count}"
        )
    latest_status_time_by_pop: dict[str, datetime] = {}
    latest_status_nonzero_by_pop: dict[str, bool] = {}
    latest_status_count_by_pop: dict[str, int] = {}
    component_status_time: datetime | None = None

    global_status_time = data_source.get_global_latest_status_time()
    active_cutoff = (
        global_status_time - timedelta(days=args.active_window_days)
        if global_status_time
        else None
    )
    assignment_active_cutoff = (
        global_status_time - timedelta(days=args.assignment_active_window_days)
        if global_status_time
        else None
    )

    if population_ids:
        latest_status_time_by_pop = data_source.get_latest_status_by_population(population_ids)
        component_status_time = max(latest_status_time_by_pop.values(), default=None)
        for population_id, status_time in latest_status_time_by_pop.items():
            snapshot = data_source.get_status_snapshot(population_id, status_time)
            latest_status_nonzero_by_pop[population_id] = (
                data_source._has_nonzero_status(snapshot) if snapshot else False
            )
            try:
                latest_status_count_by_pop[population_id] = (
                    int(round(float(snapshot.get("CurrentCount") or 0))) if snapshot else 0
                )
            except (TypeError, ValueError):
                latest_status_count_by_pop[population_id] = 0

    component_subtransfers = data_source.get_subtransfers(set(population_ids))
    component_population_id_set = set(population_ids)
    internal_delivery_links_by_input_population = (
        data_source.get_internal_delivery_links_for_input_populations(component_population_id_set)
    )
    station_split_source_site_by_population: dict[str, str] = {}
    if internal_delivery_links_by_input_population:
        source_population_ids: set[str] = set()
        for links in internal_delivery_links_by_input_population.values():
            for link in links:
                source_population_ids.update(link.get("sales_population_ids", set()))
        source_population_ids -= component_population_id_set
        if source_population_ids:
            station_split_source_site_by_population = data_source.get_population_site_map(
                source_population_ids
            )
    conserved_counts, superseded_same_stage = build_conserved_population_counts(members, data_source, stage_by_pop)
    external_mixing_population_ids = identify_external_mixing_populations(
        set(population_ids),
        component_subtransfers,
    )
    subtransfer_touched_population_ids: set[str] = set()
    subtransfer_touch_times_by_population: dict[str, list[datetime]] = defaultdict(list)
    for row in component_subtransfers:
        operation_time = parse_dt((row.get("OperationTime") or "").strip())
        for key in ("SourcePopBefore", "SourcePopAfter", "DestPopBefore", "DestPopAfter"):
            pop_id = (row.get(key) or "").strip()
            if pop_id:
                subtransfer_touched_population_ids.add(pop_id)
                if operation_time:
                    subtransfer_touch_times_by_population[pop_id].append(operation_time)
    for touch_times in subtransfer_touch_times_by_population.values():
        touch_times.sort()
    removal_counts_by_population = data_source.get_removal_counts_by_population(set(population_ids))
    culling_counts_by_population = data_source.get_culling_counts_by_population(set(population_ids))
    if conserved_counts:
        nonzero_counts = sum(1 for count in conserved_counts.values() if count > 0)
        print(
            f"Conserved counts computed for {len(conserved_counts)} populations "
            f"({nonzero_counts} non-zero)."
        )
    else:
        print("Conserved counts unavailable; using status snapshots for population_count.")
    if external_mixing_population_ids:
        print(
            "Populations with outside-component SubTransfers edges: "
            f"{len(external_mixing_population_ids)}"
        )
    if superseded_same_stage:
        print(f"Same-stage superseded populations: {len(superseded_same_stage)}")
    superseded_with_operational_activity = data_source.get_operational_activity_population_ids(
        superseded_same_stage
    )
    superseded_with_non_culling_operational_activity = data_source.get_operational_activity_population_ids(
        superseded_same_stage,
        include_culling=False,
    )
    if superseded_with_operational_activity:
        print(
            "Same-stage superseded populations with operational activity: "
            f"{len(superseded_with_operational_activity)}"
        )
    if superseded_with_non_culling_operational_activity:
        print(
            "Same-stage superseded populations with non-culling operational activity: "
            f"{len(superseded_with_non_culling_operational_activity)}"
        )

    same_day_bridge_keys: set[tuple[str, str, date]] = set()
    for member in members:
        if member.population_id not in superseded_same_stage:
            continue
        if member.end_time is None:
            continue
        duration = member.end_time - member.start_time
        if duration > timedelta(hours=same_stage_supersede_max_hours):
            continue
        stage_name = stage_by_pop.get(member.population_id) or resolve_stage_name(member)
        if not stage_name:
            continue
        same_day_bridge_keys.add((member.container_id, stage_name, member.start_time.date()))
        same_day_bridge_keys.add((member.container_id, stage_name, member.end_time.date()))

    subtransfer_roles_by_population: dict[str, set[str]] = defaultdict(set)
    for row in component_subtransfers:
        for key in ("SourcePopBefore", "SourcePopAfter", "DestPopBefore", "DestPopAfter"):
            pop_id = (row.get(key) or "").strip()
            if pop_id and pop_id in member_by_population_id:
                subtransfer_roles_by_population[pop_id].add(key)

    members_by_container: dict[str, list[ComponentMember]] = defaultdict(list)
    for member in members:
        if member.container_id:
            members_by_container[member.container_id].append(member)

    def has_explicit_stage_tokens(member: ComponentMember) -> bool:
        return bool((member.first_stage or "").strip() or (member.last_stage or "").strip())

    def resolve_same_container_stage_predecessor(member: ComponentMember) -> ComponentMember | None:
        lifecycle_name = stage_by_pop.get(member.population_id) or resolve_stage_name(member)
        if not lifecycle_name:
            return None
        candidates: list[ComponentMember] = []
        for candidate in members_by_container.get(member.container_id, []):
            if candidate.population_id == member.population_id:
                continue
            if candidate.start_time > member.start_time:
                continue
            if candidate.end_time != member.start_time:
                continue
            candidate_stage = stage_by_pop.get(candidate.population_id) or resolve_stage_name(candidate)
            if candidate_stage != lifecycle_name:
                continue
            candidates.append(candidate)
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda candidate: (
                has_explicit_stage_tokens(candidate),
                (
                    (candidate.end_time - candidate.start_time).total_seconds()
                    if candidate.end_time
                    else float("inf")
                ),
                candidate.start_time,
                candidate.population_id,
            ),
        )

    culling_tail_fold_target_by_population: dict[str, str] = {}
    for member in members:
        pop_id = member.population_id
        if culling_counts_by_population.get(pop_id, 0) <= 0:
            continue
        if pop_id in superseded_with_non_culling_operational_activity:
            continue
        role_set = subtransfer_roles_by_population.get(pop_id, set())
        if role_set != {"SourcePopAfter"}:
            continue
        predecessor = resolve_same_container_stage_predecessor(member)
        if predecessor is None:
            continue
        culling_tail_fold_target_by_population[pop_id] = predecessor.population_id
    if culling_tail_fold_target_by_population:
        print(
            "Culling-only same-container residual tails eligible for fold-back: "
            f"{len(culling_tail_fold_target_by_population)}"
        )

    def is_long_companion_same_day_bridge(
        member: ComponentMember,
        lifecycle_name: str | None,
        status_count: int | None,
    ) -> bool:
        if status_count is None or status_count <= 0:
            return False
        if not lifecycle_name:
            return False
        bridge_key = (member.container_id, lifecycle_name, member.start_time.date())
        if bridge_key not in same_day_bridge_keys:
            return False
        if member.end_time is None:
            return True
        duration = member.end_time - member.start_time
        return duration > timedelta(hours=same_stage_supersede_max_hours)

    stage_start_dates: dict[str, date] = {}
    for member in members:
        stage_name = stage_by_pop.get(member.population_id) or resolve_stage_name(member)
        if not stage_name:
            continue
        start_date = member.start_time.date()
        existing = stage_start_dates.get(stage_name)
        if existing is None or start_date < existing:
            stage_start_dates[stage_name] = start_date

    legacy_open_member = any(m.end_time is None for m in members)
    if latest_status_time_by_pop:
        if active_cutoff:
            has_active_member = any(
                latest_status_nonzero_by_pop.get(population_id, False) and status_time >= active_cutoff
                for population_id, status_time in latest_status_time_by_pop.items()
            )
        else:
            has_active_member = any(latest_status_nonzero_by_pop.values())
        has_active_member = has_active_member or legacy_open_member
    else:
        has_active_member = legacy_open_member

    active_population_by_container: dict[str, str] = {}
    # Tie-break container holders by:
    # 1) latest status timestamp
    # 2) open membership (blank source end_time)
    # 3) latest source count
    # 4) latest membership start timestamp
    container_latest: dict[str, tuple[datetime, bool, int, datetime, str]] = {}
    for member in members:
        if not member.container_id:
            continue
        if latest_status_time_by_pop and not latest_status_nonzero_by_pop.get(member.population_id, False):
            continue
        candidate_time = latest_status_time_by_pop.get(member.population_id) or member.end_time or member.start_time
        candidate_status_count = latest_status_count_by_pop.get(member.population_id, 0)
        candidate = (
            candidate_time,
            member.end_time is None,
            candidate_status_count,
            member.start_time,
            member.population_id,
        )
        current = container_latest.get(member.container_id)
        if not current or candidate > current:
            container_latest[member.container_id] = candidate

    skipped_due_outside_holder = 0
    for container_id, (candidate_time, _open_member, _status_count, _start_time, population_id) in container_latest.items():
        if enforce_latest_holder_consistency:
            latest_holder = data_source.get_latest_nonzero_status_holder_for_container(container_id)
            # If the source container's latest non-zero holder is a different
            # population after this component's candidate timestamp, this cohort no
            # longer owns the latest occupancy in that container.
            if latest_holder and latest_holder[0] != population_id and latest_holder[1] > candidate_time:
                skipped_due_outside_holder += 1
                continue
        active_population_by_container[container_id] = population_id
    if enforce_latest_holder_consistency and skipped_due_outside_holder:
        print(
            "Filtered active-container candidates due to later outside-component "
            f"latest holders: {skipped_due_outside_holder}"
        )
    elif not enforce_latest_holder_consistency:
        print("Latest-holder consistency gate disabled by selected migration profile.")
    if has_active_member and not active_population_by_container:
        has_active_member = False

    batch_end = max((m.end_time for m in members if m.end_time), default=None)
    batch_end_date = batch_end.date() if batch_end else None
    batch_status = "ACTIVE" if has_active_member else "COMPLETED"
    batch_actual_end_date = None if has_active_member else (
        component_status_time.date() if component_status_time else batch_end_date
    )

    lifecycle_stage_name = None
    frontier_rows: list[tuple[datetime, str, str]] = []
    for container_id, population_id in active_population_by_container.items():
        member = member_by_population_id.get(population_id)
        if member is None:
            continue
        stage_name = stage_by_pop.get(population_id) or resolve_stage_name(member)
        if not stage_name:
            continue
        candidate_time = latest_status_time_by_pop.get(population_id) or member.end_time or member.start_time
        frontier_rows.append((candidate_time, stage_name, population_id))

    if stage_selection_mode == STAGE_SELECTION_FRONTIER and frontier_rows:
        frontier_anchor_time = max(row[0] for row in frontier_rows)
        frontier_window = timedelta(hours=max(int(lifecycle_frontier_window_hours), 1))
        frontier_cutoff = frontier_anchor_time - frontier_window
        frontier_near_cutoff = [row for row in frontier_rows if row[0] >= frontier_cutoff]
        frontier_stage_counts = Counter(
            stage_name
            for _, stage_name, _ in frontier_near_cutoff
            if stage_name in STAGE_INDEX
        )
        if frontier_stage_counts:
            lifecycle_stage_name = max(
                frontier_stage_counts,
                key=lambda stage_name: (
                    STAGE_INDEX.get(stage_name, -1),
                    frontier_stage_counts[stage_name],
                    stage_name,
                ),
            )
            print(
                "Lifecycle stage selected from active frontier "
                f"(anchor={frontier_anchor_time}, window={frontier_window}): "
                f"{lifecycle_stage_name} from {dict(frontier_stage_counts)}"
            )
    elif stage_selection_mode == STAGE_SELECTION_LATEST_MEMBER:
        print("Lifecycle stage mode=latest_member: skipping frontier aggregation.")

    if not lifecycle_stage_name:
        current_member = None
        current_member_time = None
        for member in members:
            candidate_time = latest_status_time_by_pop.get(member.population_id) or member.end_time or member.start_time
            if not current_member_time or candidate_time > current_member_time:
                current_member_time = candidate_time
                current_member = member
        if current_member:
            lifecycle_stage_name = resolve_stage_name(current_member)
    if not lifecycle_stage_name and members:
        for member in members:
            lifecycle_stage_name = resolve_stage_name(member)
            if lifecycle_stage_name:
                break
    if not lifecycle_stage_name:
        raise SystemExit("Unable to resolve lifecycle stage for batch; add stage mapping or hall mapping.")

    # Resolve species / lifecycle stage.
    species = Species.objects.filter(name="Atlantic Salmon").first() or Species.objects.first()
    if species is None:
        raise SystemExit("Missing Species master data; run scripts/migration/setup_master_data.py")
    lifecycle_stage = LifeCycleStage.objects.filter(name=lifecycle_stage_name).first()
    if lifecycle_stage is None:
        raise SystemExit("Missing LifeCycleStage master data; run scripts/migration/setup_master_data.py")

    batch_number = args.batch_number
    if not batch_number:
        slug = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in representative).strip("-")
        batch_number = f"FT-{component_key[:8]}-{slug}"[:50]

    if not container_ids:
        raise SystemExit("No container ids found in component members")

    # Get containers using data source (CSV or SQL)
    containers = data_source.get_containers(container_ids)
    containers_by_id = {row["ContainerID"]: row for row in containers}

    # Get org units using data source
    org_unit_ids = sorted({row.get("OrgUnitID") for row in containers if row.get("OrgUnitID")})
    org_units = data_source.get_org_units(org_unit_ids)
    org_by_id = {row["OrgUnitID"]: row for row in org_units}

    containers_by_org: dict[str, list[str]] = {}
    for row in containers:
        org_id = row.get("OrgUnitID")
        container_id = row.get("ContainerID")
        if not org_id or not container_id:
            continue
        containers_by_org.setdefault(org_id, []).append(container_id)

    # Container classification:
    # 1) member stage-derived buckets,
    # 2) grouped-organisation prod_stage/site fallback,
    # 3) no implicit freshwater default (avoid A* marine areas as stations).
    container_bucket: dict[str, str] = {}
    for member in members:
        bucket = stage_bucket(member.last_stage or member.first_stage or "")
        if not bucket:
            group_meta = container_grouping.get(member.container_id, {})
            bucket = infer_bucket_from_grouping(
                group_meta.get("site"),
                group_meta.get("prod_stage"),
            )
        if not bucket:
            continue
        current = container_bucket.get(member.container_id)
        if current == "sea":
            continue
        if bucket == "sea":
            container_bucket[member.container_id] = "sea"
        else:
            container_bucket.setdefault(member.container_id, "freshwater")

    # Backfill bucket classification for members with sparse stage tokens.
    for container_id in container_ids:
        if container_id in container_bucket:
            continue
        group_meta = container_grouping.get(container_id, {})
        inferred = infer_bucket_from_grouping(
            group_meta.get("site"),
            group_meta.get("prod_stage"),
        )
        if inferred:
            container_bucket[container_id] = inferred

    if args.dry_run:
        print(f"[dry-run] Would migrate component_key={component_key} into batch_number={batch_number}")
        print(f"[dry-run] Members: {len(members)} populations, containers: {len(container_ids)}")
        return 0

    with transaction.atomic():
        history_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        history_reason = f"FishTalk migration: component {component_key}"
        def get_geography(name: str) -> Geography:
            if not name:
                name = detected_geography
            if name not in geography_cache:
                geography_cache[name], _ = Geography.objects.get_or_create(
                    name=name,
                    defaults={"description": f"Imported placeholder for {name}"},
                )
            return geography_cache[name]

        geography_cache: dict[str, Geography] = {}

        tank_type, _ = get_or_create_with_history(
            ContainerType,
            lookup={"name": "FishTalk Imported Tank"},
            defaults={
                "category": "TANK",
                "max_volume_m3": Decimal("999999.99"),
                "description": "Auto-created for FishTalk migration",
            },
            user=history_user,
            reason=history_reason,
        )
        pen_type, _ = get_or_create_with_history(
            ContainerType,
            lookup={"name": "FishTalk Imported Pen"},
            defaults={
                "category": "PEN",
                "max_volume_m3": Decimal("999999.99"),
                "description": "Auto-created for FishTalk migration",
            },
            user=history_user,
            reason=history_reason,
        )
        rack_type, _ = get_or_create_with_history(
            ContainerType,
            lookup={"name": "FishTalk Imported Rack"},
            defaults={
                "category": "OTHER",
                "max_volume_m3": Decimal("999999.99"),
                "description": "Auto-created structural container for rack/stand hierarchy",
            },
            user=history_user,
            reason=history_reason,
        )

        # Lookup (or create) org-unit scoped holders
        # PREFER LOOKUP from pre-migrated infrastructure to avoid race conditions
        station_by_org: dict[str, FreshwaterStation] = {}
        hall_by_org_group: dict[tuple[str, str], Hall] = {}
        fallback_hall_by_org: dict[str, Hall] = {}
        area_by_org: dict[str, Area] = {}
        area_group_by_org: dict[str, AreaGroup | None] = {}
        org_geo_by_id: dict[str, Geography] = {}
        org_lat_by_id: dict[str, Decimal] = {}
        org_lon_by_id: dict[str, Decimal] = {}
        org_site_name_by_id: dict[str, str] = {}
        rack_by_hall_stand: dict[tuple[int, str], Container] = {}

        # Determine which org units have sea containers vs freshwater
        org_has_sea: dict[str, bool] = {}
        org_has_freshwater: dict[str, bool] = {}
        for org_id in org_unit_ids:
            org_containers = containers_by_org.get(org_id, [])
            org_has_sea[org_id] = any(container_bucket.get(cid) == "sea" for cid in org_containers)
            org_has_freshwater[org_id] = any(
                container_bucket.get(cid) == "freshwater" for cid in org_containers
            )

        for org_id in org_unit_ids:
            org = org_by_id.get(org_id) or {}
            org_name = (org.get("Name") or org_id)[:80]
            org_site_candidates = [
                normalize_label(container_grouping.get(cid, {}).get("site"))
                for cid in containers_by_org.get(org_id, [])
                if normalize_label(container_grouping.get(cid, {}).get("site"))
            ]
            if org_site_candidates:
                org_site_name = Counter(org_site_candidates).most_common(1)[0][0]
            else:
                org_site_name = org_name
            org_site_group_candidates = [
                normalize_area_group(container_grouping.get(cid, {}).get("site_group"))
                for cid in containers_by_org.get(org_id, [])
                if normalize_area_group(container_grouping.get(cid, {}).get("site_group"))
            ]
            if org_site_group_candidates:
                org_site_group = Counter(org_site_group_candidates).most_common(1)[0][0]
            else:
                org_site_group = ""
            org_site_code = parse_site_code(org_site_name)
            lat = Decimal(str(org.get("Latitude") or 0)).quantize(Decimal("0.000001"))
            lon = Decimal(str(org.get("Longitude") or 0)).quantize(Decimal("0.000001"))

            org_geo_candidates = [
                container_grouping.get(cid, {}).get("geography")
                for cid in containers_by_org.get(org_id, [])
                if container_grouping.get(cid, {}).get("geography")
            ]
            if org_geo_candidates:
                org_geo_name = Counter(org_geo_candidates).most_common(1)[0][0]
            else:
                org_geo_name = detected_geography
            geography = get_geography(org_geo_name)
            area_group = None
            if org_site_group:
                area_group, _ = get_or_create_with_history(
                    AreaGroup,
                    lookup={
                        "name": org_site_group[:100],
                        "geography": geography,
                        "parent": None,
                    },
                    defaults={
                        "code": normalize_key(org_site_group)[:32],
                        "active": True,
                    },
                    user=history_user,
                    reason=history_reason,
                )
            org_geo_by_id[org_id] = geography
            area_group_by_org[org_id] = area_group
            org_lat_by_id[org_id] = lat
            org_lon_by_id[org_id] = lon
            org_site_name_by_id[org_id] = org_site_name

            # LOOKUP FreshwaterStation from pre-migration, fallback to create
            # Use file locking to prevent race conditions with parallel workers
            import fcntl
            import time
            
            if org_has_freshwater.get(org_id, False):
                if org_site_code.startswith("A"):
                    # Hard guard: A* sites are marine areas, never freshwater stations.
                    print(
                        "Skipping freshwater station creation for marine site-code org "
                        f"{org_id} ({org_site_name})."
                    )
                else:
                    station_name = org_site_name[:100]
                # Try to find pre-created station from ExternalIdMap
                    station_map = get_external_map("OrgUnit_FW", org_id)
                    if station_map:
                        station = FreshwaterStation.objects.get(pk=station_map.target_object_id)
                    else:
                        # First try simple lookup
                        station = FreshwaterStation.objects.filter(
                            name=station_name,
                            geography=geography,
                        ).first()
                        if not station:
                            # Use file lock to serialize creation
                            lock_file = Path(f"/tmp/migration_station_{org_id}.lock")
                            lock_file.touch()
                            with open(lock_file) as f:
                                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                                try:
                                    # Re-check after acquiring lock
                                    station = FreshwaterStation.objects.filter(
                                        name=station_name,
                                        geography=geography,
                                    ).first()
                                    if not station:
                                        station_type = infer_station_type(station_name)
                                        station, _ = get_or_create_with_history(
                                            FreshwaterStation,
                                            lookup={"name": station_name, "geography": geography},
                                            defaults={
                                                "station_type": station_type,
                                                "latitude": lat,
                                                "longitude": lon,
                                                "description": "Imported placeholder from FishTalk",
                                                "active": True,
                                            },
                                            user=history_user,
                                            reason=history_reason,
                                        )
                                finally:
                                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    ExternalIdMap.objects.update_or_create(
                        source_system="FishTalk",
                        source_model="OrgUnit_FW",
                        source_identifier=str(org_id),
                        defaults={
                            "target_app_label": station._meta.app_label,
                            "target_model": station._meta.model_name,
                            "target_object_id": station.pk,
                            "metadata": {
                                "site": org_site_name,
                                "geography": geography.name,
                            },
                        },
                    )
                    station_by_org[org_id] = station

            # LOOKUP Area from pre-migration, fallback to create
            if org_has_sea.get(org_id, False):
                area_name = org_site_name[:100]
                # Try to find pre-created area from ExternalIdMap
                area_map = get_external_map("OrgUnit_Sea", org_id)
                if area_map:
                    area = Area.objects.get(pk=area_map.target_object_id)
                else:
                    # First try simple lookup
                    area = Area.objects.filter(name=area_name, geography=geography).first()
                    if not area:
                        # Use file lock to serialize creation
                        lock_file = Path(f"/tmp/migration_area_{org_id}.lock")
                        lock_file.touch()
                        with open(lock_file) as f:
                            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                            try:
                                # Re-check after acquiring lock
                                area = Area.objects.filter(name=area_name, geography=geography).first()
                                if not area:
                                    area, _ = get_or_create_with_history(
                                        Area,
                                        lookup={"name": area_name, "geography": geography},
                                        defaults={
                                            "latitude": lat,
                                            "longitude": lon,
                                            "max_biomass": Decimal("0"),
                                            "area_group": area_group_by_org.get(org_id),
                                            "active": True,
                                        },
                                        user=history_user,
                                        reason=history_reason,
                                    )
                            finally:
                                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                expected_area_group = area_group_by_org.get(org_id)
                expected_area_group_id = expected_area_group.id if expected_area_group else None
                if area.area_group_id != expected_area_group_id:
                    area.area_group = expected_area_group
                    save_with_history(area, user=history_user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="OrgUnit_Sea",
                    source_identifier=str(org_id),
                    defaults={
                        "target_app_label": area._meta.app_label,
                        "target_model": area._meta.model_name,
                        "target_object_id": area.pk,
                        "metadata": {
                            "site": org_site_name,
                            "geography": geography.name,
                            "area_group": (
                                area_group_by_org.get(org_id).name
                                if area_group_by_org.get(org_id)
                                else None
                            ),
                        },
                    },
                )
                area_by_org[org_id] = area

        # Create containers
        aquamind_container_by_source: dict[str, Container] = {}
        for cid in container_ids:
            src = containers_by_id.get(cid) or {}
            overridden_volume_m3 = resolve_container_volume_m3(src)
            mapped = get_external_map("Containers", cid)
            if mapped:
                container = Container.objects.get(pk=mapped.target_object_id)
                if overridden_volume_m3 > 0 and container.volume_m3 != overridden_volume_m3:
                    container.volume_m3 = overridden_volume_m3
                    save_with_history(container, user=history_user, reason=history_reason)
                aquamind_container_by_source[cid] = container
                continue

            org_id = src.get("OrgUnitID") or org_unit_ids[0]
            geography = org_geo_by_id.get(org_id) or get_geography(detected_geography)
            lat = org_lat_by_id.get(org_id, Decimal("0.000000"))
            lon = org_lon_by_id.get(org_id, Decimal("0.000000"))
            bucket = container_bucket.get(cid)
            group_meta = container_grouping.get(cid, {})
            if not bucket:
                bucket = infer_bucket_from_grouping(
                    group_meta.get("site"),
                    group_meta.get("prod_stage"),
                )
            site_name_for_bucket = (
                normalize_label(group_meta.get("site"))
                or org_site_name_by_id.get(org_id)
                or (org_by_id.get(org_id, {}).get("Name") or "")
            )
            site_code_for_bucket = parse_site_code(site_name_for_bucket)
            if bucket != "sea" and site_code_for_bucket.startswith("A"):
                # Marine site codes must never route through freshwater hall/station
                # container creation; reclassify to sea container semantics.
                print(
                    "Reclassifying container to sea bucket for marine site-code: "
                    f"{cid} ({site_name_for_bucket})"
                )
                bucket = "sea"
            if not bucket:
                print(
                    "Skipping container with unresolved environment bucket: "
                    f"{cid} (site={group_meta.get('site') or '-'}, "
                    f"prod_stage={group_meta.get('prod_stage') or '-'})"
                )
                continue
            if bucket == "sea":
                container_type = pen_type
                area = area_by_org.get(org_id)
                if area is None:
                    area_name = normalize_label(group_meta.get("site")) or org_site_name_by_id.get(org_id) or (
                        org_by_id.get(org_id, {}).get("Name") or org_id
                    )
                    area, _ = get_or_create_with_history(
                        Area,
                        lookup={"name": area_name[:100], "geography": geography},
                        defaults={
                            "latitude": lat,
                            "longitude": lon,
                            "max_biomass": Decimal("0"),
                            "area_group": area_group_by_org.get(org_id),
                            "active": True,
                        },
                        user=history_user,
                        reason=history_reason,
                    )
                    expected_area_group = area_group_by_org.get(org_id)
                    expected_area_group_id = expected_area_group.id if expected_area_group else None
                    if area.area_group_id != expected_area_group_id:
                        area.area_group = expected_area_group
                        save_with_history(area, user=history_user, reason=history_reason)
                    area_by_org[org_id] = area
                    ExternalIdMap.objects.update_or_create(
                        source_system="FishTalk",
                        source_model="OrgUnit_Sea",
                        source_identifier=str(org_id),
                        defaults={
                            "target_app_label": area._meta.app_label,
                            "target_model": area._meta.model_name,
                            "target_object_id": area.pk,
                            "metadata": {
                                "site": area_name,
                                "geography": geography.name,
                                "area_group": (
                                    area_group_by_org.get(org_id).name
                                    if area_group_by_org.get(org_id)
                                    else None
                                ),
                            },
                        },
                    )
                hall = None
            else:
                container_type = tank_type
                area = None
                group_label = hall_label_from_group(group_meta.get("container_group"))
                if not group_label:
                    group_label = hall_label_from_official(src.get("OfficialID"))
                if group_label:
                    hall_key = (org_id, group_label)
                    hall = hall_by_org_group.get(hall_key)
                    if hall is None:
                        station = station_by_org.get(org_id)
                        if station is None:
                            station_name = normalize_label(group_meta.get("site")) or org_site_name_by_id.get(org_id) or (
                                org_by_id.get(org_id, {}).get("Name") or org_id
                            )
                            station_site_code = parse_site_code(station_name)
                            if station_site_code.startswith("A"):
                                print(
                                    "Skipping freshwater container under marine site-code: "
                                    f"{cid} ({station_name})"
                                )
                                continue
                            station_type = infer_station_type(station_name)
                            station, _ = get_or_create_with_history(
                                FreshwaterStation,
                                lookup={"name": station_name[:100], "geography": geography},
                                defaults={
                                    "station_type": station_type,
                                    "latitude": lat,
                                    "longitude": lon,
                                    "description": "Imported placeholder from FishTalk",
                                    "active": True,
                                },
                                user=history_user,
                                reason=history_reason,
                            )
                            station_by_org[org_id] = station
                        group_description = (
                            "Imported placeholder from FishTalk "
                            f"({group_meta.get('container_group') or group_label})"
                        )
                        hall, _ = get_or_create_with_history(
                            Hall,
                            lookup={"name": group_label[:100], "freshwater_station": station},
                            defaults={
                                "description": group_description,
                                "active": True,
                            },
                            user=history_user,
                            reason=history_reason,
                        )
                        hall_by_org_group[hall_key] = hall
                else:
                    hall = fallback_hall_by_org.get(org_id)
                    if hall is None:
                        station = station_by_org.get(org_id)
                        if station is None:
                            station_name = normalize_label(group_meta.get("site")) or org_site_name_by_id.get(org_id) or (
                                org_by_id.get(org_id, {}).get("Name") or org_id
                            )
                            station_site_code = parse_site_code(station_name)
                            if station_site_code.startswith("A"):
                                print(
                                    "Skipping fallback-hall creation under marine site-code: "
                                    f"{cid} ({station_name})"
                                )
                                continue
                            station_type = infer_station_type(station_name)
                            station, _ = get_or_create_with_history(
                                FreshwaterStation,
                                lookup={"name": station_name[:100], "geography": geography},
                                defaults={
                                    "station_type": station_type,
                                    "latitude": lat,
                                    "longitude": lon,
                                    "description": "Imported placeholder from FishTalk",
                                    "active": True,
                                },
                                user=history_user,
                                reason=history_reason,
                            )
                            station_by_org[org_id] = station
                        org_name = (org_by_id.get(org_id, {}).get("Name") or org_id)[:80]
                        hall, _ = get_or_create_with_history(
                            Hall,
                            lookup={
                                "name": f"{org_name} Hall"[:100],
                                "freshwater_station": station,
                            },
                            defaults={
                                "description": "Imported placeholder from FishTalk",
                                "active": True,
                            },
                            user=history_user,
                            reason=history_reason,
                        )
                        fallback_hall_by_org[org_id] = hall

            parent_container = None
            hierarchy_role = "HOLDING"
            stand_name = normalize_label(group_meta.get("stand_name"))
            stand_id = normalize_label(group_meta.get("stand_id"))
            if hall is not None and stand_name:
                stand_key = stand_id or stand_name
                rack_key = (int(hall.id), stand_key)
                parent_container = rack_by_hall_stand.get(rack_key)
                if parent_container is None:
                    parent_container, _ = get_or_create_with_history(
                        Container,
                        lookup={
                            "name": stand_name[:100],
                            "hall": hall,
                            "hierarchy_role": "STRUCTURAL",
                        },
                        defaults={
                            "container_type": rack_type,
                            "area": None,
                            "carrier": None,
                            "parent_container": None,
                            "volume_m3": Decimal("0.01"),
                            "max_biomass_kg": Decimal("0.00"),
                            "feed_recommendations_enabled": False,
                            "active": True,
                        },
                        user=history_user,
                        reason=history_reason,
                    )
                    rack_by_hall_stand[rack_key] = parent_container

            container_name = normalize_label(src.get("ContainerName") or cid) or cid
            container = Container(
                name=container_name[:100],
                container_type=container_type,
                hall=hall,
                area=area,
                carrier=None,
                parent_container=parent_container,
                hierarchy_role=hierarchy_role,
                volume_m3=overridden_volume_m3,
                max_biomass_kg=Decimal("0.00"),
                feed_recommendations_enabled=True,
                active=True,
            )
            save_with_history(container, user=history_user, reason=history_reason)
            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model="Containers",
                source_identifier=str(cid),
                defaults={
                    "target_app_label": container._meta.app_label,
                    "target_model": container._meta.model_name,
                    "target_object_id": container.pk,
                    "metadata": {
                        "container_name": src.get("ContainerName"),
                        "org_unit_id": src.get("OrgUnitID"),
                        "official_id": src.get("OfficialID"),
                        "overridden_volume_m3": str(overridden_volume_m3),
                        "site": container_grouping.get(cid, {}).get("site"),
                        "site_group": container_grouping.get(cid, {}).get("site_group"),
                        "company": container_grouping.get(cid, {}).get("company"),
                        "prod_stage": container_grouping.get(cid, {}).get("prod_stage"),
                        "container_group": container_grouping.get(cid, {}).get("container_group"),
                        "container_group_id": container_grouping.get(cid, {}).get("container_group_id"),
                        "stand_name": container_grouping.get(cid, {}).get("stand_name"),
                        "stand_id": container_grouping.get(cid, {}).get("stand_id"),
                        "grouping_bucket": container_grouping.get(cid, {}).get("grouping_bucket"),
                        "parent_container_id": parent_container.id if parent_container else None,
                        "hierarchy_role": hierarchy_role,
                    },
                },
            )
            aquamind_container_by_source[cid] = container

        # Create / reuse batch via ExternalIdMap
        batch_map = get_external_map("PopulationComponent", component_key)
        if batch_map:
            batch = Batch.objects.get(pk=batch_map.target_object_id)
            previous_batch_number = batch.batch_number
            if not args.batch_number:
                batch_number = batch.batch_number
            batch.batch_number = batch_number
            batch.species = species
            batch.lifecycle_stage = lifecycle_stage
            batch.status = batch_status
            batch.start_date = batch_start
            batch.actual_end_date = batch_actual_end_date
            batch.notes = f"FishTalk stitched component {component_key}; representative='{representative}'"
            save_with_history(batch, user=history_user, reason=history_reason)
            if previous_batch_number != batch.batch_number:
                print(
                    "Batch rename persisted via history-aware save: "
                    f"'{previous_batch_number}' -> '{batch.batch_number}'"
                )
        else:
            batch = Batch(
                batch_number=batch_number,
                species=species,
                lifecycle_stage=lifecycle_stage,
                status=batch_status,
                start_date=batch_start,
                actual_end_date=batch_actual_end_date,
                notes=f"FishTalk stitched component {component_key}; representative='{representative}'",
            )
            save_with_history(batch, user=history_user, reason=history_reason)
            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model="PopulationComponent",
                source_identifier=str(component_key),
                defaults={
                    "target_app_label": batch._meta.app_label,
                    "target_model": batch._meta.model_name,
                    "target_object_id": batch.pk,
                    "metadata": {"batch_number": batch.batch_number},
                },
            )

        stale_prune_stats = prune_stale_component_assignment_state(
            batch=batch,
            component_key=component_key,
            members=members,
        )
        if stale_prune_stats["stale_assignments_deleted"]:
            print(
                "Pruned stale component-mapped assignment state before rebuild: "
                f"stale_pops={stale_prune_stats['stale_population_ids']}, "
                f"stale_assignments={stale_prune_stats['stale_assignments_deleted']}, "
                f"protected_dependents={stale_prune_stats['protected_dependents_deleted']}, "
                f"external_maps={stale_prune_stats['external_maps_deleted']}"
            )

        assignment_by_population_id: dict[str, BatchContainerAssignment] = {}
        lifecycle_fallback_population_ids: list[str] = []

        # Create assignments (1 per FishTalk PopulationID)
        skipped_orphan_zero_assignments = 0
        folded_culling_tail_assignments = 0
        for member in members:
            assignment_map = get_external_map(
                "Populations",
                member.population_id,
                component_key=component_key,
                allow_legacy_fallback=not args.scoped_assignment_maps_only,
            )
            container = aquamind_container_by_source[member.container_id]
            member_group_meta = container_grouping.get(member.container_id, {})
            member_site_key = normalize_key(member_group_meta.get("site"))
            member_hall_key = normalize_key(member_group_meta.get("container_group"))
            member_is_s08_r_holl = (
                member_site_key == "S08 GJÓGV"
                and member_hall_key in S08_R_HOLL_HALL_KEYS
            )

            lifecycle_name = resolve_stage_name(member)
            if not lifecycle_name:
                # Last-resort fallback for sparse source metadata rows. This
                # keeps migration progressing while still surfacing telemetry.
                lifecycle_name = lifecycle_stage_name
                lifecycle_fallback_population_ids.append(member.population_id)
            stage = LifeCycleStage.objects.filter(name=lifecycle_name).first()
            if stage is None:
                raise SystemExit(
                    f"Missing LifeCycleStage master data for '{lifecycle_name}'. "
                    "Run scripts/migration/setup_master_data.py."
                )

            latest_status_time = latest_status_time_by_pop.get(member.population_id)
            is_component_seed = bool(component_key and member.population_id == component_key)
            is_component_initial_window_member = member.start_time == component_start_time
            member_input_supplier_ids = input_suppliers_by_population.get(
                member.population_id, set()
            )
            is_creation_window_seed_stage_member = (
                member.end_time is not None
                and lifecycle_name in creation_window_seed_stages
                and batch_start <= member.start_time.date() <= creation_window_end_date
            )
            supplier_mismatch_vs_component_start = (
                member.start_time > component_start_time
                and bool(component_start_supplier_ids)
                and bool(member_input_supplier_ids)
                and member_input_supplier_ids.isdisjoint(component_start_supplier_ids)
            )
            member_input_rows_at_start = get_member_input_rows_at_start(member)
            try:
                member_input_count_at_start = sum(
                    float(row.get("InputCount") or 0) for row in member_input_rows_at_start
                )
            except Exception:
                member_input_count_at_start = 0.0
            member_input_has_source_link = any(
                input_row_has_source_link(row) for row in member_input_rows_at_start
            )
            delayed_input_start_cluster_size = delayed_input_start_cluster_sizes.get(
                member.start_time, 0
            )
            member_has_egg_stage_token = (
                "EGG" in (member.first_stage or "").upper()
                or "EGG" in (member.last_stage or "").upper()
            )
            delayed_input_cluster_threshold = (
                delayed_status_input_egg_token_min_cluster_size
                if member_has_egg_stage_token
                else delayed_status_input_min_cluster_size
            )
            member_site_key_for_station_split = normalize_key(
                container_grouping.get(member.container_id, {}).get("site")
            )
            member_internal_delivery_links_at_start: list[dict] = []
            if member.start_time > component_start_time:
                for delivery_link in internal_delivery_links_by_input_population.get(
                    member.population_id, []
                ):
                    input_start_time = parse_dt((delivery_link.get("InputStartTime") or "").strip())
                    sales_start_time = parse_dt((delivery_link.get("SalesStartTime") or "").strip())
                    if input_start_time == member.start_time and sales_start_time == member.start_time:
                        member_internal_delivery_links_at_start.append(delivery_link)
            has_any_internal_delivery_link_at_start = bool(member_internal_delivery_links_at_start)
            has_station_split_internal_delivery_link = False
            for delivery_link in member_internal_delivery_links_at_start:
                source_population_ids = {
                    pop_id
                    for pop_id in delivery_link.get("sales_population_ids", set())
                    if pop_id and pop_id not in component_population_id_set
                }
                if not source_population_ids:
                    continue
                source_site_keys = {
                    normalize_key(station_split_source_site_by_population.get(pop_id))
                    for pop_id in source_population_ids
                    if station_split_source_site_by_population.get(pop_id)
                }
                if not source_site_keys:
                    continue
                if member_site_key_for_station_split and all(
                    source_site_key == member_site_key_for_station_split
                    for source_site_key in source_site_keys
                ):
                    continue
                has_station_split_internal_delivery_link = True
                break
            
            # For active assignments (no end_time), use latest status for fish count/biomass
            # For completed assignments, use status near start time
            if member.end_time is None and latest_status_time:
                # Active - get latest status
                status_snapshot = data_source.get_status_snapshot(member.population_id, latest_status_time)
            else:
                # Completed - get status near start
                status_snapshot = data_source.get_status_snapshot(member.population_id, member.start_time)
            status_snapshot_time = (
                parse_dt((status_snapshot.get("StatusTime") or "").strip())
                if status_snapshot
                else None
            )
            exact_start_snapshot = (
                data_source.get_status_snapshot_exact_time(member.population_id, member.start_time)
                if member.end_time is not None
                else None
            )

            exact_start_status_snapshot = exact_start_snapshot is not None
            exact_start_status_count: int | None = None
            if exact_start_snapshot:
                try:
                    exact_start_status_count = int(
                        round(float(exact_start_snapshot.get("CurrentCount") or 0))
                    )
                except Exception:
                    exact_start_status_count = 0
            exact_start_seed_init_zero_authoritative = False
            exact_start_creation_supplier_mismatch_zero_authoritative = False
            exact_start_delayed_input_nonzero_authoritative = False
            exact_start_station_split_input_nonzero_authoritative = False
            exact_start_delayed_input_bucket2_no_internal_authoritative = False
            exact_start_seed_init_zero_candidate = (
                exact_start_status_snapshot
                and exact_start_status_count == 0
                and (is_component_seed or is_component_initial_window_member)
            )
            exact_start_creation_supplier_mismatch_zero_candidate = (
                exact_start_status_snapshot
                and exact_start_status_count == 0
                and is_creation_window_seed_stage_member
                and supplier_mismatch_vs_component_start
            )

            conserved_count = conserved_counts.get(member.population_id) if conserved_counts else None
            count = int(conserved_count) if conserved_count is not None else 0
            known_removals = int(removal_counts_by_population.get(member.population_id, 0) or 0)
            biomass = Decimal("0.00")
            status_count: int | None = None
            status_avg_weight_g: Decimal | None = None
            if status_snapshot:
                try:
                    status_count = int(round(float(status_snapshot.get("CurrentCount") or 0)))
                except ValueError:
                    status_count = 0
                if conserved_count is None:
                    count = status_count
                elif count == 0 and status_count > 0:
                    # Conservation chain produced zero; prefer evidence-based status snapshot.
                    count = status_count
                elif (
                    count == 0
                    and known_removals > 0
                    and not (
                        exact_start_seed_init_zero_candidate
                        or exact_start_creation_supplier_mismatch_zero_candidate
                    )
                ):
                    # If source actions already removed fish from this population, the
                    # baseline cannot be zero without violating conservation-of-events.
                    count = known_removals
                elif (
                    count > 0
                    and status_count > 0
                    and member.population_id in external_mixing_population_ids
                    and float(status_count) >= float(count) * max(args.external_mixing_status_multiplier, 1.0)
                ):
                    # External mixing edges imply this component-only conservation chain
                    # underestimates true in-population counts for some segments.
                    count = status_count
                elif count > 0 and status_count > count:
                    if known_removals > count:
                        # Baseline should not be lower than known source removals.
                        # Keep this as a conservative floor instead of promoting
                        # to full status snapshots, which can overstate rows with
                        # outside-component mixing evidence.
                        count = known_removals
                try:
                    status_biomass = Decimal(str(status_snapshot.get("CurrentBiomassKg") or 0)).quantize(
                        Decimal("0.01")
                    )
                except Exception:
                    status_biomass = Decimal("0.00")
                biomass = status_biomass
                if status_count and status_count > 0 and status_biomass > 0:
                    # Keep higher internal precision so biomass reconstruction
                    # does not drift before model-field rounding is applied.
                    status_avg_weight_g = (
                        (status_biomass * Decimal("1000")) / Decimal(status_count)
                    ).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)
                near_start_subtransfer_touch = any(
                    member.start_time <= touch_time <= member.start_time + delayed_status_input_max_lag
                    for touch_time in subtransfer_touch_times_by_population.get(
                        member.population_id, []
                    )
                )
                exact_start_delayed_input_nonzero_candidate = (
                    exact_start_status_snapshot
                    and exact_start_status_count == 0
                    and is_creation_window_seed_stage_member
                    and member.start_time > component_start_time
                    and delayed_input_start_cluster_size >= delayed_input_cluster_threshold
                    and member_input_count_at_start > 0
                    and not member_input_has_source_link
                    and bool(component_start_supplier_ids)
                    and bool(member_input_supplier_ids)
                    and not member_input_supplier_ids.isdisjoint(component_start_supplier_ids)
                    and status_count is not None
                    and status_count > 0
                    and status_snapshot_time is not None
                    and status_snapshot_time > member.start_time
                    and status_snapshot_time <= member.start_time + delayed_status_input_max_lag
                    and not near_start_subtransfer_touch
                )
                exact_start_station_split_input_nonzero_candidate = (
                    exact_start_status_snapshot
                    and exact_start_status_count == 0
                    and has_station_split_internal_delivery_link
                    and member_input_count_at_start > 0
                    and not member_input_has_source_link
                    and status_count is not None
                    and status_count > 0
                    and status_snapshot_time is not None
                    and status_snapshot_time > member.start_time
                    and status_snapshot_time <= member.start_time + delayed_status_input_max_lag
                    and not near_start_subtransfer_touch
                )
                exact_start_delayed_input_bucket2_no_internal_candidate = (
                    exact_start_status_snapshot
                    and exact_start_status_count == 0
                    and is_creation_window_seed_stage_member
                    and member.start_time > component_start_time
                    and delayed_input_start_cluster_size
                    >= delayed_status_input_no_internal_bucket2_min_cluster_size
                    and delayed_input_start_cluster_size < delayed_input_cluster_threshold
                    and member_input_count_at_start > 0
                    and not member_input_has_source_link
                    and not has_any_internal_delivery_link_at_start
                    and bool(component_start_supplier_ids)
                    and bool(member_input_supplier_ids)
                    and not member_input_supplier_ids.isdisjoint(component_start_supplier_ids)
                    and status_count is not None
                    and status_count > 0
                    and status_snapshot_time is not None
                    and status_snapshot_time > member.start_time
                    and status_snapshot_time <= member.start_time + delayed_status_input_max_lag
                    and not near_start_subtransfer_touch
                )
                if exact_start_status_snapshot and exact_start_status_count and exact_start_status_count > 0:
                    # Exact status at population start is strongest lane-level
                    # evidence for transfer-created destination counts.
                    count = exact_start_status_count
                elif exact_start_seed_init_zero_candidate:
                    # Some cohorts record an exact-start placeholder zero before
                    # first status refresh while Ext_Inputs carries authoritative
                    # lane-start InputCount at the same timestamp.
                    if member_input_count_at_start > 0:
                        count = max(count, int(round(member_input_count_at_start)), status_count or 0)
                        exact_start_delayed_input_nonzero_authoritative = True
                    else:
                        # Seed + initial-window rows should honor exact-start zero
                        # snapshots and not be re-inflated by downstream removal floors.
                        count = 0
                        biomass = Decimal("0.00")
                        exact_start_seed_init_zero_authoritative = True
                elif exact_start_creation_supplier_mismatch_zero_candidate:
                    # Multi-day creation windows are supported, but disjoint
                    # supplier IDs from component-start anchors indicate a
                    # stitched foreign start cluster for this component.
                    count = 0
                    biomass = Decimal("0.00")
                    exact_start_creation_supplier_mismatch_zero_authoritative = True
                elif exact_start_delayed_input_nonzero_candidate:
                    # Legitimate multi-anchor seed inputs can have exact-start zero
                    # snapshots before the first same-day status update lands.
                    count = max(count, int(round(member_input_count_at_start)), status_count or 0)
                    exact_start_delayed_input_nonzero_authoritative = True
                elif exact_start_station_split_input_nonzero_candidate:
                    # Cross-station InternalDelivery inputs can surface as destination
                    # input-lane starts with exact-start zero before first status lands.
                    count = max(count, int(round(member_input_count_at_start)), status_count or 0)
                    exact_start_station_split_input_nonzero_authoritative = True
                elif exact_start_delayed_input_bucket2_no_internal_candidate:
                    # Multi-day seed starts without InternalDelivery links can
                    # still represent legitimate delayed input lane materialization.
                    count = max(count, int(round(member_input_count_at_start)), status_count or 0)
                    exact_start_delayed_input_bucket2_no_internal_authoritative = True
            if member.end_time is None and status_count is not None:
                # Open source populations should use latest measured status counts
                # as authoritative assignment population.
                if status_count > 0:
                    count = status_count
                elif known_removals > 0:
                    count = max(count, known_removals)
            if (
                count == 0
                and known_removals > 0
                and not exact_start_seed_init_zero_authoritative
                and not exact_start_creation_supplier_mismatch_zero_authoritative
            ):
                # Status snapshots are sparse in some components; if source
                # removals exist for this population, baseline cannot remain 0.
                count = known_removals

            member_has_stage_tokens = bool(
                (member.first_stage or "").strip() or (member.last_stage or "").strip()
            )
            duration = (member.end_time - member.start_time) if member.end_time else None
            is_short_superseded = (
                duration is not None
                and duration <= timedelta(hours=same_stage_supersede_max_hours)
            )
            long_bridge_companion = is_long_companion_same_day_bridge(
                member=member,
                lifecycle_name=lifecycle_name,
                status_count=status_count,
            )

            if member.population_id in superseded_same_stage:
                if long_bridge_companion:
                    # Keep long-lived companion rows when paired with short bridge rows
                    # in the same container+stage on the transfer boundary date.
                    count = status_count
                elif (
                    is_short_superseded
                    and member.population_id not in superseded_with_operational_activity
                ):
                    # Suppress short-lived same-stage bridge rows by default.
                    count = 0
                    biomass = Decimal("0.00")
                else:
                    # For long-lived superseded rows, prefer status-at-start where available.
                    # This improves lane-level alignment when SubTransfers conservation and
                    # status snapshots diverge in externally mixed chains.
                    if status_count is not None and status_count > 0:
                        count = max(status_count, known_removals)
                    elif member.population_id in superseded_with_operational_activity:
                        count = max(count, known_removals)
                    elif is_short_superseded:
                        count = 0
                        biomass = Decimal("0.00")
            elif long_bridge_companion:
                # Preserve entry snapshot for long row paired with short same-day bridge.
                # This keeps assignment history aligned with lane-level swimlane evidence.
                if status_count is not None:
                    count = status_count
            elif (
                status_count is not None
                and status_count > 0
                and not member_has_stage_tokens
                and member.population_id in external_mixing_population_ids
            ):
                # For blank-token same-container rows in externally mixed chains,
                # prefer lane-level status-at-start evidence.
                count = status_count
            if (
                member_is_s08_r_holl
                and member.population_id in s08_r_holl_initial_population_ids
                and status_count is not None
                and status_count > 0
            ):
                # S08 R-Høll initial rows should reflect observed holder counts
                # after transfer fan-in, not partial conserved chain fragments.
                count = max(count, status_count)
            initial_pop_id = s08_r_holl_initial_population_by_container.get(member.container_id)
            initial_member = member_by_population_id.get(initial_pop_id) if initial_pop_id else None
            is_pre_initial_bridge_fragment = (
                member_is_s08_r_holl
                and initial_member is not None
                and member.population_id != initial_pop_id
                and member.start_time.date() == initial_member.start_time.date()
                and member.start_time <= initial_member.start_time
                and duration is not None
                and duration.total_seconds() < S08_R_HOLL_INITIAL_MIN_DURATION_SECONDS
            )
            if is_pre_initial_bridge_fragment:
                # These are serial fan-in fragments immediately before the chosen
                # initial holder; keep history row but suppress fish duplication.
                count = 0
                biomass = Decimal("0.00")
            if (
                exact_start_seed_init_zero_authoritative
                or exact_start_creation_supplier_mismatch_zero_authoritative
            ):
                # Keep exact-start authoritative zero guards after downstream
                # heuristics (supersede/bridge/mixing) to avoid re-inflating
                # closed holders in historical rows.
                count = 0
                biomass = Decimal("0.00")
            if exact_start_delayed_input_nonzero_authoritative and count <= 0:
                # Preserve legitimate delayed-status input starts after
                # downstream heuristics that can otherwise flatten history rows.
                count = max(int(round(member_input_count_at_start)), status_count or 0, known_removals)
            if exact_start_station_split_input_nonzero_authoritative and count <= 0:
                # Keep qualified station-split internal-delivery starts intact
                # if downstream heuristics transiently flatten row counts.
                count = max(int(round(member_input_count_at_start)), status_count or 0, known_removals)
            if exact_start_delayed_input_bucket2_no_internal_authoritative and count <= 0:
                # Preserve validated no-internal-link delayed-input starts
                # after downstream heuristics that can flatten row counts.
                count = max(int(round(member_input_count_at_start)), status_count or 0, known_removals)
            count = max(count, 0)
            if count == 0:
                biomass = Decimal("0.00")
                effective_avg_weight_g: Decimal | None = None
            else:
                effective_avg_weight_g = status_avg_weight_g
                if status_avg_weight_g is not None and status_avg_weight_g > 0:
                    # Keep biomass consistent with the chosen assignment count.
                    # This avoids impossible implied weights when count comes from
                    # SubTransfers-conserved chains and biomass comes from status snapshots.
                    biomass = (
                        (Decimal(count) * status_avg_weight_g) / Decimal("1000")
                    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                elif biomass > 0:
                    # Derive avg weight from biomass as a fallback when status avg is unavailable.
                    effective_avg_weight_g = (
                        (biomass * Decimal("1000")) / Decimal(count)
                    ).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)
                else:
                    biomass = Decimal("0.00")
                    effective_avg_weight_g = None

            latest_status_nonzero = latest_status_nonzero_by_pop.get(member.population_id, False)
            if not has_active_member:
                assignment_active = False
            elif latest_status_time and assignment_active_cutoff:
                assignment_active = latest_status_nonzero and latest_status_time >= assignment_active_cutoff
            elif latest_status_time:
                assignment_active = latest_status_nonzero
            else:
                assignment_active = member.end_time is None

            active_population_id = active_population_by_container.get(member.container_id)
            if assignment_active and lifecycle_stage_name and stage and stage.name != lifecycle_stage_name:
                # Keep recent non-zero holders active even when stage tokens lag
                # behind frontier-derived lifecycle stage.
                stage_mismatch_is_recent = False
                if latest_status_time and component_status_time:
                    stage_mismatch_is_recent = latest_status_time >= (
                        component_status_time - timedelta(hours=lifecycle_frontier_window_hours)
                    )
                if not stage_mismatch_is_recent:
                    assignment_active = False

            if assignment_active and member.container_id not in active_population_by_container:
                assignment_active = False

            if assignment_active and active_population_id and active_population_id != member.population_id:
                assignment_active = False

            if assignment_active and count <= 0:
                assignment_active = False

            if assignment_active:
                assignment_departure = None
            elif latest_status_time:
                assignment_departure = latest_status_time.date()
            elif member.end_time:
                assignment_departure = member.end_time.date()
            else:
                assignment_departure = None

            fold_target_population_id = culling_tail_fold_target_by_population.get(member.population_id)
            culling_count = int(culling_counts_by_population.get(member.population_id, 0) or 0)
            should_fold_culling_tail = (
                bool(fold_target_population_id)
                and known_removals == culling_count
                and culling_count > 0
                and count == culling_count
                and member.population_id not in superseded_with_non_culling_operational_activity
            )
            if should_fold_culling_tail:
                folded_assignment = assignment_by_population_id.get(fold_target_population_id)
                if folded_assignment is not None:
                    folded_assignment_changed = False
                    if assignment_departure and (
                        folded_assignment.departure_date is None
                        or folded_assignment.departure_date < assignment_departure
                    ):
                        folded_assignment.departure_date = assignment_departure
                        folded_assignment_changed = True
                    if folded_assignment.is_active:
                        folded_assignment.is_active = False
                        folded_assignment_changed = True
                    if folded_assignment_changed:
                        save_with_history(folded_assignment, user=history_user, reason=history_reason)

                    if assignment_map and assignment_map.target_object_id != folded_assignment.pk:
                        delete_component_assignment_state_by_ids(
                            batch=batch,
                            assignment_ids={int(assignment_map.target_object_id)},
                        )

                    map_metadata = {
                        "component_key": component_key,
                        "container_id": member.container_id,
                        "baseline_population_count": count,
                        "component_population_identifier": build_component_population_identifier(
                            component_key,
                            member.population_id,
                        ),
                        "folded_culling_tail": True,
                        "folded_into_population_id": fold_target_population_id,
                    }
                    upsert_assignment_external_maps(
                        component_key=component_key,
                        population_id=member.population_id,
                        target_app_label=folded_assignment._meta.app_label,
                        target_model=folded_assignment._meta.model_name,
                        target_object_id=folded_assignment.pk,
                        metadata=map_metadata,
                        update_legacy_map=not args.scoped_assignment_maps_only,
                    )
                    assignment_by_population_id[member.population_id] = folded_assignment
                    folded_culling_tail_assignments += 1
                    continue

            suppress_orphan_zero_assignment = (
                not assignment_active
                and count <= 0
                and not member_has_stage_tokens
                and stage.name != "Post-Smolt"
                and member.population_id not in subtransfer_touched_population_ids
                and known_removals <= 0
                and (status_count is None or status_count <= 0)
            )
            if suppress_orphan_zero_assignments and suppress_orphan_zero_assignment:
                skipped_orphan_zero_assignments += 1
                continue

            defaults = {
                "batch": batch,
                "container": container,
                "lifecycle_stage": stage,
                "population_count": count,
                "biomass_kg": biomass,
                "avg_weight_g": effective_avg_weight_g,
                "assignment_date": member.start_time.date(),
                "departure_date": assignment_departure,
                "is_active": assignment_active,
                "notes": f"FishTalk PopulationID={member.population_id}",
            }

            if assignment_map:
                assignment = BatchContainerAssignment.objects.get(pk=assignment_map.target_object_id)
                for key, value in defaults.items():
                    setattr(assignment, key, value)
                save_with_history(assignment, user=history_user, reason=history_reason)
            else:
                assignment = BatchContainerAssignment(**defaults)
                save_with_history(assignment, user=history_user, reason=history_reason)

            map_metadata = {
                "component_key": component_key,
                "container_id": member.container_id,
                "baseline_population_count": count,
                "component_population_identifier": build_component_population_identifier(
                    component_key,
                    member.population_id,
                ),
            }
            upsert_assignment_external_maps(
                component_key=component_key,
                population_id=member.population_id,
                target_app_label=assignment._meta.app_label,
                target_model=assignment._meta.model_name,
                target_object_id=assignment.pk,
                metadata=map_metadata,
                update_legacy_map=not args.scoped_assignment_maps_only,
            )

            assignment_by_population_id[member.population_id] = assignment

        if skipped_orphan_zero_assignments:
            print(
                "Suppressed orphan zero-count assignment rows "
                f"(blank stage tokens + no subtransfer edge + no count evidence): "
                f"{skipped_orphan_zero_assignments}"
            )
        if folded_culling_tail_assignments:
            print(
                "Folded culling-only same-container residual tails into predecessor assignments: "
                f"{folded_culling_tail_assignments}"
            )

        initial_stage_name = lifecycle_stage.name if lifecycle_stage else lifecycle_stage_name
        member_stage_names = {
            resolve_stage_name(member)
            for member in members
            if (member.first_stage or member.last_stage) or container_grouping.get(member.container_id)
        }
        member_stage_names = {stage for stage in member_stage_names if stage in STAGE_INDEX}
        if member_stage_names:
            earliest_stage = min(member_stage_names, key=lambda s: STAGE_INDEX.get(s, 999))
            if initial_stage_name not in STAGE_INDEX or STAGE_INDEX[earliest_stage] < STAGE_INDEX[initial_stage_name]:
                initial_stage_name = earliest_stage

        def member_stage(member: ComponentMember) -> str | None:
            return resolve_stage_name(member)

        initial_members: list[ComponentMember] = []
        if initial_stage_name in {"Egg&Alevin", "Fry", "Parr", "Smolt"}:
            window_end = batch_start + timedelta(days=args.creation_window_days)
            initial_members = [
                member
                for member in members
                if member_stage(member) == initial_stage_name
                and batch_start <= member.start_time.date() <= window_end
            ]
        if not initial_members:
            initial_members = [
                member
                for member in members
                if member.start_time.date() == batch_start
                and member_stage(member) == initial_stage_name
            ]
        if not initial_members:
            initial_members = [member for member in members if member.start_time.date() == batch_start]
        if not initial_members:
            initial_members = [members[0]]

        initial_members.sort(key=lambda member: (member.start_time, member.population_id))
        creation_assignments = [
            (member, assignment_by_population_id.get(member.population_id))
            for member in initial_members
            if assignment_by_population_id.get(member.population_id)
        ]

        if creation_assignments:
            fw_creation_assignments = [
                (member, assignment)
                for member, assignment in creation_assignments
                if assignment.container_id and assignment.container and assignment.container.hall_id
            ]
            sea_only_creation_assignments = [
                (member, assignment)
                for member, assignment in creation_assignments
                if assignment.container_id and assignment.container and assignment.container.area_id
            ]
            if fw_creation_assignments:
                creation_assignments = fw_creation_assignments
            elif sea_only_creation_assignments and not args.allow_sea_only_creation_workflow:
                cleanup_result = remove_component_creation_workflow(component_key)
                print(
                    "Skipping synthetic creation workflow for sea-only component "
                    f"{component_key}; cleanup(workflows={cleanup_result['workflows_deleted']}, "
                    f"actions={cleanup_result['actions_deleted']}, maps={cleanup_result['external_maps_deleted']})."
                )
                creation_assignments = []
            elif sea_only_creation_assignments and args.allow_sea_only_creation_workflow:
                print(
                    "WARNING: --allow-sea-only-creation-workflow enabled for "
                    f"component {component_key}. This should be used only for "
                    "explicitly approved harvested/exception cohorts."
                )

        if creation_assignments:
            workflow_number = build_creation_workflow_number(batch.batch_number, component_key)
            workflow_map = get_external_map("PopulationComponentCreationWorkflow", component_key)
            if workflow_map:
                creation_workflow = BatchCreationWorkflow.objects.get(pk=workflow_map.target_object_id)
            else:
                creation_workflow = BatchCreationWorkflow.objects.filter(workflow_number=workflow_number).first()

            supplier_name = "FishTalk Legacy Supplier"
            egg_supplier = get_or_create_egg_supplier(
                supplier_name,
                history_user=history_user,
                history_reason=history_reason,
            )

            input_counts = data_source.get_input_counts([member.population_id for member, _ in creation_assignments])

            def resolve_egg_count(member: ComponentMember, assignment: BatchContainerAssignment) -> int:
                candidate = input_counts.get(member.population_id)
                if candidate and candidate > 0:
                    return int(round(candidate))
                return int(assignment.population_count or 0)

            total_eggs_planned = sum(
                resolve_egg_count(member, assignment) for member, assignment in creation_assignments
            )
            total_actions = len(creation_assignments)
            planned_start_date = min(member.start_time for member, _ in creation_assignments).date()
            planned_completion_date = max(member.start_time for member, _ in creation_assignments).date()
            progress_percentage = Decimal("100.00") if total_actions else Decimal("0.00")

            workflow_payload = {
                "workflow_number": workflow_number,
                "batch": batch,
                "status": "COMPLETED" if total_actions else "PLANNED",
                "egg_source_type": "EXTERNAL",
                "external_supplier": egg_supplier,
                "external_supplier_batch_number": str(component_key),
                "total_eggs_planned": total_eggs_planned,
                "total_eggs_received": total_eggs_planned,
                "total_mortality_on_arrival": 0,
                "planned_start_date": planned_start_date,
                "planned_completion_date": planned_completion_date,
                "actual_start_date": planned_start_date if total_actions else None,
                "actual_completion_date": planned_completion_date if total_actions else None,
                "total_actions": total_actions,
                "actions_completed": total_actions,
                "progress_percentage": progress_percentage,
                "created_by": history_user,
                "notes": f"Synthetic creation workflow from FishTalk component {component_key}",
            }

            if creation_workflow:
                for key, value in workflow_payload.items():
                    setattr(creation_workflow, key, value)
                save_with_history(creation_workflow, user=history_user, reason=history_reason)
            else:
                creation_workflow = BatchCreationWorkflow(**workflow_payload)
                save_with_history(creation_workflow, user=history_user, reason=history_reason)
            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model="PopulationComponentCreationWorkflow",
                source_identifier=str(component_key),
                defaults={
                    "target_app_label": creation_workflow._meta.app_label,
                    "target_model": creation_workflow._meta.model_name,
                    "target_object_id": creation_workflow.pk,
                    "metadata": {"batch_number": batch.batch_number},
                },
            )

            used_action_numbers = set(
                CreationAction.objects.filter(workflow=creation_workflow).values_list("action_number", flat=True)
            )
            next_action_number = 1

            def next_available_action_number() -> int:
                nonlocal next_action_number
                while next_action_number in used_action_numbers:
                    next_action_number += 1
                value = next_action_number
                used_action_numbers.add(value)
                next_action_number += 1
                return value

            for member, assignment in creation_assignments:
                action_map = get_external_map("PopulationCreationAction", member.population_id)
                if action_map:
                    creation_action = CreationAction.objects.get(pk=action_map.target_object_id)
                    same_workflow = creation_action.workflow_id == creation_workflow.pk
                    if same_workflow and creation_action.action_number:
                        action_number = creation_action.action_number
                    else:
                        # Re-mapped actions from another workflow cannot safely
                        # reuse their prior ordinal in this workflow.
                        action_number = next_available_action_number()
                else:
                    creation_action = None
                    action_number = next_available_action_number()

                egg_count = resolve_egg_count(member, assignment)
                action_payload = {
                    "workflow": creation_workflow,
                    "action_number": action_number,
                    "status": "COMPLETED" if total_actions else "PENDING",
                    "dest_assignment": assignment,
                    "egg_count_planned": egg_count,
                    "egg_count_actual": egg_count,
                    "mortality_on_arrival": 0,
                    "expected_delivery_date": member.start_time.date(),
                    "actual_delivery_date": member.start_time.date(),
                    "executed_by": history_user,
                    "notes": f"FishTalk PopulationID={member.population_id}",
                }

                if creation_action:
                    for key, value in action_payload.items():
                        setattr(creation_action, key, value)
                    save_with_history(creation_action, user=history_user, reason=history_reason)
                else:
                    creation_action = CreationAction(**action_payload)
                    save_with_history(creation_action, user=history_user, reason=history_reason)

                # Preserve creation-stage assignment counts when the assignment
                # build path flattened them to zero despite authoritative input
                # counts on the completed creation action.
                if egg_count > 0 and int(assignment.population_count or 0) <= 0:
                    assignment.population_count = egg_count
                    assignment.avg_weight_g = None
                    assignment.biomass_kg = Decimal("0.00")
                    save_with_history(assignment, user=history_user, reason=history_reason)

                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="PopulationCreationAction",
                    source_identifier=str(member.population_id),
                    defaults={
                        "target_app_label": creation_action._meta.app_label,
                        "target_model": creation_action._meta.model_name,
                        "target_object_id": creation_action.pk,
                        "metadata": {
                            "component_key": component_key,
                            "batch_number": batch.batch_number,
                        },
                    },
                )

        batch.status = batch_status
        batch.actual_end_date = batch_actual_end_date
        save_with_history(batch, user=history_user, reason=history_reason)

        print(f"Migrated component_key={component_key} into Batch(batch_number={batch.batch_number})")
        print(f"Assignments created/updated: {len(members)}")
        if lifecycle_fallback_population_ids:
            sample_ids = ", ".join(lifecycle_fallback_population_ids[:5])
            print(
                "Lifecycle-stage fallback applied to "
                f"{len(lifecycle_fallback_population_ids)} population(s) "
                f"using batch stage '{lifecycle_stage_name}'. "
                f"Sample IDs: {sample_ids}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
