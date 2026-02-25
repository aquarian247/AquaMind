#!/usr/bin/env python3
"""
Batch Generation Schedule Planner

Creates deterministic, conflict-free schedule for test data generation.
Eliminates race conditions by pre-allocating all containers.

Key Features:
- Pre-allocated containers (no runtime queries)
- Variable sea ring allocation (10-20 per batch, default 20)
- Multi-batch area packing (2+ batches per area when beneficial)
- 100% deterministic (same schedule → same data)
- Supports migration testing (reproducible)

Usage:
    # Generate schedule for 250 batches
    python generate_batch_schedule.py --batches 125 --output config/schedule_250.yaml
    
    # Dry run (just validate, don't save)
    python generate_batch_schedule.py --batches 125 --dry-run
"""
import os
import sys
import django
import yaml
import argparse
import csv
import re
from datetime import date, timedelta
from pathlib import Path
import random  # Used only for harvest target variation (deterministic via seed in schedule)
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import unicodedata

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.infrastructure.models import Geography, FreshwaterStation, Hall, Area, Container
from apps.batch.models import LifeCycleStage

HOLDING_ROLE = "HOLDING"


class BatchSchedulePlanner:
    """
    Plans deterministic batch generation schedule with optimal container utilization.
    """

    FW_NAME_PREFIXES = ("BAKKAFROST", "STOFNFISKUR", "BENCHMARK")
    SEA_NAME_PREFIXES = ("VAR", "SUMMAR", "HEYST", "VETUR")
    
    def __init__(
        self,
        batches_per_geo=125,
        target_saturation=0.85,
        stagger_days=5,
        adult_duration=450,
        reference_pack_dir=None,
    ):
        self.batches_per_geo = batches_per_geo
        self.target_saturation = target_saturation
        self.stagger_days = stagger_days
        self.adult_duration = adult_duration
        self.reference_pack_dir = Path(reference_pack_dir).resolve() if reference_pack_dir else None
        self.reference_pack_enabled = self.reference_pack_dir is not None
        self.occupancy = defaultdict(list)  # {container_name: [(start_day, end_day, batch_id), ...]}
        self.schedule = []
        self.reference_halls_by_geo_stage: Dict[str, Dict[str, List[Hall]]] = {}
        self.reference_batch_names_by_geo: Dict[str, List[str]] = {}
        self.reference_sea_batch_names_by_geo: Dict[str, List[str]] = {}
        self._batch_name_usage: Dict[str, int] = defaultdict(int)
        self._scheduled_batch_names: Set[str] = set()
        self._sea_batch_name_usage: Dict[str, int] = defaultdict(int)
        self._scheduled_sea_batch_names: Set[str] = set()

        # Stage durations (from event engine)
        self.stage_durations = {
            'Egg&Alevin': 90,
            'Fry': 90,
            'Parr': 90,
            'Smolt': 90,
            'Post-Smolt': 90,
            'Adult': adult_duration
        }

        # Weight-based harvest parameters (from event engine)
        # Get actual TGC and temperature from database models
        tgc_adult, temp_sea = self._get_adult_tgc_and_temp()
        self.harvest_targets = {
            'min_weight_kg': 4.5,  # Minimum harvest weight
            'max_weight_kg': 6.5,  # Maximum harvest weight
            'adult_start_weight_g': 450,  # Weight when entering Adult stage
            'tgc_adult': tgc_adult,  # Adult stage TGC value from database
            'temp_sea_c': temp_sea   # Sea temperature from database
        }
    
    def _get_adult_tgc_and_temp(self):
        """
        Get actual Adult stage TGC value and sea temperature from database models.
        Falls back to defaults if models not initialized.
        
        Returns:
            Tuple of (tgc_value, temperature_c)
        """
        try:
            from apps.scenario.models import TGCModel, TemperatureProfile, TemperatureReading
            from django.db.models import Avg
            
            # Get any TGC model (they should be similar for Adult stage)
            tgc_model = TGCModel.objects.first()
            
            if tgc_model:
                tgc_value = float(tgc_model.tgc_value)
            else:
                tgc_value = 0.0031  # Fallback to standard value
            
            # Get average sea temperature from any temperature profile
            temp_profile = TemperatureProfile.objects.filter(
                name__icontains='Sea'
            ).first()
            
            if temp_profile:
                avg_temp = TemperatureReading.objects.filter(
                    profile=temp_profile
                ).aggregate(avg=Avg('temperature'))['avg']
                temp_c = float(avg_temp) if avg_temp else 9.0
            else:
                temp_c = 9.0  # Fallback
            
            print(f"  Using TGC from database: {tgc_value}")
            print(f"  Using sea temp from database: {temp_c:.1f}°C")
            
            return tgc_value, temp_c
            
        except Exception as e:
            print(f"  ⚠ Could not load TGC/temp from database: {e}")
            print(f"  Using fallback values: TGC=0.0031, Temp=9.0°C")
            return 0.0031, 9.0  # Safe defaults
    
    def generate_schedule(self):
        """Generate complete deterministic schedule."""
        print("\n" + "="*80)
        print("BATCH GENERATION SCHEDULE PLANNER")
        print("="*80 + "\n")

        # Load infrastructure before deriving effective geography set.
        self._load_infrastructure()
        usable_geos = [
            geo_name
            for geo_name in ["Faroe Islands", "Scotland"]
            if self.infrastructure.get(geo_name, {}).get("stations")
        ]
        if self.reference_pack_enabled:
            usable_geos = [
                geo_name
                for geo_name in usable_geos
                if self.infrastructure.get(geo_name, {}).get("areas")
            ]
        if not usable_geos:
            raise Exception(
                "No usable geographies found for schedule generation "
                "(need stations; reference-pack mode also requires sea areas)."
            )
        
        # Calculate start date (historical)
        today = date.today()
        # Interleaved batches across usable geographies with global stagger.
        total_batches = self.batches_per_geo * len(usable_geos)
        span_days = (total_batches - 1) * self.stagger_days
        buffer_days = 50
        days_back = span_days + buffer_days
        start_date = today - timedelta(days=days_back)
        years_back = days_back / 365
        
        print(f"Configuration:")
        print(f"  Batches per geography: {self.batches_per_geo}")
        print(f"  Total batches: {total_batches}")
        print(f"  Start date: {start_date} ({years_back:.1f} years ago)")
        print(f"  Today: {today}")
        print(f"  Global Stagger: {self.stagger_days} days (Effective per-geo: {self.stagger_days*2} days)")
        print(f"  Adult stage: {self.adult_duration} days")
        print(f"  Target saturation: {self.target_saturation*100:.0f}%")
        print(f"  Geographies: {', '.join(usable_geos)}")
        print()

        # Interleaved generation across usable geographies.
        for i in range(total_batches):
            geo_idx = i % len(usable_geos)
            geo_name = usable_geos[geo_idx]
            batch_index_in_geo = i // len(usable_geos)
            
            batch_start = start_date + timedelta(days=i * self.stagger_days)
            days_since_start = (today - batch_start).days
            total_lifecycle_days = sum(self.stage_durations.values())
            duration = min(total_lifecycle_days, days_since_start)  # Date-bounded
            
            geo_data = self.infrastructure[geo_name]
            
            try:
                batch_config = self._plan_single_batch(
                    geo_name=geo_name,
                    geo_data=geo_data,
                    batch_index=batch_index_in_geo,
                    batch_start=batch_start,
                    duration=duration
                )
                
                self.schedule.append(batch_config)
                
                # Show progress
                if i < 6 or i >= total_batches - 4:
                    total_lifecycle = sum(self.stage_durations.values())
                    status = "Completed" if duration >= total_lifecycle else "Active"
                    rings = batch_config['sea']['rings_count'] if batch_config.get('sea') else 0
                    rings_str = f"{rings:2d} rings" if rings > 0 else "no sea   "
                    print(f"  Batch {i+1:3d} ({geo_name[:2]}): {batch_start} | {duration:3d} days | "
                          f"{rings_str} | {status}")
                elif i == 6:
                    print(f"  ...")
            
            except Exception as e:
                print(f"❌ Failed to plan batch {i+1} ({geo_name}): {e}")
                # Continue to try planning others or raise?
                # Raising is better to fail early
                raise e

        return self.schedule

    @staticmethod
    def _normalize_name(value):
        """Normalize labels for tolerant matching across accent/spacing variants."""
        if value is None:
            return ""
        normalized = unicodedata.normalize("NFKD", str(value))
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
        return " ".join(ascii_value.upper().split())

    @staticmethod
    def _is_truthy(value):
        """Parse CSV boolean values with safe defaults."""
        return str(value).strip().lower() in {"true", "1", "yes", "y", "t"}

    @staticmethod
    def _truncate_batch_name(base_name, suffix="", max_length=50):
        """Keep batch numbers within model constraints while preserving suffixes."""
        base_name = (base_name or "").strip()
        suffix = suffix or ""
        if len(base_name) + len(suffix) <= max_length:
            return f"{base_name}{suffix}"
        keep = max(1, max_length - len(suffix))
        return f"{base_name[:keep].rstrip()}{suffix}"

    @staticmethod
    def _infer_stage_from_hall_label(hall_label):
        """
        Infer lifecycle stage from hall naming conventions as a last-resort fallback.

        Used only for halls missing explicit static/observed mapping.
        """
        normalized = BatchSchedulePlanner._normalize_name(hall_label)
        if not normalized:
            return None

        keyword_stage_rules = [
            (("EGG", "ALEVIN", "KLEK", "HATCH", "INCUB", "ROGN", "BROOD"), "Egg&Alevin"),
            (("FRY", "STARTFODR", "STARTFO"), "Fry"),
            (("PARR",), "Parr"),
            (("SMOLT", "RAS"), "Smolt"),
            (("POST", "PRE-TRANSFER"), "Post-Smolt"),
        ]
        for keywords, stage_name in keyword_stage_rules:
            if any(keyword in normalized for keyword in keywords):
                return stage_name

        # Letter-sequence convention fallback: A/B/C/D/(E+)
        # Supports labels like A, A1, "Hall A", "A row", etc.
        letter_match = re.search(r"\b([A-J])\d?\b", normalized)
        if not letter_match:
            return None

        letter = letter_match.group(1)
        if letter == "A":
            return "Egg&Alevin"
        if letter == "B":
            return "Fry"
        if letter == "C":
            return "Parr"
        if letter == "D":
            return "Smolt"
        if letter in {"E", "F", "G", "H", "I", "J"}:
            return "Post-Smolt"
        return None

    def _read_reference_pack_csv(self, filename):
        """Read one CSV from the reference pack directory."""
        if not self.reference_pack_dir:
            return []
        path = self.reference_pack_dir / filename
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def _build_reference_batch_name_catalog(self):
        """
        Load realistic batch-number pools keyed by geography.

        Preserves CSV ordering so familiar names appear in expected cadence.
        Splits pools into:
        - FW-style names for initial batch creation.
        - Sea-style names for FW->Sea rename targets.
        """
        batch_rows = self._read_reference_pack_csv("batch_name_reference.csv")
        fw_by_geo: Dict[str, List[str]] = defaultdict(list)
        sea_by_geo: Dict[str, List[str]] = defaultdict(list)
        non_fw_by_geo: Dict[str, List[str]] = defaultdict(list)
        all_by_geo: Dict[str, List[str]] = defaultdict(list)
        seen_fw_by_geo: Dict[str, Set[str]] = defaultdict(set)
        seen_sea_by_geo: Dict[str, Set[str]] = defaultdict(set)
        seen_non_fw_by_geo: Dict[str, Set[str]] = defaultdict(set)
        seen_all_by_geo: Dict[str, Set[str]] = defaultdict(set)

        fw_global: List[str] = []
        sea_global: List[str] = []
        non_fw_global: List[str] = []
        all_global: List[str] = []
        seen_fw_global: Set[str] = set()
        seen_sea_global: Set[str] = set()
        seen_non_fw_global: Set[str] = set()
        seen_all_global: Set[str] = set()

        def _append_unique(pool, seen, value):
            if value and value not in seen:
                pool.append(value)
                seen.add(value)

        for row in batch_rows:
            batch_number = (row.get("batch_number") or "").strip()
            if not batch_number:
                continue
            geography_hint = (row.get("geography_hint") or "").strip()
            name_class = self._classify_reference_batch_name(batch_number)

            if geography_hint:
                _append_unique(
                    all_by_geo[geography_hint],
                    seen_all_by_geo[geography_hint],
                    batch_number,
                )
            _append_unique(all_global, seen_all_global, batch_number)

            if name_class == "fw":
                if geography_hint:
                    _append_unique(
                        fw_by_geo[geography_hint],
                        seen_fw_by_geo[geography_hint],
                        batch_number,
                    )
                _append_unique(fw_global, seen_fw_global, batch_number)
            else:
                if geography_hint:
                    _append_unique(
                        non_fw_by_geo[geography_hint],
                        seen_non_fw_by_geo[geography_hint],
                        batch_number,
                    )
                _append_unique(non_fw_global, seen_non_fw_global, batch_number)

            if name_class == "sea":
                if geography_hint:
                    _append_unique(
                        sea_by_geo[geography_hint],
                        seen_sea_by_geo[geography_hint],
                        batch_number,
                    )
                _append_unique(sea_global, seen_sea_global, batch_number)

        fw_catalog: Dict[str, List[str]] = {}
        for geography_hint, names in all_by_geo.items():
            fw_catalog[geography_hint] = fw_by_geo.get(geography_hint) or list(names)
        if all_global:
            fw_catalog["__global__"] = fw_global or list(all_global)

        sea_catalog: Dict[str, List[str]] = {}
        for geography_hint, names in all_by_geo.items():
            sea_catalog[geography_hint] = (
                sea_by_geo.get(geography_hint)
                or non_fw_by_geo.get(geography_hint)
                or list(names)
            )
        if all_global:
            sea_catalog["__global__"] = sea_global or non_fw_global or list(all_global)

        return dict(fw_catalog), dict(sea_catalog)

    def _classify_reference_batch_name(self, batch_number):
        """Classify reference names into FW/Sea buckets by known naming patterns."""
        normalized = self._normalize_name(batch_number)
        if any(normalized.startswith(prefix) for prefix in self.FW_NAME_PREFIXES):
            return "fw"
        if any(normalized.startswith(prefix) for prefix in self.SEA_NAME_PREFIXES):
            return "sea"
        return "other"

    def _get_realistic_batch_number(self, geo_name, batch_index):
        """Deterministically select and uniquify a reference batch name."""
        if not self.reference_pack_enabled:
            return None

        pool = self.reference_batch_names_by_geo.get(geo_name)
        if not pool:
            pool = self.reference_batch_names_by_geo.get("__global__", [])
        if not pool:
            return None

        base_name = pool[batch_index % len(pool)]
        usage_key = f"{geo_name}|{base_name}"
        attempt = self._batch_name_usage.get(usage_key, 0) + 1

        while True:
            suffix = "" if attempt == 1 else f" ({attempt})"
            candidate = self._truncate_batch_name(base_name, suffix=suffix, max_length=50)
            if candidate not in self._scheduled_batch_names:
                self._batch_name_usage[usage_key] = attempt
                self._scheduled_batch_names.add(candidate)
                return candidate
            attempt += 1

    def _build_batch_number(self, geo_name, batch_start, batch_index, geo_code=None):
        """Build deterministic batch_number with realistic fallback support."""
        realistic_name = self._get_realistic_batch_number(geo_name, batch_index)
        if realistic_name:
            return realistic_name
        prefix = geo_code if geo_code else geo_name[:3].upper()
        return f"{prefix}-{batch_start.year}-{batch_index+1:03d}"

    @staticmethod
    def _default_sea_batch_base_name(transfer_date):
        """Fallback sea-style naming when explicit sea pools are unavailable."""
        month = transfer_date.month
        if month in (3, 4, 5):
            season = "Vár"
        elif month in (6, 7, 8):
            season = "Summar"
        elif month in (9, 10, 11):
            season = "Heyst"
        else:
            season = "Vetur"
        return f"{season} {transfer_date.year}"

    def _get_realistic_sea_batch_number(self, geo_name, batch_index, batch_start):
        """Deterministically choose a sea rename target for FW->Sea transition."""
        if not self.reference_pack_enabled:
            return None

        pool = self.reference_sea_batch_names_by_geo.get(geo_name)
        if not pool:
            pool = self.reference_sea_batch_names_by_geo.get("__global__", [])

        if pool:
            base_name = pool[batch_index % len(pool)]
        else:
            transfer_offset = (
                self.stage_durations["Egg&Alevin"]
                + self.stage_durations["Fry"]
                + self.stage_durations["Parr"]
                + self.stage_durations["Smolt"]
                + self.stage_durations["Post-Smolt"]
            )
            transfer_date = batch_start + timedelta(days=transfer_offset)
            base_name = self._default_sea_batch_base_name(transfer_date)

        usage_key = f"{geo_name}|{base_name}"
        attempt = self._sea_batch_name_usage.get(usage_key, 0) + 1

        while True:
            suffix = "" if attempt == 1 else f" ({attempt})"
            candidate = self._truncate_batch_name(base_name, suffix=suffix, max_length=50)
            if candidate not in self._scheduled_sea_batch_names:
                self._sea_batch_name_usage[usage_key] = attempt
                self._scheduled_sea_batch_names.add(candidate)
                return candidate
            attempt += 1

    def _build_reference_pack_catalog(self):
        """
        Build station/area filters and hall->stage candidates from reference pack.

        Primary source is infrastructure_containers.csv. Hall-stage mapping uses
        static mappings first, then observed dominant mappings as fallback.
        """
        containers_rows = self._read_reference_pack_csv("infrastructure_containers.csv")
        stations_rows = self._read_reference_pack_csv("infrastructure_stations.csv")
        areas_rows = self._read_reference_pack_csv("infrastructure_areas.csv")
        static_rows = self._read_reference_pack_csv("hall_stage_mapping_static.csv")
        observed_rows = self._read_reference_pack_csv("hall_stage_mapping_observed_dominant.csv")

        stations_by_geo: Dict[str, Set[str]] = defaultdict(set)
        areas_by_geo: Dict[str, Set[str]] = defaultdict(set)
        container_halls_by_geo: Dict[str, Set[Tuple[str, str]]] = defaultdict(set)

        for row in containers_rows:
            if not self._is_truthy(row.get("active", "True")):
                continue
            hierarchy_role = (row.get("hierarchy_role") or "").strip().upper()
            if hierarchy_role and hierarchy_role != HOLDING_ROLE:
                continue
            geography = (row.get("geography") or "").strip()
            if not geography:
                continue
            station_name = (row.get("station_name") or "").strip()
            hall_name = (row.get("hall_name") or "").strip()
            area_name = (row.get("area_name") or "").strip()
            location_context = (row.get("location_context") or "").strip().lower()

            if location_context == "hall" or (station_name and hall_name):
                if station_name:
                    stations_by_geo[geography].add(station_name)
                if station_name and hall_name:
                    container_halls_by_geo[geography].add((station_name, hall_name))

            if location_context == "area" or area_name:
                if area_name:
                    areas_by_geo[geography].add(area_name)

        fallback_stations_by_geo: Dict[str, Set[str]] = defaultdict(set)
        for row in stations_rows:
            if not self._is_truthy(row.get("active", "True")):
                continue
            geography = (row.get("geography") or "").strip()
            station_name = (row.get("station_name") or "").strip()
            if geography and station_name:
                fallback_stations_by_geo[geography].add(station_name)
        for geography, names in fallback_stations_by_geo.items():
            if not stations_by_geo[geography]:
                stations_by_geo[geography].update(names)

        fallback_areas_by_geo: Dict[str, Set[str]] = defaultdict(set)
        for row in areas_rows:
            if not self._is_truthy(row.get("active", "True")):
                continue
            geography = (row.get("geography") or "").strip()
            area_name = (row.get("area_name") or "").strip()
            if geography and area_name:
                fallback_areas_by_geo[geography].add(area_name)
        for geography, names in fallback_areas_by_geo.items():
            if not areas_by_geo[geography]:
                areas_by_geo[geography].update(names)

        halls = Hall.objects.select_related("freshwater_station__geography").all()
        halls_by_station: Dict[str, List[Hall]] = defaultdict(list)
        for hall in halls:
            station_key = self._normalize_name(hall.freshwater_station.name)
            halls_by_station[station_key].append(hall)

        container_halls_normalized: Dict[str, Set[Tuple[str, str]]] = defaultdict(set)
        container_halls_canonical: Dict[str, Dict[Tuple[str, str], Tuple[str, str]]] = defaultdict(dict)
        for geography, pairs in container_halls_by_geo.items():
            for station_name, hall_name in pairs:
                normalized_pair = (
                    self._normalize_name(station_name),
                    self._normalize_name(hall_name),
                )
                container_halls_normalized[geography].add(normalized_pair)
                if normalized_pair not in container_halls_canonical[geography]:
                    container_halls_canonical[geography][normalized_pair] = (
                        station_name,
                        hall_name,
                    )

        stage_halls_static: Dict[str, Dict[str, List[Tuple[str, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        stage_halls_observed: Dict[str, Dict[str, List[Tuple[str, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        stage_halls_inferred: Dict[str, Dict[str, List[Tuple[str, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        mapped_pairs_by_geo: Dict[str, Set[Tuple[str, str]]] = defaultdict(set)

        for row in static_rows:
            site_name = (row.get("site_name") or "").strip()
            hall_label = (row.get("hall_label") or "").strip()
            stage_name = (row.get("lifecycle_stage") or "").strip()
            if not (site_name and hall_label and stage_name):
                continue

            station_key = self._normalize_name(site_name)
            hall_label_key = self._normalize_name(hall_label)
            for hall in halls_by_station.get(station_key, []):
                geo_name = hall.freshwater_station.geography.name
                hall_name_key = self._normalize_name(hall.name)
                if not hall_label_key:
                    continue
                if not (
                    hall_name_key == hall_label_key
                    or hall_name_key.startswith(hall_label_key)
                    or hall_label_key in hall_name_key
                ):
                    continue

                candidate = (hall.freshwater_station.name, hall.name)
                if container_halls_by_geo[geo_name]:
                    normalized_pair = (
                        self._normalize_name(candidate[0]),
                        self._normalize_name(candidate[1]),
                    )
                    if normalized_pair not in container_halls_normalized[geo_name]:
                        continue

                if candidate not in stage_halls_static[geo_name][stage_name]:
                    stage_halls_static[geo_name][stage_name].append(candidate)
                    mapped_pairs_by_geo[geo_name].add(
                        (
                            self._normalize_name(candidate[0]),
                            self._normalize_name(candidate[1]),
                        )
                    )

        for row in observed_rows:
            geography = (row.get("geography") or "").strip()
            station_name = (row.get("station_name") or "").strip()
            hall_name = (row.get("hall_name") or "").strip()
            stage_name = (row.get("dominant_lifecycle_stage") or "").strip()
            if not (geography and station_name and hall_name and stage_name):
                continue

            if container_halls_by_geo[geography]:
                normalized_pair = (
                    self._normalize_name(station_name),
                    self._normalize_name(hall_name),
                )
                if normalized_pair not in container_halls_normalized[geography]:
                    continue
                station_name, hall_name = container_halls_canonical[geography].get(
                    normalized_pair,
                    (station_name, hall_name),
                )

            candidate = (station_name, hall_name)
            if candidate not in stage_halls_observed[geography][stage_name]:
                stage_halls_observed[geography][stage_name].append(candidate)
                mapped_pairs_by_geo[geography].add(
                    (
                        self._normalize_name(candidate[0]),
                        self._normalize_name(candidate[1]),
                    )
                )

        # Tertiary fallback: infer stage from hall names for unmapped halls.
        for geography, pairs in container_halls_by_geo.items():
            for station_name, hall_name in pairs:
                normalized_pair = (
                    self._normalize_name(station_name),
                    self._normalize_name(hall_name),
                )
                if normalized_pair in mapped_pairs_by_geo[geography]:
                    continue
                inferred_stage = self._infer_stage_from_hall_label(hall_name)
                if not inferred_stage:
                    continue
                candidate = (station_name, hall_name)
                if candidate not in stage_halls_inferred[geography][inferred_stage]:
                    stage_halls_inferred[geography][inferred_stage].append(candidate)

        stage_halls: Dict[str, Dict[str, List[Tuple[str, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        all_stage_sources = set(stage_halls_static) | set(stage_halls_observed) | set(stage_halls_inferred)
        for geography in all_stage_sources:
            stage_names = (
                set(stage_halls_static[geography])
                | set(stage_halls_observed[geography])
                | set(stage_halls_inferred[geography])
            )
            for stage_name in stage_names:
                ordered_candidates: List[Tuple[str, str]] = []
                seen_candidates: Set[Tuple[str, str]] = set()
                for candidate in stage_halls_static[geography].get(stage_name, []):
                    if candidate not in seen_candidates:
                        ordered_candidates.append(candidate)
                        seen_candidates.add(candidate)
                for candidate in stage_halls_observed[geography].get(stage_name, []):
                    if candidate not in seen_candidates:
                        ordered_candidates.append(candidate)
                        seen_candidates.add(candidate)
                for candidate in stage_halls_inferred[geography].get(stage_name, []):
                    if candidate not in seen_candidates:
                        ordered_candidates.append(candidate)
                        seen_candidates.add(candidate)
                if ordered_candidates:
                    stage_halls[geography][stage_name] = ordered_candidates

        return stations_by_geo, areas_by_geo, stage_halls

    @staticmethod
    def _container_occupancy_key(container):
        """
        Build stable occupancy key for containers/rings.

        Realistic migrated infrastructure may reuse short container labels across halls,
        so IDs are required to avoid false conflicts.
        """
        return f"{container.id}:{container.name}"
    
    def _load_infrastructure(self):
        """Load and organize infrastructure data."""
        print("Loading infrastructure...")
        
        self.infrastructure = {}
        self.reference_halls_by_geo_stage = {}
        self.reference_batch_names_by_geo = {}
        self.reference_sea_batch_names_by_geo = {}
        self._batch_name_usage.clear()
        self._scheduled_batch_names.clear()
        self._sea_batch_name_usage.clear()
        self._scheduled_sea_batch_names.clear()
        stations_by_geo = {}
        areas_by_geo = {}
        stage_hall_candidates = {}

        if self.reference_pack_enabled:
            if not self.reference_pack_dir.exists():
                raise Exception(f"Reference pack directory not found: {self.reference_pack_dir}")
            stations_by_geo, areas_by_geo, stage_hall_candidates = self._build_reference_pack_catalog()
            (
                self.reference_batch_names_by_geo,
                self.reference_sea_batch_names_by_geo,
            ) = self._build_reference_batch_name_catalog()
            print(f"  Reference-pack mode enabled: {self.reference_pack_dir}")
            geo_name_counts = {
                geo_name: len(pool)
                for geo_name, pool in self.reference_batch_names_by_geo.items()
                if geo_name != "__global__"
            }
            sea_geo_name_counts = {
                geo_name: len(pool)
                for geo_name, pool in self.reference_sea_batch_names_by_geo.items()
                if geo_name != "__global__"
            }
            if geo_name_counts:
                print(f"    FW batch name pools: {geo_name_counts}")
            elif self.reference_batch_names_by_geo.get("__global__"):
                print(
                    "    FW batch name pool (global): "
                    f"{len(self.reference_batch_names_by_geo['__global__'])}"
                )
            if sea_geo_name_counts:
                print(f"    Sea batch name pools: {sea_geo_name_counts}")
            elif self.reference_sea_batch_names_by_geo.get("__global__"):
                print(
                    "    Sea batch name pool (global): "
                    f"{len(self.reference_sea_batch_names_by_geo['__global__'])}"
                )
        
        for geo in Geography.objects.filter(name__in=['Faroe Islands', 'Scotland']):
            if self.reference_pack_enabled:
                station_names = sorted(stations_by_geo.get(geo.name) or [])
                if station_names:
                    stations = list(
                        FreshwaterStation.objects.filter(
                            geography=geo,
                            name__in=station_names,
                        ).order_by('name')
                    )
                else:
                    stations = list(
                        FreshwaterStation.objects.filter(
                            geography=geo,
                            active=True,
                        ).order_by('name')
                    )

                area_names = sorted(areas_by_geo.get(geo.name) or [])
                if area_names:
                    areas = list(
                        Area.objects.filter(
                            geography=geo,
                            name__in=area_names,
                            active=True,
                        ).order_by('name')
                    )
                else:
                    areas = list(Area.objects.filter(geography=geo, active=True).order_by('name'))
            else:
                # Legacy synthetic mode: Filter to production stations only
                # (FI-FW-* and S-FW-* patterns).
                prefix = 'FI-FW' if geo.name == 'Faroe Islands' else 'S-FW'
                stations = list(FreshwaterStation.objects.filter(
                    geography=geo,
                    name__startswith=prefix
                ).order_by('name'))
                
                areas = list(Area.objects.filter(
                    geography=geo
                ).order_by('name'))
            
            self.infrastructure[geo.name] = {
                'geography': geo,
                'stations': stations,
                'areas': areas,
            }

            if self.reference_pack_enabled:
                hall_map = {}
                hall_lookup = {
                    (hall.freshwater_station.name, hall.name): hall
                    for hall in Hall.objects.select_related('freshwater_station').filter(
                        freshwater_station__geography=geo
                    )
                }
                for stage_name, stage_pairs in stage_hall_candidates.get(geo.name, {}).items():
                    resolved_halls = []
                    seen_pairs = set()
                    for station_name, hall_name in stage_pairs:
                        key = (station_name, hall_name)
                        if key in seen_pairs:
                            continue
                        hall = hall_lookup.get(key)
                        if hall:
                            resolved_halls.append(hall)
                            seen_pairs.add(key)
                    if resolved_halls:
                        hall_map[stage_name] = resolved_halls
                self.reference_halls_by_geo_stage[geo.name] = hall_map
            
            print(f"  {geo.name}: {len(stations)} stations, {len(areas)} sea areas")
            if self.reference_pack_enabled:
                stage_hall_counts = {
                    stage_name: len(halls)
                    for stage_name, halls in self.reference_halls_by_geo_stage.get(geo.name, {}).items()
                }
                print(f"    stage halls: {stage_hall_counts}")
        
        print()
    
    def _plan_single_batch(self, geo_name, geo_data, batch_index, batch_start, duration):
        """Plan container allocation for single batch with weight-based harvest estimation."""

        # For weight-based planning: Estimate actual harvest timing
        # Use worst-case scenario (slowest growth to highest weight target)
        harvest_target_kg = self.harvest_targets['max_weight_kg']  # Plan for maximum weight (longest duration)
        estimated_harvest_days = self._estimate_harvest_days(
            adult_start_weight_g=self.harvest_targets['adult_start_weight_g'],
            target_harvest_kg=harvest_target_kg,
            tgc=self.harvest_targets['tgc_adult'],
            temp_c=self.harvest_targets['temp_sea_c']
        )

        # Use the longer of: date-bounded duration OR estimated harvest duration
        # This ensures containers are planned for worst-case occupation
        effective_duration = max(duration, estimated_harvest_days + 450)  # +450 for full lifecycle

        # Allocate freshwater containers (10 per stage)
        # Each stage can use ANY available hall (doesn't need to be same station)
        fw_containers = self._allocate_freshwater_independent(
            geo_data['stations'],
            batch_index,
            batch_start,
            duration,  # Match execution horizon to avoid over-reserving future stages
            geo_name=geo_name,
        )

        # Get station name from first allocated hall (for batch metadata)
        first_allocation = list(fw_containers.values())[0] if fw_containers else None
        first_hall_name = first_allocation.get('hall') if first_allocation else None
        station_name = (
            first_allocation.get('station')
            if first_allocation and first_allocation.get('station')
            else None
        )
        if not station_name and first_hall_name:
            station_name = first_hall_name.rsplit('-Hall-', 1)[0]
        if not station_name:
            station_name = geo_data['stations'][0].name

        # Deterministic sea area selection (round-robin)
        area_idx = batch_index % len(geo_data['areas'])

        # Allocate sea rings (20 per batch, full area utilization)
        sea_containers = self._allocate_sea_rings(
            geo_data['areas'],
            area_idx,
            batch_index,
            batch_start,
            duration
        )

        # Generate batch config - include harvest target for execution
        batch_id = self._build_batch_number(
            geo_name=geo_name,
            batch_start=batch_start,
            batch_index=batch_index,
            geo_code=getattr(geo_data['geography'], 'code', None),
        )
        sea_batch_number_target = self._get_realistic_sea_batch_number(
            geo_name=geo_name,
            batch_index=batch_index,
            batch_start=batch_start,
        )
        # Deterministic egg count based on batch index (eliminates random seed)
        eggs = 3000000 + ((batch_index * 123456) % 800000)  # Range: 3.0M - 3.8M
        actual_harvest_target = self._get_random_harvest_target()  # Random target for execution

        return {
            'batch_id': batch_id,
            'start_date': str(batch_start),
            'eggs': eggs,
            'duration': duration,  # Actual execution duration
            'effective_duration': effective_duration,  # Conservative planning duration
            'harvest_target_kg': actual_harvest_target,  # For execution (matches engine)
            'geography': geo_name,
            'station': station_name,
            'sea_batch_number_target': sea_batch_number_target,
            'freshwater': fw_containers,
            'sea': sea_containers,
        }
    
    def _allocate_freshwater_independent(
        self,
        all_stations,
        batch_index,
        batch_start,
        duration,
        geo_name=None,
    ):
        """
        Allocate freshwater halls independently per stage.
        Each stage can use ANY available hall (not restricted to single station).
        
        This maximizes packing density and prevents artificial station bottlenecks.
        """
        if self.reference_pack_enabled and geo_name:
            return self._allocate_freshwater_from_reference(
                geo_name=geo_name,
                batch_index=batch_index,
                batch_start=batch_start,
                duration=duration,
            )

        allocations = {}
        
        stage_configs = [
            ('Egg&Alevin', 'A', 0),
            ('Fry', 'B', 90),
            ('Parr', 'C', 180),
            ('Smolt', 'D', 270),
            ('Post-Smolt', 'E', 360)
        ]
        
        for stage_name, hall_letter, stage_start_day in stage_configs:
            stage_end_day = stage_start_day + self.stage_durations[stage_name]
            
            # Only allocate if this stage is reached (date-bounded)
            if stage_start_day >= duration:
                continue
            
            # Find ANY hall of this type (across all stations) with 10 available containers
            allocated_hall = None
            allocated_containers = []
            
            for station in all_stations:
                hall_name = f"{station.name}-Hall-{hall_letter}"
                containers = list(
                    Container.objects.filter(
                        hall__name=hall_name,
                        hierarchy_role=HOLDING_ROLE,
                    ).order_by('name')
                )
                
                if len(containers) < 10:
                    continue
                
                # Check availability
                absolute_start = (batch_start - date(2018, 1, 1)).days + stage_start_day
                absolute_end = (batch_start - date(2018, 1, 1)).days + min(stage_end_day, duration)
                
                # Find 10 available containers in this hall
                available = []
                for container in containers:
                    if self._check_container_available(
                        self._container_occupancy_key(container),
                        absolute_start,
                        absolute_end,
                    ):
                        available.append(container)
                    if len(available) == 10:
                        break
                
                if len(available) == 10:
                    # Found a hall with capacity!
                    allocated_hall = hall_name
                    allocated_containers = available
                    
                    # Mark as occupied
                    for container in available:
                        self.occupancy[self._container_occupancy_key(container)].append(
                            (absolute_start, absolute_end, batch_index)
                        )
                    
                    break
            
            if not allocated_hall:
                raise Exception(
                    f"No {hall_letter} hall has 10 available containers for batch {batch_index} "
                    f"starting {batch_start}! Capacity exceeded - reduce batch count or increase stagger."
                )
            
            allocations[stage_name.lower().replace('&', '_').replace('-', '_')] = {
                'hall': allocated_hall,
                'station': allocated_hall.rsplit('-Hall-', 1)[0] if '-Hall-' in allocated_hall else '',
                'containers': [c.name for c in allocated_containers],
                'container_ids': [c.id for c in allocated_containers],
                'start_day': stage_start_day,
                'end_day': min(stage_end_day, duration)
            }
        
        return allocations

    def _allocate_freshwater_from_reference(self, geo_name, batch_index, batch_start, duration):
        """
        Allocate halls by lifecycle-stage mapping from reference pack.

        Unlike synthetic mode, this does not assume hall letters A-E and supports
        familiar migrated hall names.
        """
        allocations = {}
        stage_configs = [
            ('Egg&Alevin', 0),
            ('Fry', 90),
            ('Parr', 180),
            ('Smolt', 270),
            ('Post-Smolt', 360),
        ]

        stage_halls = self.reference_halls_by_geo_stage.get(geo_name, {})
        target_container_count = 10
        for stage_name, stage_start_day in stage_configs:
            stage_end_day = stage_start_day + self.stage_durations[stage_name]
            if stage_start_day >= duration:
                continue

            hall_candidates = stage_halls.get(stage_name, [])
            if not hall_candidates:
                raise Exception(
                    f"Reference pack has no hall candidates for stage {stage_name} in {geo_name}."
                )

            absolute_start = (batch_start - date(2018, 1, 1)).days + stage_start_day
            absolute_end = (batch_start - date(2018, 1, 1)).days + min(stage_end_day, duration)
            available_by_hall = []
            for hall in hall_candidates:
                hall_containers = list(
                    Container.objects.filter(
                        hall=hall,
                        active=True,
                        hierarchy_role=HOLDING_ROLE,
                    ).order_by('name')
                )
                if not hall_containers:
                    continue
                available = [
                    container
                    for container in hall_containers
                    if self._check_container_available(
                        self._container_occupancy_key(container), absolute_start, absolute_end
                    )
                ]
                if available:
                    available_by_hall.append((hall, available))

            available_capacity = sum(len(available) for _, available in available_by_hall)
            required_count = min(target_container_count, available_capacity)
            if required_count <= 0:
                raise Exception(
                    f"No available reference-pack containers for stage {stage_name} "
                    f"in {geo_name} for batch {batch_index} starting {batch_start}."
                )

            selected_containers = []
            used_halls = []
            for hall, available in available_by_hall:
                if len(selected_containers) >= required_count:
                    break
                take = min(
                    len(available),
                    required_count - len(selected_containers),
                )
                if take <= 0:
                    continue
                selected_containers.extend(available[:take])
                used_halls.append(hall)

            if len(selected_containers) < required_count:
                raise Exception(
                    f"No reference-pack hall set has {required_count} available containers for stage {stage_name} "
                    f"in {geo_name} for batch {batch_index} starting {batch_start}."
                )

            for container in selected_containers:
                self.occupancy[self._container_occupancy_key(container)].append(
                    (absolute_start, absolute_end, batch_index)
                )

            primary_hall = used_halls[0]
            if len(used_halls) == 1:
                hall_label = primary_hall.name
            else:
                hall_names = ", ".join(hall.name for hall in used_halls)
                hall_label = f"MULTI({hall_names})"

            schedule_key = stage_name.lower().replace('&', '_').replace('-', '_')
            allocations[schedule_key] = {
                'hall': hall_label,
                'station': primary_hall.freshwater_station.name,
                'containers': [c.name for c in selected_containers],
                'container_ids': [c.id for c in selected_containers],
                'start_day': stage_start_day,
                'end_day': min(stage_end_day, duration),
            }

        return allocations
    
    def _allocate_freshwater(self, station, batch_index, batch_start, duration):
        """
        Allocate freshwater containers for all stages.
        
        Key insight: Each batch occupies ONE hall per stage sequentially.
        A station can host 5 batches simultaneously (1 per hall).
        
        With 90-day stages and 30-day stagger, each hall hosts ~3 batches over time.
        """
        allocations = {}
        
        stage_configs = [
            ('Egg&Alevin', 'A', 0),
            ('Fry', 'B', 90),
            ('Parr', 'C', 180),
            ('Smolt', 'D', 270),
            ('Post-Smolt', 'E', 360)
        ]
        
        for stage_name, hall_letter, stage_start_day in stage_configs:
            stage_end_day = stage_start_day + self.stage_durations[stage_name]
            
            # Only allocate if this stage is reached (date-bounded)
            if stage_start_day >= duration:
                continue
            
            hall_name = f"{station.name}-Hall-{hall_letter}"
            
            # Get all containers in this hall
            containers = list(Container.objects.filter(
                hall__name=hall_name,
                hierarchy_role=HOLDING_ROLE,
            ).order_by('name'))
            
            if len(containers) < 10:
                raise Exception(f"Hall {hall_name} has only {len(containers)} containers (need 10)")
            
            # Check hall availability during this stage period
            absolute_start = (batch_start - date(2018, 1, 1)).days + stage_start_day
            absolute_end = (batch_start - date(2018, 1, 1)).days + min(stage_end_day, duration)
            
            # Find 10 available containers in this hall
            available = []
            for container in containers:
                if self._check_container_available(
                    self._container_occupancy_key(container),
                    absolute_start,
                    absolute_end,
                ):
                    available.append(container)
                if len(available) == 10:
                    break
            
            if len(available) < 10:
                raise Exception(f"Hall {hall_name} doesn't have 10 available containers for batch starting {batch_start}")
            
            # Mark as occupied
            for container in available:
                self.occupancy[self._container_occupancy_key(container)].append(
                    (absolute_start, absolute_end, batch_index)
                )
            
            allocations[stage_name.lower().replace('&', '_').replace('-', '_')] = {
                'hall': hall_name,
                'containers': [c.name for c in available],
                'container_ids': [c.id for c in available],
                'start_day': stage_start_day,
                'end_day': min(stage_end_day, duration)
            }
        
        return allocations
    
    def _estimate_harvest_days(self, adult_start_weight_g, target_harvest_kg, tgc, temp_c):
        """
        Estimate days needed to reach harvest weight from adult stage entry.

        Uses the same TGC formula as the event engine:
        W_final^(1/3) = W_initial^(1/3) + TGC * temp * days

        Args:
            adult_start_weight_g: Weight when entering adult stage (g)
            target_harvest_kg: Target harvest weight (kg)
            tgc: Thermal growth coefficient
            temp_c: Temperature in Celsius

        Returns:
            Days needed to reach target weight (capped at adult_duration)
        """
        w_start_kg = adult_start_weight_g / 1000  # Convert to kg
        w_target_kg = target_harvest_kg

        # TGC formula: W_target^(1/3) = W_start^(1/3) + TGC * temp * days
        # Solve for days: days = (W_target^(1/3) - W_start^(1/3)) / (TGC * temp)
        days_needed = (w_target_kg**(1/3) - w_start_kg**(1/3)) / (tgc * temp_c)

        # Cap at maximum adult duration (some batches may not reach target weight)
        return min(max(days_needed, 1), self.adult_duration)

    def _get_random_harvest_target(self):
        """Get random harvest target weight (4.5-6.5kg) matching event engine."""
        return random.uniform(
            self.harvest_targets['min_weight_kg'],
            self.harvest_targets['max_weight_kg']
        )

    def _check_container_available(self, container_key, start_day, end_day):
        """Check if container is available during specified period."""
        occupied_periods = self.occupancy.get(container_key, [])
        for occ_start, occ_end, _ in occupied_periods:
            # Check for overlap
            if not (end_day <= occ_start or start_day >= occ_end):
                return False  # Conflict detected
        return True  # Available
    
    def _select_best_station(self, stations, batch_start, duration):
        """
        Select station with available halls for this batch's lifecycle.
        
        Allows multiple batches per station (up to 5 simultaneous, 1 per hall).
        """
        # Try each station
        for station in stations:
            # Check if this station has available halls for all needed stages
            if self._station_has_capacity(station, batch_start, duration):
                return station
        
        # Fallback: just use round-robin (shouldn't happen with proper capacity)
        raise Exception(f"No station has capacity for batch starting {batch_start}! Reduce batch count.")
    
    def _station_has_capacity(self, station, batch_start, duration):
        """
        Check if station has at least 10 available containers in each needed hall.
        """
        stage_configs = [
            ('A', 0, 90),      # Egg&Alevin
            ('B', 90, 180),    # Fry
            ('C', 180, 270),   # Parr
            ('D', 270, 360),   # Smolt
            ('E', 360, 450)    # Post-Smolt
        ]
        
        for hall_letter, stage_start, stage_end in stage_configs:
            if stage_start >= duration:
                continue  # Stage not reached
            
            hall_name = f"{station.name}-Hall-{hall_letter}"
            containers = list(
                Container.objects.filter(
                    hall__name=hall_name,
                    hierarchy_role=HOLDING_ROLE,
                ).order_by('name')
            )
            
            if len(containers) < 10:
                return False  # Hall doesn't have 10 containers
            
            # Check if 10 containers are available during this stage
            absolute_start = (batch_start - date(2018, 1, 1)).days + stage_start
            absolute_end = (batch_start - date(2018, 1, 1)).days + min(stage_end, duration)
            
            available_count = sum(
                1
                for c in containers
                if self._check_container_available(
                    self._container_occupancy_key(c),
                    absolute_start,
                    absolute_end,
                )
            )
            
            if available_count < 10:
                return False  # Not enough available containers in this hall
        
        return True  # Station has capacity for all needed stages
    
    def _allocate_sea_rings(self, areas, preferred_area_idx, batch_index, batch_start, duration):
        """
        Allocate sea rings with adaptive allocation (8-20 rings per batch).
        
        Strategy for high saturation (5-day stagger):
        - Try 8 rings first (allows 107 batches @ 860 rings)
        - Fall back to 10, 12, 15, or 20 based on availability
        - Adaptive: takes what's available to maximize saturation
        """
        
        # Adult stage timing
        adult_start_day = sum([90, 90, 90, 90, 90])  # After all FW stages
        adult_end_day = min(adult_start_day + self.adult_duration, duration)
        
        # Only allocate if Adult stage is reached
        if duration < adult_start_day:
            return None  # Batch doesn't reach Adult stage
        
        # Try preferred area first (round-robin), then all others
        for offset in range(len(areas)):
            area_idx = (preferred_area_idx + offset) % len(areas)
            area = areas[area_idx]
            
            # Get all rings in this area
            rings = list(
                Container.objects.filter(
                    area=area,
                    hierarchy_role=HOLDING_ROLE,
                ).order_by('name')
            )
            if not rings:
                continue  # Skip areas without available ring inventory
            
            # Allocate 10 rings per batch (1:1 ratio from Post-Smolt)
            # Fallback to larger allocations if needed for packing efficiency
            # Post-Smolt: 10 containers → Adult: 10-15 rings preferred
            preferred_ring_counts = [20, 15, 12, 10, 8, 6, 4, 2, 1]
            ring_count_candidates = [
                count for count in preferred_ring_counts if count <= len(rings)
            ]
            for ring_count in ring_count_candidates:
                available_rings = []
                for ring in rings:
                    if self._check_rings_available([ring], batch_start, adult_start_day, adult_end_day):
                        available_rings.append(ring)
                    if len(available_rings) == ring_count:
                        break
                
                if len(available_rings) >= ring_count:
                    # Found enough rings! Use exactly ring_count
                    selected_rings = available_rings[:ring_count]
                    self._mark_rings_occupied(selected_rings, batch_start, adult_start_day, adult_end_day, batch_index)
                    
                    note = None
                    if ring_count == 20:
                        note = 'Full area'
                    elif ring_count >= 15:
                        note = f'Large allocation ({ring_count}/20 rings)'
                    elif ring_count >= 10:
                        note = f'Standard allocation ({ring_count}/20 rings)'
                    else:
                        note = f'Minimal allocation ({ring_count}/20 rings)'
                    
                    return {
                        'area': area.name,
                        'rings': [r.name for r in selected_rings],
                        'ring_ids': [r.id for r in selected_rings],
                        'rings_count': ring_count,
                        'start_day': adult_start_day,
                        'end_day': adult_end_day,
                        'note': note
                    }
        
        # No space found - provide helpful diagnostic
        total_rings = sum(
            len(
                list(
                    Container.objects.filter(
                        area=a,
                        hierarchy_role=HOLDING_ROLE,
                    )
                )
            )
            for a in areas
        )
        occupied_count = sum(1 for ring_name in self.occupancy.keys() 
                           if any(area.name in ring_name for area in areas))
        
        raise Exception(
            f"No available rings for batch {batch_index}! "
            f"Total rings: {total_rings}, Occupied: {occupied_count}. "
            f"Consider reducing batch count or increasing stagger."
        )
    
    def _check_rings_available(self, rings, batch_start, adult_start_day, adult_end_day):
        """Check if rings are available during Adult stage period."""
        absolute_start = (batch_start - date(2018, 1, 1)).days + adult_start_day
        absolute_end = (batch_start - date(2018, 1, 1)).days + adult_end_day
        
        for ring in rings:
            ring_key = self._container_occupancy_key(ring)
            occupied_periods = self.occupancy.get(ring_key, [])
            for occ_start, occ_end, _ in occupied_periods:
                # Check for overlap
                if not (absolute_end <= occ_start or absolute_start >= occ_end):
                    return False  # Conflict detected
        
        return True  # All rings available
    
    def _mark_rings_occupied(self, rings, batch_start, adult_start_day, adult_end_day, batch_index):
        """Mark rings as occupied in occupancy tracker."""
        absolute_start = (batch_start - date(2018, 1, 1)).days + adult_start_day
        absolute_end = (batch_start - date(2018, 1, 1)).days + adult_end_day
        
        for ring in rings:
            ring_key = self._container_occupancy_key(ring)
            self.occupancy[ring_key].append((absolute_start, absolute_end, batch_index))
    
    def validate_schedule(self):
        """Validate schedule has no conflicts."""
        print("\n" + "="*80)
        print("VALIDATING SCHEDULE")
        print("="*80 + "\n")
        
        conflicts = 0
        
        # Check for container overlaps
        for container_name, periods in self.occupancy.items():
            # Sort by start time
            sorted_periods = sorted(periods, key=lambda x: x[0])
            
            for i in range(len(sorted_periods) - 1):
                curr_start, curr_end, curr_batch = sorted_periods[i]
                next_start, next_end, next_batch = sorted_periods[i + 1]
                
                if curr_end > next_start:
                    print(f"  ❌ Conflict: {container_name}")
                    print(f"     Batch {curr_batch}: Days {curr_start}-{curr_end}")
                    print(f"     Batch {next_batch}: Days {next_start}-{next_end}")
                    conflicts += 1
        
        if conflicts == 0:
            print(f"✅ Zero conflicts detected")
            print(f"✅ Schedule is valid")
        else:
            print(f"❌ {conflicts} conflicts detected")
            print(f"❌ Reduce batch count or adjust allocation")
        
        return conflicts == 0
    
    def print_statistics(self):
        """Print schedule statistics."""
        print("\n" + "="*80)
        print("SCHEDULE STATISTICS")
        print("="*80 + "\n")
        
        total_batches = len(self.schedule)
        
        # Ring allocation distribution
        ring_counts = [b['sea']['rings_count'] for b in self.schedule if b.get('sea')]
        full_area_batches = sum(1 for r in ring_counts if r == 20)
        partial_batches = sum(1 for r in ring_counts if r == 10)
        
        print(f"Total Batches: {total_batches}")
        print(f"  Faroe Islands: {sum(1 for b in self.schedule if 'Faroe' in b['geography'])}")
        print(f"  Scotland: {sum(1 for b in self.schedule if 'Scotland' in b['geography'])}")
        print()
        
        print(f"Sea Ring Allocation:")
        print(f"  Full area (20 rings): {full_area_batches} batches")
        print(f"  Partial area (10 rings): {partial_batches} batches")
        if ring_counts:
            avg_rings = sum(ring_counts) / len(ring_counts)
            total_rings_used = sum(ring_counts)
            print(f"  Average rings/batch: {avg_rings:.1f}")
            print(f"  Total ring occupancy: {total_rings_used} ring-periods")
        print()
        
        # Container utilization
        total_containers = Container.objects.filter(
            active=True,
            hierarchy_role=HOLDING_ROLE,
        ).count()
        unique_containers_used = len(self.occupancy)
        
        print(f"Container Utilization:")
        print(f"  Total containers: {total_containers}")
        print(f"  Containers allocated: {unique_containers_used}")
        print(f"  Utilization: {unique_containers_used/total_containers*100:.1f}%")
        print()
    
    def save_schedule(self, output_path):
        """Save schedule to YAML file with worker partitioning."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Partition schedule into worker groups (chronological chunks)
        # Each worker gets a contiguous time slice with no overlap
        worker_partitions = self._partition_for_workers(num_workers=14)
        
        schedule_data = {
            'metadata': {
                'generated_date': str(date.today()),
                'total_batches': len(self.schedule),
                'batches_per_geography': self.batches_per_geo,
                'target_saturation': self.target_saturation,
                'stagger_days': self.stagger_days,
                'reference_pack_dir': str(self.reference_pack_dir) if self.reference_pack_enabled else None,
                'worker_partitions': worker_partitions,
            },
            'batches': self.schedule
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(schedule_data, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Schedule saved to: {output_path}")
        print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
        print(f"\n📊 Worker Partitioning:")
        for worker_id, info in worker_partitions.items():
            print(f"   Worker {worker_id}: Batches {info['batch_range']} ({info['count']} batches)")
        print()
    
    def _partition_for_workers(self, num_workers=14):
        """
        Partition schedule into worker groups based on chronological time slices.
        
        Key insight: Batches that start far apart in time won't compete for containers.
        Group batches into time windows and assign each window to a worker.
        
        Returns dict mapping worker_id to batch indices.
        """
        if len(self.schedule) < num_workers:
            # Fewer batches than workers, one batch per worker
            return {
                f"worker_{i+1}": {
                    'batch_indices': [i],
                    'batch_range': f"{i+1}",
                    'count': 1
                }
                for i in range(len(self.schedule))
            }
        
        # Calculate batches per worker (roughly equal distribution)
        batches_per_worker = len(self.schedule) // num_workers
        remainder = len(self.schedule) % num_workers
        
        partitions = {}
        start_idx = 0
        
        for worker_num in range(num_workers):
            # Give first 'remainder' workers one extra batch
            worker_batch_count = batches_per_worker + (1 if worker_num < remainder else 0)
            end_idx = start_idx + worker_batch_count
            
            batch_indices = list(range(start_idx, end_idx))
            
            partitions[f"worker_{worker_num + 1}"] = {
                'batch_indices': batch_indices,
                'batch_range': f"{start_idx + 1}-{end_idx}",
                'count': worker_batch_count
            }
            
            start_idx = end_idx
        
        return partitions


def main():
    parser = argparse.ArgumentParser(
        description='Generate deterministic batch generation schedule'
    )
    parser.add_argument(
        '--batches',
        type=int,
        default=None,
        help='Number of batches per geography (if not specified, calculated from --years and --stagger)'
    )
    parser.add_argument(
        '--years',
        type=float,
        default=4.0,
        help='Years of historical data to generate (default: 4.0)'
    )
    parser.add_argument(
        '--saturation',
        type=float,
        default=0.85,
        help='Target infrastructure saturation (default: 0.85)'
    )
    parser.add_argument(
        '--stagger',
        type=int,
        default=5,
        help='Days between batch starts (default: 5 for high saturation)'
    )
    parser.add_argument(
        '--adult-duration',
        type=int,
        default=450,
        help='Adult stage duration in days (default: 450)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='config/batch_generation_schedule.yaml',
        help='Output YAML file path'
    )
    parser.add_argument(
        '--reference-pack',
        type=str,
        default=None,
        help=(
            'Optional path to a realistic asset reference pack directory '
            '(for example scripts/data_generation/reference_pack/latest).'
        )
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate and validate schedule but don\'t save'
    )
    
    args = parser.parse_args()
    
    # Calculate batches_per_geo from years and stagger if not explicitly provided
    if args.batches is None:
        # Calculate maximum batches from BOTH time and infrastructure constraints
        total_days = int(args.years * 365)
        
        # Time constraint: How many batches fit in the timespan?
        total_batch_starts = total_days // args.stagger
        max_from_time = total_batch_starts // 2  # Per geography
        
        # Infrastructure constraint: Sea rings are the bottleneck
        # Compact allocation: 10 rings per batch (matches Post-Smolt container count)
        # Scotland: 400 rings / 10 = 40 batches max in Adult simultaneously
        # At 85% saturation: 40 × 0.85 = 34 concurrent Adult batches
        
        rings_per_batch = 10  # Compact: Post-Smolt 10 containers → Adult 10 rings (1:1 ratio)
        scotland_rings = 400
        available_rings = scotland_rings * args.saturation
        max_concurrent_adult_scotland = int(available_rings / rings_per_batch)
        
        # For the requested stagger, how many batches would overlap in Adult?
        adult_overlap = args.adult_duration / args.stagger
        
        # Can we support that many? If not, we're infrastructure-limited
        if adult_overlap > max_concurrent_adult_scotland:
            # Infrastructure-limited: Use what fits
            max_from_infrastructure = max_concurrent_adult_scotland
            print(f'   ⚠️  Stagger too tight: {adult_overlap:.0f} batches would overlap in Adult, but capacity is {max_concurrent_adult_scotland}')
        else:
            # Stagger is safe: Use time-based limit
            max_from_infrastructure = max_from_time
        
        # Use the lesser of the two constraints
        batches_per_geo = min(max_from_time, max_from_infrastructure)
        
        print(f"\n📊 Auto-calculating batch count from constraints:")
        print(f"   Target: {args.years} years, {args.saturation*100:.0f}% saturation, {args.stagger}-day stagger")
        print(f"   Time constraint: {max_from_time} batches/geo (fits in {total_days} days)")
        print(f"   Infrastructure constraint: {max_from_infrastructure} batches/geo (400 Scotland rings)")
        print(f"   Limiting factor: {'TIME' if batches_per_geo == max_from_time else 'INFRASTRUCTURE'}")
        print(f"   Selected: {batches_per_geo} batches per geography")
        print(f"   Total batches: {batches_per_geo * 2}\n")
    else:
        batches_per_geo = args.batches
        calculated_years = (batches_per_geo * 2 * args.stagger) / 365
        print(f"\n📊 Using specified batch count:")
        print(f"   Batches per geography: {batches_per_geo}")
        print(f"   Total batches: {batches_per_geo * 2}")
        print(f"   With {args.stagger}-day stagger: ~{calculated_years:.1f} years of data\n")
    
    def _build_planner(batch_count):
        planner = BatchSchedulePlanner(
            batches_per_geo=batch_count,
            target_saturation=args.saturation,
            stagger_days=args.stagger,
            adult_duration=args.adult_duration,
            reference_pack_dir=args.reference_pack,
        )
        planner.generate_schedule()
        return planner

    try:
        planner = None

        # In reference-pack mode, auto-sized runs can overestimate capacity when
        # stage-specific hall availability (for example Post-Smolt in Scotland)
        # is tighter than coarse sea-ring estimates. Probe feasible batch counts
        # and pick the highest passing value instead of hard-failing.
        if args.reference_pack and args.batches is None:
            low = 1
            high = max(1, batches_per_geo)
            best_planner = None
            best_batches = None
            last_capacity_error = None

            print("\n🔍 Reference-pack feasibility search enabled for auto-sized batch count.")
            while low <= high:
                probe = (low + high) // 2
                print(f"\n  Probe: {probe} batches per geography")
                try:
                    probe_planner = _build_planner(probe)
                except Exception as probe_exc:
                    message = str(probe_exc)
                    capacity_issue = (
                        "No available reference-pack containers for stage" in message
                        or "Reference pack has no hall candidates for stage" in message
                        or "No reference-pack hall set has" in message
                    )
                    if not capacity_issue:
                        raise
                    print(f"    infeasible: {message}")
                    last_capacity_error = message
                    high = probe - 1
                    continue

                print("    feasible")
                best_planner = probe_planner
                best_batches = probe
                low = probe + 1

            if best_planner is None or best_batches is None:
                raise Exception(
                    "Could not produce any feasible reference-pack schedule in auto-sizing mode. "
                    f"Last capacity error: {last_capacity_error or 'unknown'}"
                )

            if best_batches != batches_per_geo:
                print(
                    "\n⚖️  Auto-sizing adjusted for reference-pack capacity: "
                    f"{batches_per_geo} -> {best_batches} batches per geography."
                )
            planner = best_planner
            batches_per_geo = best_batches
        else:
            planner = _build_planner(batches_per_geo)

        # Validate
        valid = planner.validate_schedule()

        # Statistics
        planner.print_statistics()

        if not valid:
            print("\n❌ Schedule validation failed!")
            return 1

        # Save (unless dry-run)
        if args.dry_run:
            print("\n🏃 DRY RUN MODE - Schedule not saved")
            print(f"   Would save to: {args.output}")
        else:
            planner.save_schedule(args.output)
            print("\n✅ Schedule generation complete!")
            print(f"\nExecute with:")
            print(f"  python scripts/data_generation/execute_batch_schedule.py {args.output}")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
