#!/usr/bin/env python3
# flake8: noqa
"""Pilot migrate FishTalk transfers (movements) for one stitched population component.

This script supports two transfer data sources:
1. **SubTransfers (recommended)**: Active through 2025, use with --use-subtransfers
2. **PublicTransfers (legacy)**: Broken since Jan 2023, default for backward compatibility

SubTransfers tracks actual fish movements with granular population chains:
  - SourcePopBefore -> SourcePopAfter (remnant chain)
  - SourcePopBefore -> DestPopAfter (transfer to new location)

Target (AquaMind):
  - apps.batch.models.BatchTransferWorkflow (1 per FishTalk OperationID)
  - apps.batch.models.TransferAction (1 per FishTalk edge SourcePop->DestPop)

Important:
  - This is a *best-effort* backfill: FishTalk transfers can represent splits/merges;
    AquaMind TransferAction requires absolute transferred_count and biomass.
    We estimate using the source population snapshot near the operation time.
  - Assignment-derived synthetic stage-transition workflows/actions are disabled by
    default. Enable explicitly only for legacy diagnostics.

Writes only to aquamind_db_migr_dev.
"""

from __future__ import annotations

import argparse
import os
import sys
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
os.environ.setdefault("SKIP_CELERY_SIGNALS", "1")

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db

configure_migration_environment()

import django

django.setup()
assert_default_db_is_migration_db()

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.contrib.auth import get_user_model
from scripts.migration.history import save_with_history

from apps.batch.models import Batch, BatchTransferWorkflow, TransferAction, LifeCycleStage
from apps.batch.models.assignment import BatchContainerAssignment
from apps.migration_support.models import ExternalIdMap
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext
from scripts.migration.tools.etl_loader import ETLDataLoader
from scripts.migration.tools.population_assignment_mapping import get_assignment_external_map


User = get_user_model()

REPORT_DIR_DEFAULT = PROJECT_ROOT / "scripts" / "migration" / "output" / "population_stitching"


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None

    cleaned = value.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def ensure_aware(dt: datetime) -> datetime:
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt, dt_timezone.utc)


def to_decimal(value: object, *, places: str) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return Decimal(raw).quantize(Decimal(places))
    except Exception:
        return None


def get_external_map(
    source_model: str,
    source_identifier: str,
    *,
    component_key: str | None = None,
) -> ExternalIdMap | None:
    if source_model == "Populations":
        return get_assignment_external_map(
            str(source_identifier),
            component_key=component_key,
        )
    return ExternalIdMap.objects.filter(
        source_system="FishTalk", source_model=source_model, source_identifier=str(source_identifier)
    ).first()


def stage_at(events: list[tuple[datetime, str]], when: datetime) -> str:
    if not events:
        return ""
    if timezone.is_aware(when):
        when = timezone.make_naive(when)
    idx = bisect_right(events, (when, "\uffff")) - 1
    if idx < 0:
        return ""
    return events[idx][1]


def stage_slug(stage_name: str) -> str:
    return "".join(ch for ch in stage_name.upper() if ch.isalnum())[:4]


def fishtalk_stage_to_aquamind(stage_name: str) -> str | None:
    if not stage_name:
        return None
    upper = stage_name.upper()
    if any(token in upper for token in ("EGG", "ALEVIN", "SAC FRY", "GREEN EGG", "EYE-EGG")):
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
    if "BROODSTOCK" in upper:
        return "Adult"
    return None


STAGE_ORDER = ["Egg&Alevin", "Fry", "Parr", "Smolt", "Post-Smolt", "Adult"]
STAGE_INDEX = {name: idx for idx, name in enumerate(STAGE_ORDER)}


@dataclass(frozen=True)
class ComponentMember:
    population_id: str
    start_time: datetime
    end_time: datetime | None


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
            members.append(ComponentMember(population_id=row.get("population_id", ""), start_time=start, end_time=end))

    members.sort(key=lambda m: m.start_time)
    return members


def load_members_from_chain(chain_dir: Path, *, chain_id: str) -> list[ComponentMember]:
    """Load members from SubTransfers-based chain stitching output."""
    import csv

    path = chain_dir / "batch_chains.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing chain file: {path}")

    members: list[ComponentMember] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("chain_id") != chain_id:
                continue
            
            start = parse_dt(row.get("start_time", ""))
            if start is None:
                continue
            end = parse_dt(row.get("end_time", ""))
            members.append(ComponentMember(
                population_id=row.get("population_id", ""),
                start_time=start,
                end_time=end,
            ))

    members.sort(key=lambda m: m.start_time)
    return members


