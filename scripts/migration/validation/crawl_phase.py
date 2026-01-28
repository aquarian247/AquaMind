"""Crawl-phase pre-run validations for FishTalk migration batches."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from apps.migration_support.models import ExternalIdMap

WATER_TYPE_CANDIDATES = (
    "container_water_type_history.csv",
    "containerwatertypehistory.csv",
    "container_water_type_history_v2.csv",
)
WATER_TYPE_LOOKUP_CANDIDATES = (
    "water_type.csv",
    "water_types.csv",
    "watertype.csv",
)
POP_STAGE_CANDIDATES = ("population_stages.csv", "populationproductionstages.csv")
PRODUCTION_STAGE_CANDIDATES = ("production_stages.csv", "productionstages.csv")
FEEDING_ACTIONS_CANDIDATES = ("feeding_actions.csv", "feedingactions.csv")
FEED_RECEPTION_BATCHES_CANDIDATES = (
    "feed_reception_batches.csv",
    "feedreceptionbatches.csv",
)
FEED_RECEPTIONS_CANDIDATES = ("feed_receptions.csv", "feedreceptions.csv")
FEED_STORE_ASSIGNMENT_CANDIDATES = (
    "feed_store_unit_assignment.csv",
    "feed_store_unit_assignments.csv",
    "feedstoreunitassignment.csv",
    "feedstoreunitassignments.csv",
)
STATUS_VALUES_CANDIDATES = ("status_values.csv", "public_status_values.csv")

EVENT_TABLE_TARGETS = {
    "feeding_actions.csv": "FeedingEvent",
    "feeding_hand_weights.csv": None,
    "mortality_actions.csv": "MortalityEvent",
    "transfer_operations.csv": "BatchTransferWorkflow",
    "transfer_edges.csv": "TransferAction",
    "sub_transfers.csv": "TransferAction",
    "operation_stage_changes.csv": None,
    "public_weight_samples.csv": "GrowthSample",
    "ext_weight_samples_v2.csv": "GrowthSample",
    "daily_sensor_readings.csv": "EnvironmentalReading",
    "time_sensor_readings.csv": "EnvironmentalReading",
}

DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
)

STAGE_ORDER = {
    "Egg&Alevin": 0,
    "Fry": 1,
    "Parr": 2,
    "Smolt": 3,
    "Post-Smolt": 4,
    "Adult": 5,
}


@dataclass
class ChecklistResult:
    name: str
    status: str
    details: str


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        return None


def fishtalk_stage_to_aquamind(stage_name: str) -> str | None:
    if not stage_name:
        return None
    upper = stage_name.upper()
    if any(token in upper for token in ("EGG", "ALEVIN", "SAC", "GREEN", "EYE")):
        return "Egg&Alevin"
    if "FRY" in upper:
        return "Fry"
    if "PARR" in upper:
        return "Parr"
    if "SMOLT" in upper and ("POST" in upper or "LARGE" in upper):
        return "Post-Smolt"
    if "SMOLT" in upper:
        return "Smolt"
    if any(token in upper for token in ("ONGROW", "GROWER", "GRILSE", "BROODSTOCK")):
        return "Adult"
    return None


def classify_water_type(name: str) -> str:
    if not name:
        return "Unknown"
    upper = name.upper()
    if any(token in upper for token in ("SEA", "SALT", "MARINE", "OCEAN")):
        return "Sea"
    if "FRESH" in upper or "FRESHWATER" in upper:
        return "Freshwater"
    return "Unknown"


def find_csv(base_dirs: Iterable[Path], candidates: Iterable[str]) -> Path | None:
    for base in base_dirs:
        for name in candidates:
            path = base / name
            if path.exists():
                return path
    return None


class CrawlPhasePreRunValidator:
    """Validate crawl-phase prerequisites for a selected batch."""

    def __init__(
        self,
        batch_key: str,
        members: list,
        *,
        csv_dirs: Iterable[Path],
        component_key: str | None = None,
    ) -> None:
        self.batch_key = batch_key
        self.members = members
        self.csv_dirs = list(csv_dirs)
        self.component_key = component_key

    def run(self) -> list[ChecklistResult]:
        results = [
            self._check_multi_geography(),
            self._check_lifecycle_ordering(),
            self._check_feed_chain(),
            self._check_rerun_accumulation(),
        ]
        return results

    def write_model_gap_report(
        self,
        output_dir: Path,
        *,
        results: list[ChecklistResult] | None = None,
    ) -> Path | None:
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "model_gap_report.md"
        now = datetime.now().isoformat(timespec="seconds")

        missing_sections: list[str] = []
        stage_path = find_csv(self.csv_dirs, PRODUCTION_STAGE_CANDIDATES)
        if stage_path:
            unmapped_stages = set()
            with stage_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    stage_name = (row.get("StageName") or "").strip()
                    if stage_name and not fishtalk_stage_to_aquamind(stage_name):
                        unmapped_stages.add(stage_name)
            if unmapped_stages:
                sample = ", ".join(sorted(unmapped_stages)[:12])
                suffix = "..." if len(unmapped_stages) > 12 else ""
                missing_sections.append(
                    f"- ProductionStages: {len(unmapped_stages)} unmapped values ({sample}{suffix})"
                )
            else:
                missing_sections.append("- ProductionStages: none detected")
        else:
            missing_sections.append("- ProductionStages: CSV missing")

        water_lookup_path = find_csv(self.csv_dirs, WATER_TYPE_LOOKUP_CANDIDATES)
        if water_lookup_path:
            unmapped_water = set()
            with water_lookup_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    name = (row.get("Name") or row.get("WaterType") or "").strip()
                    if name and classify_water_type(name) == "Unknown":
                        unmapped_water.add(name)
            if unmapped_water:
                sample = ", ".join(sorted(unmapped_water)[:12])
                suffix = "..." if len(unmapped_water) > 12 else ""
                missing_sections.append(
                    f"- WaterType: {len(unmapped_water)} unmapped values ({sample}{suffix})"
                )
            else:
                missing_sections.append("- WaterType: none detected")
        else:
            missing_sections.append("- WaterType: CSV missing")

        event_gaps = []
        for filename, target in EVENT_TABLE_TARGETS.items():
            path = find_csv(self.csv_dirs, (filename,))
            if path and target is None:
                event_gaps.append(filename)
        if event_gaps:
            event_gap_lines = [f"- {name}: no direct migration target" for name in sorted(event_gaps)]
        else:
            event_gap_lines = ["- None detected"]

        snapshot_lines = []
        status_path = find_csv(self.csv_dirs, STATUS_VALUES_CANDIDATES)
        population_ids = {
            m.population_id for m in self.members if getattr(m, "population_id", "")
        }
        if not status_path:
            snapshot_lines.append(
                "- status_values.csv missing; transfer/feeding snapshots unavailable in CSV mode"
            )
        else:
            with status_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                fieldnames = reader.fieldnames or []
                required = {"CurrentCount", "CurrentBiomassKg"}
                missing_fields = sorted(required - set(fieldnames))
                seen_populations = set()
                for row in reader:
                    pop_id = (row.get("PopulationID") or "").strip()
                    if pop_id in population_ids:
                        seen_populations.add(pop_id)
                missing_pops = sorted(population_ids - seen_populations)
            if missing_fields:
                snapshot_lines.append(
                    f"- status_values.csv missing required fields: {', '.join(missing_fields)}"
                )
            if missing_pops:
                sample = ", ".join(missing_pops[:12])
                suffix = "..." if len(missing_pops) > 12 else ""
                snapshot_lines.append(
                    f"- status_values.csv has no snapshots for {len(missing_pops)} populations ({sample}{suffix})"
                )
            if not missing_fields and not missing_pops:
                snapshot_lines.append(
                    "- status_values.csv provides CurrentCount/CurrentBiomassKg snapshots for batch populations"
                )

        violation_lines = []
        if results is None:
            results = [
                self._check_multi_geography(),
                self._check_lifecycle_ordering(),
                self._check_feed_chain(),
            ]
        for result in results:
            if result.name in (
                "Single geography (FW/Sea)",
                "Lifecycle ordering (Egg/Fry after Adult)",
                "Feed chain order (Reception -> Store -> Feeding)",
            ):
                violation_lines.append(f"- [{result.status}] {result.name}: {result.details}")

        report_lines = [
            "# Model Gap Report",
            f"- Batch: {self.batch_key}",
            f"- Generated: {now}",
            "",
            "## Missing lookup mappings",
            *missing_sections,
            "",
            "## FishTalk events with no direct target table",
            *event_gap_lines,
            "",
            "## Snapshot fields required for AquaMind computations but not derivable from raw events",
            *snapshot_lines,
            "",
            "## Violations found (multi-geo, stage order, feed chain)",
            *violation_lines,
            "",
        ]

        report_path.write_text("\n".join(report_lines), encoding="utf-8")
        return report_path

    def _check_multi_geography(self) -> ChecklistResult:
        container_ids = {m.container_id for m in self.members if getattr(m, "container_id", "")}
        if not container_ids:
            return ChecklistResult(
                "Single geography (FW/Sea)",
                "WARN",
                "No container IDs found for batch; cannot confirm water type mix.",
            )

        history_path = find_csv(self.csv_dirs, WATER_TYPE_CANDIDATES)
        if not history_path:
            return ChecklistResult(
                "Single geography (FW/Sea)",
                "SKIP",
                "ContainerWaterTypeHistory CSV not found in csv dirs.",
            )

        water_type_lookup_path = find_csv(self.csv_dirs, WATER_TYPE_LOOKUP_CANDIDATES)
        water_type_by_id = {}
        if water_type_lookup_path:
            with water_type_lookup_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    wt_id = (row.get("WaterTypeID") or "").strip()
                    name = (row.get("Name") or row.get("WaterType") or "").strip()
                    if wt_id:
                        water_type_by_id[wt_id] = name

        history_by_container: dict[str, list[tuple[datetime | None, datetime | None, str]]] = {}
        with history_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                container_id = (row.get("ContainerID") or "").strip()
                if container_id not in container_ids:
                    continue
                start_time = parse_dt((row.get("StartTime") or "").strip())
                end_time = parse_dt((row.get("EndTime") or "").strip())
                water_type_id = (row.get("WaterTypeID") or "").strip()
                water_name = water_type_by_id.get(water_type_id, water_type_id)
                water_class = classify_water_type(water_name)
                history_by_container.setdefault(container_id, []).append(
                    (start_time, end_time, water_class)
                )

        classifications: set[str] = set()
        unknown_containers = 0
        for member in self.members:
            container_id = getattr(member, "container_id", "")
            if not container_id or container_id not in history_by_container:
                unknown_containers += 1
                continue
            member_start = getattr(member, "start_time", None) or datetime.min
            member_end = getattr(member, "end_time", None) or datetime.max
            for start, end, water_class in history_by_container[container_id]:
                if start and start > member_end:
                    continue
                if end and end < member_start:
                    continue
                if water_class != "Unknown":
                    classifications.add(water_class)

        if "Freshwater" in classifications and "Sea" in classifications:
            return ChecklistResult(
                "Single geography (FW/Sea)",
                "FAIL",
                "Batch touches both Freshwater and Sea containers (check FW/Sea linkage).",
            )
        if classifications:
            detail = ", ".join(sorted(classifications))
            if unknown_containers:
                detail = f"{detail}; {unknown_containers} containers missing water history"
            return ChecklistResult(
                "Single geography (FW/Sea)",
                "PASS",
                f"Detected water types: {detail}.",
            )

        return ChecklistResult(
            "Single geography (FW/Sea)",
            "WARN",
            "No classified water types found for batch containers.",
        )

    def _check_lifecycle_ordering(self) -> ChecklistResult:
        stage_path = find_csv(self.csv_dirs, POP_STAGE_CANDIDATES)
        stage_lookup_path = find_csv(self.csv_dirs, PRODUCTION_STAGE_CANDIDATES)
        if not stage_path or not stage_lookup_path:
            return ChecklistResult(
                "Lifecycle ordering (Egg/Fry after Adult)",
                "SKIP",
                "PopulationProductionStages or ProductionStages CSV missing.",
            )

        stage_name_by_id = {}
        with stage_lookup_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stage_id = (row.get("StageID") or "").strip()
                stage_name = (row.get("StageName") or "").strip()
                if stage_id:
                    stage_name_by_id[stage_id] = stage_name

        population_ids = {m.population_id for m in self.members if getattr(m, "population_id", "")}
        stage_events: list[tuple[datetime, int]] = []
        with stage_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                population_id = (row.get("PopulationID") or "").strip()
                if population_id not in population_ids:
                    continue
                stage_id = (row.get("StageID") or "").strip()
                stage_name = stage_name_by_id.get(stage_id, "")
                aquamind_stage = fishtalk_stage_to_aquamind(stage_name)
                if aquamind_stage not in STAGE_ORDER:
                    continue
                ts = parse_dt((row.get("StartTime") or "").strip())
                if ts:
                    stage_events.append((ts, STAGE_ORDER[aquamind_stage]))

        if not stage_events:
            return ChecklistResult(
                "Lifecycle ordering (Egg/Fry after Adult)",
                "WARN",
                "No population stage events found for this batch.",
            )

        stage_events.sort(key=lambda item: item[0])
        max_seen = -1
        violations = 0
        for _, stage_rank in stage_events:
            if stage_rank < max_seen:
                violations += 1
            else:
                max_seen = stage_rank

        if violations:
            return ChecklistResult(
                "Lifecycle ordering (Egg/Fry after Adult)",
                "FAIL",
                f"Detected {violations} stage-order regressions in PopulationProductionStages.",
            )

        return ChecklistResult(
            "Lifecycle ordering (Egg/Fry after Adult)",
            "PASS",
            "Stage chronology is monotonic across batch populations.",
        )

    def _check_feed_chain(self) -> ChecklistResult:
        feeding_path = find_csv(self.csv_dirs, FEEDING_ACTIONS_CANDIDATES)
        if not feeding_path:
            return ChecklistResult(
                "Feed chain order (Reception -> Store -> Feeding)",
                "SKIP",
                "Feeding CSV not found in csv dirs.",
            )

        reception_batch_path = find_csv(self.csv_dirs, FEED_RECEPTION_BATCHES_CANDIDATES)
        reception_path = find_csv(self.csv_dirs, FEED_RECEPTIONS_CANDIDATES)
        store_path = find_csv(self.csv_dirs, FEED_STORE_ASSIGNMENT_CANDIDATES)
        if not reception_batch_path or not store_path:
            return ChecklistResult(
                "Feed chain order (Reception -> Store -> Feeding)",
                "SKIP",
                "FeedReceptionBatches/FeedStoreUnitAssignment CSVs missing.",
            )

        reception_time_by_batch: dict[str, datetime] = {}
        if reception_path:
            reception_time_by_id: dict[str, datetime] = {}
            with reception_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    reception_id = (row.get("FeedReceptionID") or "").strip()
                    ts = parse_dt(
                        (row.get("ReceptionTime") or row.get("ReceptionDate") or "").strip()
                    )
                    if reception_id and ts:
                        reception_time_by_id[reception_id] = ts

            with reception_batch_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    feed_batch_id = (row.get("FeedBatchID") or "").strip()
                    reception_id = (row.get("FeedReceptionID") or "").strip()
                    if not feed_batch_id:
                        continue
                    ts = (
                        parse_dt((row.get("ReceptionTime") or "").strip())
                        or reception_time_by_id.get(reception_id)
                    )
                    if ts:
                        existing = reception_time_by_batch.get(feed_batch_id)
                        if not existing or ts < existing:
                            reception_time_by_batch[feed_batch_id] = ts
        else:
            with reception_batch_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    feed_batch_id = (row.get("FeedBatchID") or "").strip()
                    ts = parse_dt((row.get("ReceptionTime") or "").strip())
                    if feed_batch_id and ts:
                        existing = reception_time_by_batch.get(feed_batch_id)
                        if not existing or ts < existing:
                            reception_time_by_batch[feed_batch_id] = ts

        assignment_windows: dict[str, list[tuple[datetime | None, datetime | None]]] = {}
        with store_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                container_id = (row.get("ContainerID") or "").strip()
                if not container_id:
                    continue
                start = parse_dt((row.get("StartDate") or row.get("StartTime") or "").strip())
                end = parse_dt((row.get("EndDate") or row.get("EndTime") or "").strip())
                assignment_windows.setdefault(container_id, []).append((start, end))

        population_to_container = {
            m.population_id: m.container_id
            for m in self.members
            if getattr(m, "population_id", "") and getattr(m, "container_id", "")
        }
        population_ids = set(population_to_container)

        missing_receptions = 0
        missing_assignments = 0
        time_violations = 0
        feed_rows_checked = 0

        with feeding_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                population_id = (row.get("PopulationID") or "").strip()
                if population_id not in population_ids:
                    continue
                feed_batch_id = (row.get("FeedBatchID") or "").strip()
                feeding_time = parse_dt((row.get("FeedingTime") or "").strip())
                if not feed_batch_id or not feeding_time:
                    continue
                feed_rows_checked += 1

                reception_time = reception_time_by_batch.get(feed_batch_id)
                if not reception_time:
                    missing_receptions += 1
                elif feeding_time < reception_time:
                    time_violations += 1

                container_id = population_to_container.get(population_id)
                if not container_id:
                    missing_assignments += 1
                    continue
                windows = assignment_windows.get(container_id, [])
                if not any(
                    (start is None or start <= feeding_time)
                    and (end is None or end >= feeding_time)
                    for start, end in windows
                ):
                    missing_assignments += 1

        if feed_rows_checked == 0:
            return ChecklistResult(
                "Feed chain order (Reception -> Store -> Feeding)",
                "WARN",
                "No feeding rows found for this batch in feeding_actions.csv.",
            )

        if missing_receptions or missing_assignments or time_violations:
            return ChecklistResult(
                "Feed chain order (Reception -> Store -> Feeding)",
                "FAIL",
                (
                    f"Feed rows checked={feed_rows_checked}; "
                    f"missing receptions={missing_receptions}, "
                    f"missing store assignments={missing_assignments}, "
                    f"reception after feeding={time_violations}."
                ),
            )

        return ChecklistResult(
            "Feed chain order (Reception -> Store -> Feeding)",
            "PASS",
            f"Feed rows checked={feed_rows_checked}; order consistent.",
        )

    def _check_rerun_accumulation(self) -> ChecklistResult:
        population_ids = {m.population_id for m in self.members if getattr(m, "population_id", "")}
        if not population_ids:
            return ChecklistResult(
                "Rerun accumulation risk (existing assignments)",
                "WARN",
                "No population IDs found for batch; cannot check assignments.",
            )

        existing_maps = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="Populations",
            source_identifier__in=population_ids,
        )
        existing_count = existing_maps.count()

        component_warning = ""
        if self.component_key:
            component_map_exists = ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="PopulationComponent",
                source_identifier=self.component_key,
            ).exists()
            if component_map_exists:
                component_warning = " Component already mapped via PopulationComponent."

        if existing_count:
            sample_ids = list(existing_maps.values_list("source_identifier", flat=True)[:3])
            sample_str = ", ".join(sample_ids)
            return ChecklistResult(
                "Rerun accumulation risk (existing assignments)",
                "WARN",
                f"Found {existing_count} population assignments already mapped ({sample_str}).{component_warning}",
            )

        if component_warning:
            return ChecklistResult(
                "Rerun accumulation risk (existing assignments)",
                "WARN",
                component_warning.strip(),
            )

        return ChecklistResult(
            "Rerun accumulation risk (existing assignments)",
            "PASS",
            "No existing population assignment mappings detected.",
        )
