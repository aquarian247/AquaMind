#!/usr/bin/env python3
# flake8: noqa
"""Migrate FishTalk growth model master data (TGC, FCR, Temperature) to AquaMind.

This script migrates:
- TemperatureTables + TemperatureTableEntries → TemperatureProfile + TemperatureReading
- GrowthModels + TGCTableEntries → TGCModel (with day-specific TGC values stored as average)
- GrowthModels + FCRTableEntries → FCRModel + FCRModelStage (weight→stage aggregation)
- Creates default MortalityModel if none exist

FishTalk schema note:
  - dbo.GrowthModels (120 rows) - Parent model with Comment field for name
  - dbo.TGCTableEntries (7,530 rows) - Day-specific TGC values per GrowthModelID
  - dbo.FCRTableEntries (8,639 rows) - Weight/Temperature-specific FCR values
  - dbo.TemperatureTables (20 rows) - Temperature profile definitions
  - dbo.TemperatureTableEntries (240 rows) - IntervalStart (day number), Temperature

Writes only to aquamind_db_migr_dev.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db

configure_migration_environment()

import django

django.setup()
assert_default_db_is_migration_db()

from django.db import transaction
from django.contrib.auth import get_user_model

from scripts.migration.history import save_with_history, get_or_create_with_history
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext
from apps.migration_support.models import ExternalIdMap

User = get_user_model()


# Weight-to-stage mapping for FCR aggregation
# Based on typical Atlantic salmon lifecycle weights
WEIGHT_TO_STAGE = [
    (0.0, 0.5, "Egg&Alevin"),      # ~0.1-0.5g - egg/alevin stage
    (0.5, 5.0, "Fry"),              # ~0.5-5g - fry stage
    (5.0, 30.0, "Parr"),            # ~5-30g - parr stage
    (30.0, 100.0, "Smolt"),         # ~30-100g - smolt stage
    (100.0, 500.0, "Post-Smolt"),   # ~100-500g - post-smolt
    (500.0, float('inf'), "Adult"), # 500g+ - adult/ongrowing
]

# Default duration in days for each stage
STAGE_DURATION_DAYS = {
    "Egg&Alevin": 90,
    "Fry": 60,
    "Parr": 120,
    "Smolt": 90,
    "Post-Smolt": 180,
    "Adult": 360,
}


def weight_to_stage(weight_g: float) -> str:
    """Map a weight in grams to a lifecycle stage name."""
    for min_w, max_w, stage in WEIGHT_TO_STAGE:
        if min_w <= weight_g < max_w:
            return stage
    return "Adult"  # Fallback


@dataclass
class FishTalkTemperatureTable:
    """FishTalk TemperatureTables row."""
    table_id: str
    registration_date: str
    table_mode: int
    interval_type: int
    table_start: str
    version: int


@dataclass
class FishTalkTemperatureEntry:
    """FishTalk TemperatureTableEntries row."""
    table_id: str
    interval_start: int  # Day number
    temperature: float


@dataclass
class FishTalkGrowthModel:
    """FishTalk GrowthModels row."""
    model_id: str
    comment: str  # Used as name
    growth_model_type: int
    low_limit: float
    high_limit: float
    active: bool
    fcr_model_type: int
    use_fcr_temp: bool


@dataclass
class FishTalkTGCEntry:
    """FishTalk TGCTableEntries row."""
    model_id: str
    day_number: int
    tgc: float


@dataclass
class FishTalkFCREntry:
    """FishTalk FCRTableEntries row."""
    model_id: str
    weight: float
    temperature: float
    fcr: float
    correction_factor: Optional[float]


class ScenarioModelExtractor(BaseExtractor):
    """Extractor for FishTalk growth model data."""

    def extract_temperature_tables(self) -> List[FishTalkTemperatureTable]:
        """Extract all temperature table definitions."""
        query = """
        SELECT
            CONVERT(NVARCHAR(36), TemperatureTableID) AS table_id,
            CONVERT(NVARCHAR(30), RegistrationDate, 126) AS registration_date,
            TableMode AS table_mode,
            IntervalType AS interval_type,
            CONVERT(NVARCHAR(30), TableStart, 126) AS table_start,
            Version AS version
        FROM dbo.TemperatureTables
        ORDER BY RegistrationDate
        """
        headers = ['table_id', 'registration_date', 'table_mode', 'interval_type', 'table_start', 'version']
        rows = self._run_sqlcmd(query, headers)
        
        results = []
        for row in rows:
            results.append(FishTalkTemperatureTable(
                table_id=row['table_id'],
                registration_date=row['registration_date'],
                table_mode=int(row['table_mode']) if row['table_mode'] else 0,
                interval_type=int(row['interval_type']) if row['interval_type'] else 0,
                table_start=row['table_start'],
                version=int(row['version']) if row['version'] else 0,
            ))
        return results

    def extract_temperature_entries(self) -> List[FishTalkTemperatureEntry]:
        """Extract all temperature table entries."""
        query = """
        SELECT
            CONVERT(NVARCHAR(36), TemperatureTableID) AS table_id,
            IntervalStart AS interval_start,
            Temperature AS temperature
        FROM dbo.TemperatureTableEntries
        ORDER BY TemperatureTableID, IntervalStart
        """
        headers = ['table_id', 'interval_start', 'temperature']
        rows = self._run_sqlcmd(query, headers)
        
        results = []
        for row in rows:
            results.append(FishTalkTemperatureEntry(
                table_id=row['table_id'],
                interval_start=int(row['interval_start']) if row['interval_start'] else 0,
                temperature=float(row['temperature']) if row['temperature'] else 0.0,
            ))
        return results

    def extract_growth_models(self) -> List[FishTalkGrowthModel]:
        """Extract all growth model definitions."""
        query = """
        SELECT
            CONVERT(NVARCHAR(36), GrowthModelID) AS model_id,
            ISNULL(Comment, 'Model_' + CONVERT(NVARCHAR(8), ROW_NUMBER() OVER (ORDER BY GrowthModelID))) AS comment,
            GrowthModelType AS growth_model_type,
            LowLimit AS low_limit,
            HighLimit AS high_limit,
            Active AS active,
            FCRModelType AS fcr_model_type,
            UseFCRTemp AS use_fcr_temp
        FROM dbo.GrowthModels
        WHERE Active = 1
        ORDER BY Comment
        """
        headers = ['model_id', 'comment', 'growth_model_type', 'low_limit', 'high_limit', 'active', 'fcr_model_type', 'use_fcr_temp']
        rows = self._run_sqlcmd(query, headers)
        
        results = []
        for row in rows:
            results.append(FishTalkGrowthModel(
                model_id=row['model_id'],
                comment=row['comment'] or f"Model_{row['model_id'][:8]}",
                growth_model_type=int(row['growth_model_type']) if row['growth_model_type'] else 0,
                low_limit=float(row['low_limit']) if row['low_limit'] else 0.0,
                high_limit=float(row['high_limit']) if row['high_limit'] else 0.0,
                active=row['active'] == '1' or row['active'].upper() == 'TRUE',
                fcr_model_type=int(row['fcr_model_type']) if row['fcr_model_type'] else 0,
                use_fcr_temp=row['use_fcr_temp'] == '1' or (row['use_fcr_temp'] or '').upper() == 'TRUE',
            ))
        return results

    def extract_tgc_entries(self) -> List[FishTalkTGCEntry]:
        """Extract all TGC table entries."""
        query = """
        SELECT
            CONVERT(NVARCHAR(36), GrowthModelID) AS model_id,
            DayNumber AS day_number,
            TGC AS tgc
        FROM dbo.TGCTableEntries
        ORDER BY GrowthModelID, DayNumber
        """
        headers = ['model_id', 'day_number', 'tgc']
        rows = self._run_sqlcmd(query, headers)
        
        results = []
        for row in rows:
            results.append(FishTalkTGCEntry(
                model_id=row['model_id'],
                day_number=int(row['day_number']) if row['day_number'] else 0,
                tgc=float(row['tgc']) if row['tgc'] else 0.0,
            ))
        return results

    def extract_fcr_entries(self) -> List[FishTalkFCREntry]:
        """Extract all FCR table entries."""
        query = """
        SELECT
            CONVERT(NVARCHAR(36), GrowthModelID) AS model_id,
            Weight AS weight,
            Temperature AS temperature,
            FCR AS fcr,
            CorrectionFactor AS correction_factor
        FROM dbo.FCRTableEntries
        ORDER BY GrowthModelID, Weight, Temperature
        """
        headers = ['model_id', 'weight', 'temperature', 'fcr', 'correction_factor']
        rows = self._run_sqlcmd(query, headers)
        
        results = []
        for row in rows:
            corr = None
            if row['correction_factor']:
                try:
                    corr = float(row['correction_factor'])
                except ValueError:
                    corr = None
            
            results.append(FishTalkFCREntry(
                model_id=row['model_id'],
                weight=float(row['weight']) if row['weight'] else 0.0,
                temperature=float(row['temperature']) if row['temperature'] else 0.0,
                fcr=float(row['fcr']) if row['fcr'] else 0.0,
                correction_factor=corr,
            ))
        return results


def get_or_create_external_map(
    source_model: str,
    source_identifier: str,
    target_app_label: str,
    target_model: str,
    target_object_id: int,
    metadata: Optional[dict] = None,
) -> Tuple[ExternalIdMap, bool]:
    """Get or create an ExternalIdMap entry."""
    existing = ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model=source_model,
        source_identifier=str(source_identifier),
    ).first()
    
    if existing:
        return existing, False
    
    entry = ExternalIdMap.objects.create(
        source_system="FishTalk",
        source_model=source_model,
        source_identifier=str(source_identifier),
        target_app_label=target_app_label,
        target_model=target_model,
        target_object_id=target_object_id,
        metadata=metadata or {},
    )
    return entry, True


def migrate_temperature_profiles(
    extractor: ScenarioModelExtractor,
    user,
    dry_run: bool = False,
) -> Dict[str, int]:
    """Migrate FishTalk TemperatureTables to AquaMind TemperatureProfile."""
    from apps.scenario.models import TemperatureProfile, TemperatureReading
    
    tables = extractor.extract_temperature_tables()
    entries = extractor.extract_temperature_entries()
    
    # Group entries by table_id
    entries_by_table: Dict[str, List[FishTalkTemperatureEntry]] = defaultdict(list)
    for entry in entries:
        entries_by_table[entry.table_id].append(entry)
    
    # Track FishTalk ID → AquaMind ID mapping
    id_map: Dict[str, int] = {}
    
    created_profiles = 0
    created_readings = 0
    skipped_profiles = 0
    
    for table in tables:
        # Check if already migrated
        existing_map = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="TemperatureTables",
            source_identifier=table.table_id,
        ).first()
        
        if existing_map:
            id_map[table.table_id] = existing_map.target_object_id
            skipped_profiles += 1
            continue
        
        # Generate a name from the table data
        profile_name = f"FT-TempProfile-{table.table_id[:8]}"
        
        if dry_run:
            print(f"  [DRY RUN] Would create TemperatureProfile: {profile_name}")
            created_profiles += 1
            continue
        
        # Create the profile
        profile, was_created = get_or_create_with_history(
            TemperatureProfile,
            lookup={"name": profile_name},
            defaults={},
            user=user,
            reason="FishTalk migration: TemperatureTables",
        )
        
        if was_created:
            created_profiles += 1
            
            # Register in ExternalIdMap
            get_or_create_external_map(
                source_model="TemperatureTables",
                source_identifier=table.table_id,
                target_app_label="scenario",
                target_model="TemperatureProfile",
                target_object_id=profile.profile_id,
                metadata={
                    "registration_date": table.registration_date,
                    "table_mode": table.table_mode,
                    "interval_type": table.interval_type,
                },
            )
            
            # Create readings for this profile
            table_entries = entries_by_table.get(table.table_id, [])
            for entry in table_entries:
                # IntervalStart is already a day number in FishTalk
                day_number = entry.interval_start if entry.interval_start > 0 else 1
                
                reading, reading_created = get_or_create_with_history(
                    TemperatureReading,
                    lookup={"profile": profile, "day_number": day_number},
                    defaults={"temperature": entry.temperature},
                    user=user,
                    reason="FishTalk migration: TemperatureTableEntries",
                )
                if reading_created:
                    created_readings += 1
        
        id_map[table.table_id] = profile.profile_id
    
    print(f"  Temperature Profiles: {created_profiles} created, {skipped_profiles} skipped")
    print(f"  Temperature Readings: {created_readings} created")
    
    return id_map


def migrate_tgc_models(
    extractor: ScenarioModelExtractor,
    growth_models: List[FishTalkGrowthModel],
    temp_profile_map: Dict[str, int],
    user,
    dry_run: bool = False,
) -> Dict[str, int]:
    """Migrate FishTalk GrowthModels + TGCTableEntries to AquaMind TGCModel."""
    from apps.scenario.models import TGCModel, TemperatureProfile
    
    tgc_entries = extractor.extract_tgc_entries()
    
    # Group TGC entries by model_id and compute average TGC
    tgc_by_model: Dict[str, List[float]] = defaultdict(list)
    for entry in tgc_entries:
        tgc_by_model[entry.model_id].append(entry.tgc)
    
    # Get a default temperature profile (first one if available)
    default_profile = TemperatureProfile.objects.first()
    if not default_profile and not dry_run:
        # Create a minimal default profile
        default_profile, _ = get_or_create_with_history(
            TemperatureProfile,
            lookup={"name": "Default Temperature Profile"},
            defaults={},
            user=user,
            reason="FishTalk migration: Default temperature profile for TGC models",
        )
    
    id_map: Dict[str, int] = {}
    created_models = 0
    skipped_models = 0
    
    for gm in growth_models:
        # Check if already migrated
        existing_map = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="GrowthModels_TGC",
            source_identifier=gm.model_id,
        ).first()
        
        if existing_map:
            id_map[gm.model_id] = existing_map.target_object_id
            skipped_models += 1
            continue
        
        # Calculate average TGC for this model
        tgc_values = tgc_by_model.get(gm.model_id, [])
        avg_tgc = sum(tgc_values) / len(tgc_values) if tgc_values else 0.025  # Default TGC
        
        # Generate model name
        model_name = gm.comment.strip() if gm.comment else f"FT-TGC-{gm.model_id[:8]}"
        model_name = f"FT-TGC-{model_name}"[:255]  # Ensure unique and within limit
        
        if dry_run:
            print(f"  [DRY RUN] Would create TGCModel: {model_name} (avg TGC: {avg_tgc:.4f})")
            created_models += 1
            continue
        
        # Use the first available temperature profile or default
        profile = default_profile
        
        # Create the TGC model
        tgc_model, was_created = get_or_create_with_history(
            TGCModel,
            lookup={"name": model_name},
            defaults={
                "location": "FishTalk Import",
                "release_period": "Year-round",
                "tgc_value": avg_tgc,
                "exponent_n": 0.33,  # Standard exponent
                "exponent_m": 0.66,  # Standard exponent
                "profile": profile,
            },
            user=user,
            reason="FishTalk migration: GrowthModels → TGCModel",
        )
        
        if was_created:
            created_models += 1
            
            # Register in ExternalIdMap
            get_or_create_external_map(
                source_model="GrowthModels_TGC",
                source_identifier=gm.model_id,
                target_app_label="scenario",
                target_model="TGCModel",
                target_object_id=tgc_model.model_id,
                metadata={
                    "original_comment": gm.comment,
                    "growth_model_type": gm.growth_model_type,
                    "tgc_entry_count": len(tgc_values),
                    "avg_tgc": avg_tgc,
                },
            )
        
        id_map[gm.model_id] = tgc_model.model_id
    
    print(f"  TGC Models: {created_models} created, {skipped_models} skipped")
    
    return id_map


def migrate_fcr_models(
    extractor: ScenarioModelExtractor,
    growth_models: List[FishTalkGrowthModel],
    user,
    dry_run: bool = False,
) -> Dict[str, int]:
    """Migrate FishTalk GrowthModels + FCRTableEntries to AquaMind FCRModel + FCRModelStage."""
    from apps.scenario.models import FCRModel, FCRModelStage
    from apps.batch.models import LifeCycleStage
    
    fcr_entries = extractor.extract_fcr_entries()
    
    # Group FCR entries by model_id and then by stage
    fcr_by_model_stage: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for entry in fcr_entries:
        stage = weight_to_stage(entry.weight)
        fcr_by_model_stage[entry.model_id][stage].append(entry.fcr)
    
    # Get lifecycle stages
    stage_objects: Dict[str, LifeCycleStage] = {}
    for stage in LifeCycleStage.objects.all():
        stage_objects[stage.name] = stage
    
    id_map: Dict[str, int] = {}
    created_models = 0
    created_stages = 0
    skipped_models = 0
    
    for gm in growth_models:
        # Check if already migrated
        existing_map = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="GrowthModels_FCR",
            source_identifier=gm.model_id,
        ).first()
        
        if existing_map:
            id_map[gm.model_id] = existing_map.target_object_id
            skipped_models += 1
            continue
        
        # Generate model name
        model_name = gm.comment.strip() if gm.comment else f"FT-FCR-{gm.model_id[:8]}"
        model_name = f"FT-FCR-{model_name}"[:255]
        
        if dry_run:
            stages_with_data = fcr_by_model_stage.get(gm.model_id, {})
            print(f"  [DRY RUN] Would create FCRModel: {model_name} ({len(stages_with_data)} stages)")
            created_models += 1
            continue
        
        # Create the FCR model
        fcr_model, was_created = get_or_create_with_history(
            FCRModel,
            lookup={"name": model_name},
            defaults={},
            user=user,
            reason="FishTalk migration: GrowthModels → FCRModel",
        )
        
        if was_created:
            created_models += 1
            
            # Register in ExternalIdMap
            get_or_create_external_map(
                source_model="GrowthModels_FCR",
                source_identifier=gm.model_id,
                target_app_label="scenario",
                target_model="FCRModel",
                target_object_id=fcr_model.model_id,
                metadata={
                    "original_comment": gm.comment,
                    "fcr_model_type": gm.fcr_model_type,
                },
            )
            
            # Create FCR stages based on aggregated weight data
            model_stages = fcr_by_model_stage.get(gm.model_id, {})
            
            for stage_name, fcr_values in model_stages.items():
                if stage_name not in stage_objects:
                    print(f"    [WARN] Stage '{stage_name}' not found in LifeCycleStage, skipping")
                    continue
                
                avg_fcr = sum(fcr_values) / len(fcr_values) if fcr_values else 1.2
                duration_days = STAGE_DURATION_DAYS.get(stage_name, 90)
                
                stage_obj, stage_created = get_or_create_with_history(
                    FCRModelStage,
                    lookup={"model": fcr_model, "stage": stage_objects[stage_name]},
                    defaults={
                        "fcr_value": avg_fcr,
                        "duration_days": duration_days,
                    },
                    user=user,
                    reason="FishTalk migration: FCRTableEntries → FCRModelStage",
                )
                if stage_created:
                    created_stages += 1
        
        id_map[gm.model_id] = fcr_model.model_id
    
    print(f"  FCR Models: {created_models} created, {skipped_models} skipped")
    print(f"  FCR Model Stages: {created_stages} created")
    
    return id_map


def migrate_mortality_models(user, dry_run: bool = False) -> Dict[str, int]:
    """Create default mortality models (FishTalk doesn't have dedicated mortality model tables)."""
    from apps.scenario.models import MortalityModel
    
    # Default mortality configurations
    default_mortalities = [
        {"name": "FT-Mortality-Low", "frequency": "daily", "rate": 0.01},
        {"name": "FT-Mortality-Standard", "frequency": "daily", "rate": 0.05},
        {"name": "FT-Mortality-High", "frequency": "daily", "rate": 0.10},
    ]
    
    id_map: Dict[str, int] = {}
    created_models = 0
    skipped_models = 0
    
    for config in default_mortalities:
        # Check if already exists
        existing = MortalityModel.objects.filter(name=config["name"]).first()
        if existing:
            id_map[config["name"]] = existing.model_id
            skipped_models += 1
            continue
        
        if dry_run:
            print(f"  [DRY RUN] Would create MortalityModel: {config['name']}")
            created_models += 1
            continue
        
        model, was_created = get_or_create_with_history(
            MortalityModel,
            lookup={"name": config["name"]},
            defaults={
                "frequency": config["frequency"],
                "rate": config["rate"],
            },
            user=user,
            reason="FishTalk migration: Default mortality model",
        )
        
        if was_created:
            created_models += 1
        
        id_map[config["name"]] = model.model_id
    
    print(f"  Mortality Models: {created_models} created, {skipped_models} skipped")
    
    return id_map


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate FishTalk growth model master data to AquaMind"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing to database",
    )
    parser.add_argument(
        "--skip-temperature",
        action="store_true",
        help="Skip temperature profile migration",
    )
    parser.add_argument(
        "--skip-tgc",
        action="store_true",
        help="Skip TGC model migration",
    )
    parser.add_argument(
        "--skip-fcr",
        action="store_true",
        help="Skip FCR model migration",
    )
    parser.add_argument(
        "--skip-mortality",
        action="store_true",
        help="Skip mortality model creation",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    
    print("\n" + "=" * 60)
    print("SCENARIO MODEL MIGRATION (FishTalk → AquaMind)")
    print("=" * 60)
    
    if args.dry_run:
        print("[DRY RUN MODE - No database changes will be made]")
    
    # Get migration user
    migration_user = User.objects.filter(username="system_admin").first()
    if not migration_user:
        migration_user = User.objects.filter(is_superuser=True).first()
    if not migration_user:
        print("[ERROR] No suitable migration user found")
        return 1
    
    print(f"\nMigration user: {migration_user.username}")
    
    # Create extractor
    context = ExtractionContext(profile="fishtalk_readonly")
    extractor = ScenarioModelExtractor(context)
    
    print(f"\nFishTalk connection: {extractor.info()}")
    
    # Track results
    results = {}
    
    with transaction.atomic():
        # 1. Migrate Temperature Profiles
        if not args.skip_temperature:
            print("\n[1/4] Migrating Temperature Profiles...")
            temp_profile_map = migrate_temperature_profiles(extractor, migration_user, args.dry_run)
            results["temperature_profiles"] = len(temp_profile_map)
        else:
            print("\n[1/4] Skipping Temperature Profiles (--skip-temperature)")
            temp_profile_map = {}
        
        # 2. Extract growth models (needed for TGC and FCR)
        print("\n[2/4] Extracting Growth Models from FishTalk...")
        growth_models = extractor.extract_growth_models()
        print(f"  Found {len(growth_models)} active growth models")
        
        # 3. Migrate TGC Models
        if not args.skip_tgc:
            print("\n[3/4] Migrating TGC Models...")
            tgc_model_map = migrate_tgc_models(
                extractor, growth_models, temp_profile_map, migration_user, args.dry_run
            )
            results["tgc_models"] = len(tgc_model_map)
        else:
            print("\n[3/4] Skipping TGC Models (--skip-tgc)")
        
        # 4. Migrate FCR Models
        if not args.skip_fcr:
            print("\n[4/4] Migrating FCR Models...")
            fcr_model_map = migrate_fcr_models(
                extractor, growth_models, migration_user, args.dry_run
            )
            results["fcr_models"] = len(fcr_model_map)
        else:
            print("\n[4/4] Skipping FCR Models (--skip-fcr)")
        
        # 5. Create default mortality models
        if not args.skip_mortality:
            print("\n[5/4] Creating Default Mortality Models...")
            mortality_map = migrate_mortality_models(migration_user, args.dry_run)
            results["mortality_models"] = len(mortality_map)
        else:
            print("\n[5/4] Skipping Mortality Models (--skip-mortality)")
        
        if args.dry_run:
            print("\n[DRY RUN] Rolling back transaction...")
            transaction.set_rollback(True)
    
    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    for key, count in results.items():
        print(f"  {key}: {count}")
    
    if args.dry_run:
        print("\n[DRY RUN] No changes were made to the database")
    else:
        print("\n[SUCCESS] Migration completed!")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