def load_subtransfers_from_csv(csv_dir: Path, population_ids: set[str]) -> list[dict]:
    """Load SubTransfers data from CSV for specified populations."""
    import csv
    
    path = csv_dir / "sub_transfers.csv"
    if not path.exists():
        return []
    
    transfers = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            src_before = row.get("SourcePopBefore", "")
            src_after = row.get("SourcePopAfter", "")
            dst_after = row.get("DestPopAfter", "")
            
            # Include if any involved population is in our set
            if src_before in population_ids or src_after in population_ids or dst_after in population_ids:
                transfers.append(row)
    
    return transfers


def load_stage_names_from_csv(csv_dir: Path) -> dict[str, str]:
    import csv

    path = csv_dir / "production_stages.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing production stages file: {path}")

    stage_name_by_id: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stage_id = (row.get("StageID") or "").strip()
            if not stage_id:
                continue
            stage_name_by_id[stage_id] = (row.get("StageName") or "").strip()

    return stage_name_by_id


def load_population_stages_from_csv(csv_dir: Path, population_ids: set[str]) -> list[dict]:
    import csv

    path = csv_dir / "population_stages.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing population stages file: {path}")

    rows: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id and pop_id in population_ids:
                rows.append(row)

    return rows


def build_status_snapshot_index(csv_dir: Path, population_ids: set[str]) -> dict[str, tuple[list[datetime], list[tuple[int, Decimal]]]]:
    import csv

    path = csv_dir / "status_values.csv"
    if not path.exists():
        return {}

    raw: dict[str, list[tuple[datetime, int, Decimal]]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if not pop_id or pop_id not in population_ids:
                continue
            ts = parse_dt(row.get("StatusTime", ""))
            if ts is None:
                continue
            ts = ensure_aware(ts)
            count_val = row.get("CurrentCount")
            biom_val = row.get("CurrentBiomassKg")
            try:
                count = int(float(count_val)) if count_val not in (None, "") else 0
            except ValueError:
                count = 0
            try:
                biomass = Decimal(str(biom_val)) if biom_val not in (None, "") else Decimal("0.00")
            except Exception:
                biomass = Decimal("0.00")
            raw.setdefault(pop_id, []).append((ts, count, biomass))

    index: dict[str, tuple[list[datetime], list[tuple[int, Decimal]]]] = {}
    for pop_id, items in raw.items():
        items.sort(key=lambda item: item[0])
        times = [item[0] for item in items]
        values = [(item[1], item[2]) for item in items]
        index[pop_id] = (times, values)

    return index


def lookup_status_snapshot_from_index(
    index: dict[str, tuple[list[datetime], list[tuple[int, Decimal]]]],
    population_id: str,
    at_time: datetime,
) -> tuple[int, Decimal]:
    if not index or population_id not in index:
        return 0, Decimal("0.00")
    times, values = index[population_id]
    if not times:
        return 0, Decimal("0.00")
    pos = bisect_right(times, at_time)
    if pos > 0:
        return values[pos - 1]
    if pos < len(values):
        return values[pos]
    return 0, Decimal("0.00")


def resolve_component_key(report_dir: Path, *, component_id: int | None, component_key: str | None) -> str:
    if component_key:
        return component_key
    if component_id is None:
        raise ValueError("Provide --component-id or --component-key")

    import csv

    path = report_dir / "population_members.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("component_id") == str(component_id) and row.get("component_key"):
                return row["component_key"]

    raise ValueError("Unable to resolve component_key from report")


def lookup_status_snapshot(extractor: BaseExtractor, *, population_id: str, at_time: datetime) -> tuple[int, Decimal]:
    ts = at_time.strftime("%Y-%m-%d %H:%M:%S")
    rows = extractor._run_sqlcmd(
        query=(
            "SELECT TOP 1 StatusTime, CurrentCount, CurrentBiomassKg "
            "FROM dbo.PublicStatusValues "
            f"WHERE PopulationID = '{population_id}' AND StatusTime <= '{ts}' "
            "ORDER BY StatusTime DESC"
        ),
        headers=["StatusTime", "CurrentCount", "CurrentBiomassKg"],
    )
    if not rows:
        rows = extractor._run_sqlcmd(
            query=(
                "SELECT TOP 1 StatusTime, CurrentCount, CurrentBiomassKg "
                "FROM dbo.PublicStatusValues "
                f"WHERE PopulationID = '{population_id}' AND StatusTime >= '{ts}' "
                "ORDER BY StatusTime ASC"
            ),
            headers=["StatusTime", "CurrentCount", "CurrentBiomassKg"],
        )

    count = 0
    biomass = Decimal("0.00")
    if rows:
        try:
            count = int(round(float(rows[0].get("CurrentCount") or 0)))
        except Exception:
            count = 0
        biomass = to_decimal(rows[0].get("CurrentBiomassKg"), places="0.01") or Decimal("0.00")

    return max(count, 0), biomass


def lookup_project_info(extractor: BaseExtractor, *, population_id: str) -> tuple[str | None, str | None, str | None]:
    rows = extractor._run_sqlcmd(
        query=(
            "SELECT ProjectNumber, InputYear, RunningNumber "
            "FROM dbo.Populations "
            f"WHERE PopulationID = '{population_id}'"
        ),
        headers=["ProjectNumber", "InputYear", "RunningNumber"],
    )
    if not rows:
        return None, None, None
    row = rows[0]
    project_number = (row.get("ProjectNumber") or "").strip() or None
    input_year = (row.get("InputYear") or "").strip() or None
    running_number = (row.get("RunningNumber") or "").strip() or None
    return project_number, input_year, running_number


CHAIN_DIR_DEFAULT = PROJECT_ROOT / "scripts" / "migration" / "output" / "chain_stitching"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pilot migrate transfer workflows/actions for a stitched FishTalk component",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Transfer data sources:
  --use-subtransfers: Use SubTransfers table (active through 2025, recommended for 2020+)
  Default: Use PublicTransfers (broken since Jan 2023, legacy only)
        """,
    )
    
    # SubTransfers-based stitching (recommended)
    chain_group = parser.add_argument_group("SubTransfers-based stitching (recommended)")
    chain_group.add_argument(
        "--chain-id",
        help="Chain ID from scripts/migration/legacy/tools/subtransfer_chain_stitching.py (deprecated)",
    )
    chain_group.add_argument(
        "--chain-dir",
        default=str(CHAIN_DIR_DEFAULT),
        help="Directory containing batch_chains.csv from scripts/migration/legacy/tools/subtransfer_chain_stitching.py (deprecated)",
    )
    
    # Project-based stitching (legacy)
    legacy_group = parser.add_argument_group("Project-based stitching (legacy)")
    legacy_group.add_argument("--component-id", type=int, help="Component id from components.csv")
    legacy_group.add_argument("--component-key", help="Stable component_key from components.csv")
    legacy_group.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    
    # Transfer data source options
    parser.add_argument(
        "--use-subtransfers",
        action="store_true",
        help="Use SubTransfers table instead of PublicTransfers (recommended for 2020+ batches)",
    )
    synthetic_group = parser.add_mutually_exclusive_group()
    synthetic_group.add_argument(
        "--skip-synthetic-stage-transitions",
        dest="skip_synthetic_stage_transitions",
        action="store_true",
        help=(
            "Default behavior. Do not synthesize assignment-derived "
            "PopulationStageTransition workflows/actions; keep only transfer-edge-backed "
            "workflows/actions."
        ),
    )
    synthetic_group.add_argument(
        "--include-synthetic-stage-transitions",
        dest="skip_synthetic_stage_transitions",
        action="store_false",
        help=(
            "Legacy override. Synthesize assignment-derived PopulationStageTransition "
            "workflows/actions."
        ),
    )
    parser.set_defaults(skip_synthetic_stage_transitions=True)
    parser.add_argument("--sql-profile", default="fishtalk_readonly", help="FishTalk SQL Server profile")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    parser.add_argument(
        "--use-csv",
        type=str,
        metavar="CSV_DIR",
        help="Use pre-extracted CSV files from this directory instead of live SQL",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.skip_synthetic_stage_transitions:
        print(
            "Synthetic stage-transition workflows/actions disabled "
            "(default migration guardrail)."
        )
    else:
        print(
            "WARNING: synthetic stage-transition workflows/actions enabled "
            "via --include-synthetic-stage-transitions."
        )
    
    # Determine which stitching approach to use
    use_chain_stitching = args.chain_id is not None
    use_project_stitching = args.component_id is not None or args.component_key is not None
    
    if not use_chain_stitching and not use_project_stitching:
        raise SystemExit(
            "Provide either:\n"
            "  SubTransfers-based: --chain-id CHAIN-00001\n"
            "  Project-based: --component-id or --component-key"
        )
    
    if use_chain_stitching and use_project_stitching:
        raise SystemExit("Cannot use both --chain-id and --component-id/--component-key")
    
    # Load members based on stitching approach
    if use_chain_stitching:
        chain_dir = Path(args.chain_dir)
        members = load_members_from_chain(chain_dir, chain_id=args.chain_id)
        if not members:
            raise SystemExit(f"No members found for chain {args.chain_id}")
        component_key = f"chain:{args.chain_id}"
        print(f"Loaded {len(members)} populations from chain {args.chain_id}")
        
        # For chain-based, default to SubTransfers
        if not args.use_subtransfers:
            print("Note: Using --use-subtransfers by default for chain-based stitching")
            args.use_subtransfers = True
    else:
        report_dir = Path(args.report_dir)
        component_key = resolve_component_key(report_dir, component_id=args.component_id, component_key=args.component_key)
        members = load_members_from_report(report_dir, component_id=args.component_id, component_key=component_key)
        if not members:
            raise SystemExit("No members found for the selected component")

    batch_map = get_external_map("PopulationComponent", component_key)
    if not batch_map:
        raise SystemExit(
            f"Missing ExternalIdMap for PopulationComponent {component_key}. "
            "Run scripts/migration/tools/pilot_migrate_component.py first."
        )
    batch = Batch.objects.get(pk=batch_map.target_object_id)

    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not user:
        raise SystemExit("No users exist in AquaMind DB; cannot create transfer workflows")

    population_ids = sorted({m.population_id for m in members if m.population_id})
    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.now()) for m in members)

    extractor = None if args.use_csv else BaseExtractor(ExtractionContext(profile=args.sql_profile))

    # For chain-based stitching, skip project lookup (not relevant)
    project_number, input_year, running_number = None, None, None
    if not use_chain_stitching and not args.use_csv:
        project_number, input_year, running_number = lookup_project_info(
            extractor, population_id=component_key
        )

    in_clause = ",".join(f"'{pid}'" for pid in population_ids)
    start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = window_end.strftime("%Y-%m-%d %H:%M:%S")
    pop_id_set = set(population_ids)
    status_index = build_status_snapshot_index(Path(args.use_csv), pop_id_set) if args.use_csv else {}

    # Load transfers from appropriate source
    if args.use_subtransfers:
        # Use SubTransfers (recommended for 2020+)
        if args.use_csv:
            # Load from CSV
            csv_dir = Path(args.use_csv)
            raw_transfers = load_subtransfers_from_csv(csv_dir, pop_id_set)
            # Convert to consistent format
            transfer_rows = []
            for row in raw_transfers:
                # SubTransfers has SourcePopBefore, SourcePopAfter, DestPopAfter
                # For transfer workflows, we care about SourcePopBefore -> DestPopAfter
                src = row.get("SourcePopBefore", "")
                dst = row.get("DestPopAfter", "")
                if src and dst and src in pop_id_set and dst in pop_id_set:
                    transfer_rows.append({
                        "OperationID": row.get("OperationID", ""),
                        "OperationStartTime": row.get("OperationTime", ""),
                        "SourcePop": src,
                        "DestPop": dst,
                        "ShareCountForward": row.get("ShareCountFwd", ""),
                        "ShareBiomassForward": row.get("ShareBiomFwd", ""),
                    })
            print(f"Loaded {len(transfer_rows)} SubTransfers edges from CSV")
        else:
            # Query from SQL
            transfer_rows = extractor._run_sqlcmd(
                query=(
                    "SELECT st.OperationID, "
                    "CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime, "
                    "CONVERT(varchar(36), st.SourcePopBefore) AS SourcePop, "
                    "CONVERT(varchar(36), st.DestPopAfter) AS DestPop, "
                    "CONVERT(varchar(64), st.ShareCountFwd) AS ShareCountForward, "
                    "CONVERT(varchar(64), st.ShareBiomFwd) AS ShareBiomassForward "
                    "FROM dbo.SubTransfers st "
                    "JOIN dbo.Operations o ON o.OperationID = st.OperationID "
                    f"WHERE st.SourcePopBefore IN ({in_clause}) "
                    f"AND st.DestPopAfter IN ({in_clause}) "
                    f"AND o.StartTime >= '{start_str}' AND o.StartTime <= '{end_str}' "
                    "ORDER BY o.StartTime ASC"
                ),
                headers=[
                    "OperationID",
                    "OperationStartTime",
                    "SourcePop",
                    "DestPop",
                    "ShareCountForward",
                    "ShareBiomassForward",
                ],
            )
            print(f"Loaded {len(transfer_rows)} SubTransfers edges from SQL")
    else:
        # Use PublicTransfers (legacy, broken since Jan 2023)
        transfer_rows = extractor._run_sqlcmd(
            query=(
                "SELECT pt.OperationID, "
                "CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime, "
                "CONVERT(varchar(36), pt.SourcePop) AS SourcePop, "
                "CONVERT(varchar(36), pt.DestPop) AS DestPop, "
                "CONVERT(varchar(64), pt.ShareCountForward) AS ShareCountForward, "
                "CONVERT(varchar(64), pt.ShareBiomassForward) AS ShareBiomassForward "
                "FROM dbo.PublicTransfers pt "
                "JOIN dbo.Operations o ON o.OperationID = pt.OperationID "
                f"WHERE (pt.SourcePop IN ({in_clause}) OR pt.DestPop IN ({in_clause})) "
                f"AND o.StartTime >= '{start_str}' AND o.StartTime <= '{end_str}' "
                "ORDER BY o.StartTime ASC"
            ),
            headers=[
                "OperationID",
                "OperationStartTime",
                "SourcePop",
                "DestPop",
                "ShareCountForward",
                "ShareBiomassForward",
            ],
        )
        print(f"Loaded {len(transfer_rows)} PublicTransfers edges from SQL")

    if args.use_csv:
        csv_dir = Path(args.use_csv)
        stage_name_by_id = load_stage_names_from_csv(csv_dir)
        stage_events_raw = load_population_stages_from_csv(csv_dir, pop_id_set)
    else:
        stages_raw = extractor._run_sqlcmd(
            query="SELECT StageID, StageName FROM dbo.ProductionStages",
            headers=["StageID", "StageName"],
        )
        stage_name_by_id = {row["StageID"]: (row.get("StageName", "") or "").strip() for row in stages_raw}

        stage_events_raw = extractor._run_sqlcmd(
            query=(
                "SELECT pps.PopulationID, pps.StageID, pps.StartTime "
                "FROM dbo.PopulationProductionStages pps "
                + (
                    "JOIN dbo.Populations p ON p.PopulationID = pps.PopulationID "
                    f"WHERE p.ProjectNumber = '{project_number}' "
                    f"AND p.InputYear = '{input_year}' "
                    f"AND p.RunningNumber = '{running_number}'"
                    if project_number and input_year and running_number
                    else f"WHERE pps.PopulationID IN ({in_clause})"
                )
            ),
            headers=["PopulationID", "StageID", "StartTime"],
        )

    stage_events: dict[str, list[tuple[datetime, str]]] = {}
    for row in stage_events_raw:
        ts = parse_dt(row.get("StartTime", ""))
        if ts is None:
            continue
        stage_name = stage_name_by_id.get(row.get("StageID", ""), "")
        stage_events.setdefault(row["PopulationID"], []).append((ts, stage_name))
    for pop_id, events in stage_events.items():
        events.sort(key=lambda item: item[0])

    transitions_by_pair: dict[tuple[str, str], list[BatchContainerAssignment]] = {}

    # Keep only internal edges (both endpoints in component) to avoid linking outside batches.
    transfer_rows = [
        row
        for row in transfer_rows
        if (row.get("SourcePop") in population_ids and row.get("DestPop") in population_ids)
    ]

    if args.dry_run:
        print(f"[dry-run] Would migrate {len(transfer_rows)} PublicTransfers edges into batch={batch.batch_number}")
        return 0

    assignment_by_pop: dict[str, BatchContainerAssignment] = {}
    for pid in population_ids:
        mapped = get_external_map("Populations", pid, component_key=component_key)
        if mapped:
            assignment_by_pop[pid] = BatchContainerAssignment.objects.get(pk=mapped.target_object_id)

    # Group edges by operation.
    by_op: dict[str, list[dict[str, str]]] = {}
    for row in transfer_rows:
        op_id = (row.get("OperationID") or "").strip()
        if not op_id:
            continue
        by_op.setdefault(op_id, []).append(row)

    created_wf = updated_wf = created_actions = updated_actions = skipped = 0
    created_stage_wf = updated_stage_wf = created_stage_actions = updated_stage_actions = skipped_stage = 0

    with transaction.atomic():
        history_user = user
        history_reason = f"FishTalk migration: transfers for component {component_key}"
        stage_prefix = f"{component_key}:"
        stage_wf_ids = list(
            ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="PopulationStageTransition",
                source_identifier__startswith=stage_prefix,
            ).values_list("target_object_id", flat=True)
        )
        if stage_wf_ids:
            BatchTransferWorkflow.objects.filter(pk__in=stage_wf_ids).delete()
            ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model__in=["PopulationStageTransition", "PopulationStageTransitionAction"],
                source_identifier__startswith=stage_prefix,
            ).delete()

        for op_id, edges in by_op.items():
            op_time = parse_dt(edges[0].get("OperationStartTime") or "")
            if op_time is None:
                skipped += len(edges)
                continue
            op_time = ensure_aware(op_time)
            op_date = op_time.date()

            # Pick lifecycle stage context from the first source/dest assignment.
            source_stage = None
            dest_stage = None
            source_stage_name = None
            dest_stage_name = None
            for edge in edges:
                src = (edge.get("SourcePop") or "").strip()
                dst = (edge.get("DestPop") or "").strip()
                if not source_stage and src in assignment_by_pop:
                    source_stage = assignment_by_pop[src].lifecycle_stage
                if not dest_stage and dst in assignment_by_pop:
                    dest_stage = assignment_by_pop[dst].lifecycle_stage
                if not source_stage_name and src in stage_events:
                    source_stage_name = stage_at(stage_events.get(src, []), op_time)
                if not dest_stage_name and dst in stage_events:
                    dest_stage_name = stage_at(stage_events.get(dst, []), op_time)
            source_stage = source_stage or LifeCycleStage.objects.first()
            if source_stage is None:
                raise SystemExit("Missing LifeCycleStage master data")

            if source_stage_name:
                mapped_name = fishtalk_stage_to_aquamind(source_stage_name)
                if mapped_name:
                    source_stage = LifeCycleStage.objects.filter(name=mapped_name).first() or source_stage
            if dest_stage_name:
                mapped_name = fishtalk_stage_to_aquamind(dest_stage_name)
                if mapped_name:
                    dest_stage = LifeCycleStage.objects.filter(name=mapped_name).first() or dest_stage

            workflow_type = "CONTAINER_REDISTRIBUTION"
            if dest_stage and source_stage and getattr(dest_stage, "id", None) != getattr(source_stage, "id", None):
                workflow_type = "LIFECYCLE_TRANSITION"

            wf_map = get_external_map("TransferOperation", op_id)
            if wf_map:
                workflow = BatchTransferWorkflow.objects.get(pk=wf_map.target_object_id)
                # Don't overwrite user-entered notes; just keep FishTalk reference.
                workflow.planned_start_date = op_date
                workflow.source_lifecycle_stage = source_stage
                workflow.dest_lifecycle_stage = dest_stage
                workflow.workflow_type = workflow_type
                save_with_history(workflow, user=history_user, reason=history_reason)
                updated_wf += 1
            else:
                wf_number = f"FT-TRF-{op_date.strftime('%Y%m%d')}-{op_id[:8]}"[:50]
                workflow = BatchTransferWorkflow(
                    workflow_number=wf_number,
                    batch=batch,
                    workflow_type=workflow_type,
                    source_lifecycle_stage=source_stage,
                    dest_lifecycle_stage=dest_stage,
                    status="DRAFT",
                    planned_start_date=op_date,
                    planned_completion_date=op_date,
                    initiated_by=user,
                    notes=f"FishTalk OperationID={op_id}",
                )
                save_with_history(workflow, user=history_user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="TransferOperation",
                    source_identifier=str(op_id),
                    defaults={
                        "target_app_label": workflow._meta.app_label,
                        "target_model": workflow._meta.model_name,
                        "target_object_id": workflow.pk,
                        "metadata": {"operation_start_time": edges[0].get("OperationStartTime")},
                    },
                )
                created_wf += 1

            # Build per-source snapshot so multiple edges from same source are sequentially allocated.
            edges_sorted = sorted(
                edges,
                key=lambda e: (
                    (e.get("SourcePop") or ""),
                    # Desc by max share to allocate larger first
                    -(float(e.get("ShareBiomassForward") or 0) if str(e.get("ShareBiomassForward") or "").strip() else 0.0),
                    (e.get("DestPop") or ""),
                ),
            )

            source_remaining: dict[str, tuple[int, Decimal]] = {}

            max_action_number = (
                workflow.actions.aggregate(max_action_number=Max("action_number"))[
                    "max_action_number"
                ]
                or 0
            )

            for idx, edge in enumerate(edges_sorted, start=max_action_number + 1):
                src = (edge.get("SourcePop") or "").strip()
                dst = (edge.get("DestPop") or "").strip()
                if not src or not dst:
                    skipped += 1
                    continue
                if src not in assignment_by_pop or dst not in assignment_by_pop:
                    skipped += 1
                    continue

                if src not in source_remaining:
                    if args.use_csv:
                        source_remaining[src] = lookup_status_snapshot_from_index(
                            status_index, population_id=src, at_time=op_time
                        )
                    else:
                        source_remaining[src] = lookup_status_snapshot(extractor, population_id=src, at_time=op_time)

                src_count_before, src_biomass_before = source_remaining[src]

                share_count = float(edge.get("ShareCountForward") or 0) if str(edge.get("ShareCountForward") or "").strip() else 0.0
                share_biom = float(edge.get("ShareBiomassForward") or 0) if str(edge.get("ShareBiomassForward") or "").strip() else 0.0
                share_count = max(0.0, min(1.0, share_count))
                share_biom = max(0.0, min(1.0, share_biom))

                est_count = int(round(src_count_before * (share_count or share_biom))) if src_count_before > 0 else 0
                if est_count <= 0 and (share_count > 0 or share_biom > 0) and src_count_before > 0:
                    est_count = 1
                est_count = min(est_count, src_count_before) if src_count_before > 0 else est_count

                est_biomass = (src_biomass_before * Decimal(str(share_biom or share_count))).quantize(Decimal("0.01")) if src_biomass_before > 0 else Decimal("0.00")

                # Sequentially reduce remaining for this source to avoid double-counting.
                new_src_count = max(0, src_count_before - est_count)
                new_src_biomass = max(Decimal("0.00"), (src_biomass_before - est_biomass).quantize(Decimal("0.01")))
                source_remaining[src] = (new_src_count, new_src_biomass)

                if est_count <= 0:
                    skipped += 1
                    continue

                action_identifier = f"{op_id}:{src}:{dst}"
                action_map = get_external_map("PublicTransferEdge", action_identifier)

                defaults = {
                    "workflow": workflow,
                    "action_number": idx,
                    "source_assignment": assignment_by_pop[src],
                    "dest_assignment": assignment_by_pop[dst],
                    "source_population_before": max(src_count_before, est_count),
                    "transferred_count": est_count,
                    "mortality_during_transfer": 0,
                    "transferred_biomass_kg": est_biomass,
                    "allow_mixed": False,
                    "status": "COMPLETED",
                    "planned_date": op_date,
                    "actual_execution_date": op_date,
                    "transfer_method": None,
                    "notes": f"FishTalk OperationID={op_id}; share_count={share_count}; share_biomass={share_biom}",
                }

                if action_map:
                    action = TransferAction.objects.get(pk=action_map.target_object_id)
                    for k, v in defaults.items():
                        setattr(action, k, v)
                    save_with_history(action, user=history_user, reason=history_reason)
                    updated_actions += 1
                else:
                    action_number = defaults["action_number"]
                    while TransferAction.objects.filter(
                        workflow=workflow, action_number=action_number
                    ).exists():
                        action_number += 1
                    defaults["action_number"] = action_number
                    action = TransferAction(**defaults)
                    save_with_history(action, user=history_user, reason=history_reason)
                    ExternalIdMap.objects.update_or_create(
                        source_system="FishTalk",
                        source_model="PublicTransferEdge",
                        source_identifier=action_identifier,
                        defaults={
                            "target_app_label": action._meta.app_label,
                            "target_model": action._meta.model_name,
                            "target_object_id": action.pk,
                            "metadata": {"operation_id": op_id, "source_pop": src, "dest_pop": dst},
                        },
                    )
                    created_actions += 1

            # Finalize workflow summary.
            workflow.total_actions_planned = workflow.actions.count()
            workflow.actions_completed = workflow.actions.filter(status="COMPLETED").count()
            workflow.completion_percentage = Decimal("100.00") if workflow.total_actions_planned else Decimal("0.00")
            workflow.actual_start_date = op_date
            workflow.actual_completion_date = op_date
            workflow.status = "COMPLETED" if workflow.total_actions_planned else workflow.status
            workflow.completed_by = user
            save_with_history(workflow, user=history_user, reason=history_reason)
            workflow.recalculate_totals()

        stage_assignments: dict[str, list[BatchContainerAssignment]] = {}
        if not args.skip_synthetic_stage_transitions:
            for assignment in batch.batch_assignments.select_related("lifecycle_stage"):
                if assignment.lifecycle_stage and assignment.lifecycle_stage.name in STAGE_INDEX:
                    stage_assignments.setdefault(assignment.lifecycle_stage.name, []).append(assignment)

        stage_start_dates: dict[str, datetime.date] = {}
        for stage_name, assignments in stage_assignments.items():
            stage_start_dates[stage_name] = min(a.assignment_date for a in assignments)

        ordered_stages = [name for name in STAGE_ORDER if name in stage_start_dates]
        transitions_by_pair = {}
        for idx in range(1, len(ordered_stages)):
            from_stage = ordered_stages[idx - 1]
            to_stage = ordered_stages[idx]
            transitions_by_pair[(from_stage, to_stage)] = list(stage_assignments.get(to_stage, []))

        for (from_stage_name, to_stage_name), transitions in transitions_by_pair.items():
            source_stage = LifeCycleStage.objects.filter(name=from_stage_name).first()
            dest_stage = LifeCycleStage.objects.filter(name=to_stage_name).first()
            if not source_stage or not dest_stage:
                skipped_stage += len(transitions)
                continue

            if not transitions:
                continue

            transition_times = [ensure_aware(datetime.combine(t.assignment_date, datetime.min.time())) for t in transitions]
            min_time = min(transition_times)
            max_time = max(transition_times)
            op_date = min_time.date()

            transition_identifier = f"{component_key}:{from_stage_name}:{to_stage_name}"
            wf_number = (
                f"FT-STG-{op_date.strftime('%Y%m%d')}-{stage_slug(from_stage_name)}-"
                f"{stage_slug(to_stage_name)}-{component_key[:6]}"
            )[:50]
            workflow = BatchTransferWorkflow(
                workflow_number=wf_number,
                batch=batch,
                workflow_type="LIFECYCLE_TRANSITION",
                source_lifecycle_stage=source_stage,
                dest_lifecycle_stage=dest_stage,
                status="COMPLETED",
                planned_start_date=min_time.date(),
                planned_completion_date=max_time.date(),
                actual_start_date=min_time.date(),
                actual_completion_date=max_time.date(),
                initiated_by=user,
                completed_by=user,
                notes=f"FishTalk stage transition {from_stage_name}→{to_stage_name}; component={component_key}",
            )
            save_with_history(workflow, user=history_user, reason=history_reason)
            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model="PopulationStageTransition",
                source_identifier=transition_identifier,
                defaults={
                    "target_app_label": workflow._meta.app_label,
                    "target_model": workflow._meta.model_name,
                    "target_object_id": workflow.pk,
                    "metadata": {
                        "from_stage": from_stage_name,
                        "to_stage": to_stage_name,
                        "transition_start": min_time.isoformat(),
                        "transition_end": max_time.isoformat(),
                    },
                },
            )
            created_stage_wf += 1

            action_number = 1
            from_assignments_sorted = sorted(
                stage_assignments.get(from_stage_name, []),
                key=lambda a: a.assignment_date,
            )
            for dest_assignment, transition_time in zip(transitions, transition_times):
                source_assignment = None
                for candidate in from_assignments_sorted:
                    if candidate.assignment_date <= dest_assignment.assignment_date:
                        source_assignment = candidate
                    else:
                        break
                if source_assignment is None:
                    source_assignment = dest_assignment

                count = dest_assignment.population_count or 0
                biomass = dest_assignment.biomass_kg or Decimal("0.00")
                action_identifier = f"{transition_identifier}:{dest_assignment.pk}"
                action_defaults = {
                    "workflow": workflow,
                    "action_number": action_number,
                    "source_assignment": source_assignment,
                    "dest_assignment": dest_assignment,
                    "source_population_before": max(count, 0),
                    "transferred_count": max(count, 0),
                    "mortality_during_transfer": 0,
                    "transferred_biomass_kg": biomass,
                    "allow_mixed": False,
                    "status": "COMPLETED",
                    "planned_date": transition_time.date(),
                    "actual_execution_date": transition_time.date(),
                    "transfer_method": None,
                    "notes": (
                        f"FishTalk stage transition {from_stage_name}→{to_stage_name}; "
                        f"DestAssignment={dest_assignment.pk}"
                    ),
                }

                action = TransferAction(**action_defaults)
                save_with_history(action, user=history_user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="PopulationStageTransitionAction",
                    source_identifier=action_identifier,
                    defaults={
                        "target_app_label": action._meta.app_label,
                        "target_model": action._meta.model_name,
                        "target_object_id": action.pk,
                        "metadata": {
                            "assignment_id": dest_assignment.pk,
                            "from_stage": from_stage_name,
                            "to_stage": to_stage_name,
                        },
                    },
                )
                created_stage_actions += 1
                action_number += 1

            workflow.total_actions_planned = workflow.actions.count()
            workflow.actions_completed = workflow.actions.filter(status="COMPLETED").count()
            workflow.completion_percentage = Decimal("100.00") if workflow.total_actions_planned else Decimal("0.00")
            workflow.status = "COMPLETED" if workflow.total_actions_planned else workflow.status
            save_with_history(workflow, user=history_user, reason=history_reason)
            workflow.recalculate_totals()

    if args.skip_synthetic_stage_transitions:
        print("Skipped synthetic PopulationStageTransition workflow/action generation (--skip-synthetic-stage-transitions).")

    print(
        f"Migrated transfers for component_key={component_key} into batch={batch.batch_number} "
        f"(workflows created={created_wf}, updated={updated_wf}; actions created={created_actions}, updated={updated_actions}, skipped={skipped}; "
        f"stage workflows created={created_stage_wf}, updated={updated_stage_wf}; "
        f"stage actions created={created_stage_actions}, updated={updated_stage_actions}, skipped={skipped_stage})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
