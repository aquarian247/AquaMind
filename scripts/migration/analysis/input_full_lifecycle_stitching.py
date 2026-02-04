#!/usr/bin/env python3
# flake8: noqa
"""Build full-lifecycle population members for a sea-phase input batch.

This script expands a sea InputName batch (e.g., "Vár 2024|1|2024") by stitching
in freshwater populations that represent the biological origin of the same fish.

Primary signals (in order):
1) PopulationLink edges (if extracted) to connect FW/Sea populations.
2) Ext_Populations_v2.PopulationName parsing to detect original yearclass/supplier.
3) Timing + stage coverage heuristics based on PopulationProductionStages.

Outputs (per batch key, in scripts/migration/output/input_stitching/):
- full_lifecycle_population_members_<slug>.csv
- full_lifecycle_candidates_<slug>.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
)

SUPPLIER_CODE_MAP = {
    "BM": ["Benchmark", "Benchmark Gen"],
    "BF": ["Bakkafrost"],
    "SF": ["Stofnfiskur"],
    "AG": ["AquaGen"],
}

MONTH_MAP = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "MAI": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OKT": 10,
    "OCT": 10,
    "NOV": 11,
    "DES": 12,
    "DEC": 12,
}

SEA_NAME_RE = re.compile(
    r"^\s*(?P<unit>S?\d{2})\s+(?P<station>S\d{2})\s+(?P<supplier>[A-Z]{2})\s+"
    r"(?P<seamonth>[A-Z]{3})\s+(?P<seayear>\d{2}).*\((?P<fwmonth>[A-Z]{3})\s+(?P<fwyer>\d{2})\)",
    re.IGNORECASE,
)

STATION_RE = re.compile(r"(S\d{2})")

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
    "A": "Fry",
    "BA": "Parr",
    "BB": "Parr",
    "C": "Smolt",
    "D": "Smolt",
    "E": "Post-Smolt",
    "F": "Post-Smolt",
    "ROGN": "Egg&Alevin",
}

FAROE_SITE_KEYWORDS = {"north", "south", "west", "east", "faroe", "føroyar", "streymoy"}
SCOTLAND_SITE_KEYWORDS = {"scotland", "scottish", "uk", "loch"}


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_float(value: str) -> float:
    if not value:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", ascii_value).strip("_")
    return cleaned or "batch"


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
    if any(token in upper for token in ("ONGROW", "GROWER", "GRILSE")):
        return "Adult"
    if "BROODSTOCK" in upper:
        return "Adult"
    return None


def determine_geography(site_name: str, site_group: str | None = None) -> str:
    if site_group:
        sg_lower = site_group.lower()
        if sg_lower in ("west", "north", "south", "east"):
            return "Faroe Islands"
    if site_name:
        name_lower = site_name.lower()
        if any(kw in name_lower for kw in FAROE_SITE_KEYWORDS):
            return "Faroe Islands"
        if any(kw in name_lower for kw in SCOTLAND_SITE_KEYWORDS):
            return "Scotland"
    return "Unknown"


def normalize_label(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split()).strip()


def hall_label_from_group(group_name: str | None) -> str:
    label = normalize_label(group_name)
    if not label:
        return ""
    if "Høll" in label:
        before, _, after = label.partition("Høll")
        before = before.strip()
        after = after.strip()
        if before and not after:
            return f"Hall {before}"
        if after and not before:
            return f"Hall {after}"
        if before and after:
            return f"Hall {before}"
        return "Hall"
    if label.startswith("Hall ") or label.endswith(" Hall"):
        return label
    return label


def hall_label_from_official(official_id: str | None) -> str:
    if not official_id:
        return ""
    prefix = official_id.split(";")[0].strip()
    return hall_label_from_group(prefix)


def normalize_key(value: str | None) -> str:
    return normalize_label(value).upper()


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
    return None


def parse_sea_name(name: str) -> dict | None:
    match = SEA_NAME_RE.search(name.upper())
    if not match:
        return None
    data = match.groupdict()
    sea_month = MONTH_MAP.get(data["seamonth"][:3])
    fw_month = MONTH_MAP.get(data["fwmonth"][:3])
    sea_year = 2000 + int(data["seayear"])
    fw_year = 2000 + int(data["fwyer"])
    sea_date = datetime(sea_year, sea_month, 1) if sea_month else None
    fw_date = datetime(fw_year, fw_month, 1) if fw_month else None
    return {
        "Unit": data["unit"].upper(),
        "FWStationCode": data["station"].upper(),
        "SupplierCode": data["supplier"].upper(),
        "SeaMonth": data["seamonth"][:3].upper(),
        "SeaYear": sea_year,
        "SeaDate": sea_date,
        "FWBatchMonth": data["fwmonth"][:3].upper(),
        "FWBatchYear": fw_year,
        "FWBatchDate": fw_date,
    }


def parse_station_code(value: str | None) -> str | None:
    if not value:
        return None
    match = STATION_RE.search(value)
    return match.group(1) if match else None


def parse_batch_month_year(input_name: str) -> tuple[int | None, int | None]:
    if not input_name:
        return None, None
    month_tokens = (
        "january|jan|february|feb|march|mar|mars|april|apr|may|mai|june|jun|juni|july|jul|"
        "august|aug|september|sep|sept|septembur|october|oct|oktober|okt|"
        "november|nov|december|dec|desembur|des"
    )
    match = re.search(
        rf"({month_tokens})\s*([0-9]{{2,4}})",
        input_name,
        re.IGNORECASE,
    )
    if not match:
        return None, None
    month_raw = match.group(1).upper()
    month_key = month_raw[:3]
    # Normalize known long forms
    if month_raw.startswith("MARS"):
        month_key = "MAR"
    elif month_raw.startswith("SEPT"):
        month_key = "SEP"
    elif month_raw.startswith("DESEMBUR") or month_raw.startswith("DES"):
        month_key = "DEC"
    elif month_raw.startswith("OKTOBER") or month_raw.startswith("OKT"):
        month_key = "OCT"
    month = MONTH_MAP.get(month_key)
    year_raw = match.group(2)
    year = int(year_raw)
    if year < 100:
        year += 2000
    return month, year


def supplier_code_from_input_name(input_name: str) -> str | None:
    if not input_name:
        return None
    for code, tokens in SUPPLIER_CODE_MAP.items():
        for token in tokens:
            if token.lower() in input_name.lower():
                return code
    return None


def parse_batch_key(batch_key: str) -> tuple[str, str, str]:
    parts = [p.strip() for p in batch_key.split("|")]
    if len(parts) != 3:
        raise ValueError("batch_key must be InputName|InputNumber|YearClass")
    return parts[0], parts[1], parts[2]


def parse_yearclass_from_population_name(name: str) -> str | None:
    if not name:
        return None
    match = re.search(r"\(([^)]+)\)", name)
    if not match:
        return None
    inner = match.group(1)
    year_match = re.search(r"(\d{2,4})", inner)
    if not year_match:
        return None
    year = year_match.group(1)
    if len(year) == 2:
        year = f"20{year}"
    return year


def parse_supplier_code_from_population_name(name: str) -> str | None:
    if not name:
        return None
    tokens = re.findall(r"\b[A-Z]{2}\b", name.upper())
    for token in tokens:
        if token in SUPPLIER_CODE_MAP:
            return token
    return None


@dataclass
class InputRecord:
    population_id: str
    input_name: str
    input_number: str
    year_class: str
    supplier_id: str
    start_time: datetime | None
    input_count: float
    input_biomass: float


@dataclass
class PopulationMeta:
    population_id: str
    container_id: str
    start_time: datetime | None
    end_time: datetime | None


@dataclass
class PopulationStages:
    fishtalk_stages: list[str]
    aquamind_stages: list[str]


@dataclass
class CandidateBatch:
    batch_key: str
    population_ids: list[str]
    stage_set: set[str]
    earliest_start: datetime | None
    latest_end: datetime | None
    gap_days: int | None
    total_input: float
    supplier_match: bool
    linked_population_count: int

    @property
    def population_count(self) -> int:
        return len(self.population_ids)

    @property
    def stage_count(self) -> int:
        return len(self.stage_set)

    @property
    def has_fw(self) -> bool:
        return any(s in self.stage_set for s in ("Egg&Alevin", "Fry", "Parr", "Smolt"))

    @property
    def has_sea(self) -> bool:
        return any(s in self.stage_set for s in ("Post-Smolt", "Adult"))


def load_csv_dict(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_stage_index(csv_dir: Path) -> dict[str, PopulationStages]:
    stage_name_by_id = {}
    for row in load_csv_dict(csv_dir / "production_stages.csv"):
        stage_name_by_id[row.get("StageID", "")] = row.get("StageName", "") or ""

    events_by_pop: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    for row in load_csv_dict(csv_dir / "population_stages.csv"):
        pop_id = row.get("PopulationID", "")
        stage_id = row.get("StageID", "")
        stage_name = stage_name_by_id.get(stage_id, "")
        ts = parse_dt(row.get("StartTime", ""))
        if not pop_id or not stage_name or ts is None:
            continue
        events_by_pop[pop_id].append((ts, stage_name))

    stages_by_pop: dict[str, PopulationStages] = {}
    for pop_id, events in events_by_pop.items():
        events.sort(key=lambda x: x[0])
        fishtalk = [name for _, name in events]
        aqua = [fishtalk_stage_to_aquamind(name) for name in fishtalk]
        aqua = [a for a in aqua if a]
        stages_by_pop[pop_id] = PopulationStages(fishtalk_stages=fishtalk, aquamind_stages=aqua)
    return stages_by_pop


def build_population_meta(csv_dir: Path) -> dict[str, PopulationMeta]:
    meta = {}
    for row in load_csv_dict(csv_dir / "populations.csv"):
        pop_id = row.get("PopulationID", "")
        if not pop_id:
            continue
        meta[pop_id] = PopulationMeta(
            population_id=pop_id,
            container_id=row.get("ContainerID", ""),
            start_time=parse_dt(row.get("StartTime", "")),
            end_time=parse_dt(row.get("EndTime", "")),
        )
    return meta


def build_input_records(csv_dir: Path) -> tuple[list[InputRecord], dict[str, InputRecord]]:
    records: list[InputRecord] = []
    by_pop: dict[str, InputRecord] = {}
    for row in load_csv_dict(csv_dir / "ext_inputs.csv"):
        record = InputRecord(
            population_id=row.get("PopulationID", ""),
            input_name=row.get("InputName", "").strip(),
            input_number=row.get("InputNumber", "").strip(),
            year_class=row.get("YearClass", "").strip(),
            supplier_id=row.get("SupplierID", "").strip(),
            start_time=parse_dt(row.get("StartTime", "")),
            input_count=parse_float(row.get("InputCount", "")),
            input_biomass=parse_float(row.get("InputBiomass", "")),
        )
        if not record.population_id or not record.input_name or not record.year_class:
            continue
        records.append(record)
        by_pop.setdefault(record.population_id, record)
    return records, by_pop


def build_population_name_index(csv_dir: Path) -> dict[str, str]:
    names = {}
    for row in load_csv_dict(csv_dir / "ext_populations.csv"):
        pop_id = row.get("PopulationID", "")
        if pop_id:
            names[pop_id] = row.get("PopulationName", "") or ""
    return names


def build_population_links(csv_dir: Path) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    rows = load_csv_dict(csv_dir / "population_links.csv")
    for row in rows:
        src = row.get("FromPopulationID", "")
        dst = row.get("ToPopulationID", "")
        if not src or not dst:
            continue
        graph[src].add(dst)
        graph[dst].add(src)
    return graph


def build_container_indexes(csv_dir: Path) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    containers = {row.get("ContainerID", ""): row for row in load_csv_dict(csv_dir / "containers.csv")}
    org_units = {row.get("OrgUnitID", ""): row for row in load_csv_dict(csv_dir / "org_units.csv")}
    grouping = {row.get("ContainerID", ""): row for row in load_csv_dict(csv_dir / "grouped_organisation.csv")}
    return containers, org_units, grouping


def supplier_matches(input_name: str, supplier_codes: set[str]) -> bool:
    if not input_name or not supplier_codes:
        return False
    for code in supplier_codes:
        for token in SUPPLIER_CODE_MAP.get(code, []):
            if token.lower() in input_name.lower():
                return True
    return False


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("" if row.get(key) is None else row.get(key)) for key in fieldnames})


def build_heuristic_fw_sea_links(
    *,
    input_name: str,
    sea_population_ids: list[str],
    pop_meta: dict[str, PopulationMeta],
    names_by_pop: dict[str, str],
    containers_by_id: dict[str, dict],
    grouping_by_container: dict[str, dict],
    csv_dir: Path,
    window_days: int,
    min_score: int,
    include_smolt: bool,
    output_dir: Path,
    slug: str,
) -> tuple[set[str], set[str]]:
    """Non-canonical heuristic FW→Sea linking using hall + date + count alignment."""
    try:
        import pandas as pd  # type: ignore
    except Exception:
        print("[WARN] pandas not available; heuristic FW→Sea linking skipped.")
        return set(), set()

    expected_supplier = supplier_code_from_input_name(input_name)
    expected_month, expected_year = parse_batch_month_year(input_name)
    expected_station = parse_station_code(input_name)

    # Build sea candidates from pattern (seeded by ext_inputs + name-based match)
    sea_rows = []
    for pop_id in sea_population_ids:
        name = names_by_pop.get(pop_id, "")
        parsed = parse_sea_name(name)
        if not parsed:
            continue
        sea_rows.append((pop_id, parsed))

    # If we can infer supplier/month/year from input_name, add matching sea pops by name pattern.
    if expected_supplier and expected_month and expected_year:
        for pop_id, name in names_by_pop.items():
            meta = pop_meta.get(pop_id)
            if not meta or not meta.start_time:
                continue
            grouping = grouping_by_container.get(meta.container_id, {})
            if grouping.get("ProdStage") != "MarineSite":
                continue
            parsed = parse_sea_name(name)
            if not parsed:
                continue
            if parsed["SupplierCode"] != expected_supplier:
                continue
            if parsed["FWBatchDate"] is None:
                continue
            if parsed["FWBatchDate"].month != expected_month or parsed["FWBatchDate"].year != expected_year:
                continue
            if expected_station and parsed["FWStationCode"] != expected_station:
                continue
            sea_rows.append((pop_id, parsed))

    if not sea_rows:
        return set(), set()

    # Build FW candidate index by station code (post-smolt halls only; smolt optional)
    fw_by_station: dict[str, list[str]] = defaultdict(list)
    fw_meta = {}
    for pop_id, meta in pop_meta.items():
        grouping = grouping_by_container.get(meta.container_id, {})
        if grouping.get("ProdStage") not in ("FreshWater", "SmoltProduction", "Hatchery"):
            continue
        hall_stage = stage_from_hall(grouping.get("Site"), grouping.get("ContainerGroup"))
        if hall_stage != "Post-Smolt" and not (include_smolt and hall_stage == "Smolt"):
            continue
        if not meta.end_time:
            continue
        station = parse_station_code(grouping.get("Site"))
        if not station:
            continue
        fw_by_station.setdefault(station, []).append(pop_id)
        fw_meta[pop_id] = meta

    # Build candidate pairs
    candidates = []
    for sea_pop_id, parsed in sea_rows:
        sea_meta = pop_meta.get(sea_pop_id)
        if not sea_meta or not sea_meta.start_time:
            continue
        station = parsed["FWStationCode"]
        for fw_pop_id in fw_by_station.get(station, []):
            fw_pop_meta = fw_meta.get(fw_pop_id)
            if not fw_pop_meta or not fw_pop_meta.end_time:
                continue
            diff_days = (fw_pop_meta.end_time - sea_meta.start_time).days
            if abs(diff_days) > window_days:
                continue
            score = 40
            if abs(diff_days) <= 7:
                score += 20
            elif abs(diff_days) <= 21:
                score += 10
            else:
                score += 5

            if parsed.get("SeaDate") and sea_meta.start_time:
                if (
                    sea_meta.start_time.month == parsed["SeaDate"].month
                    and sea_meta.start_time.year == parsed["SeaDate"].year
                ):
                    score += 5
            if parsed.get("FWBatchDate") and fw_pop_meta.start_time:
                if (
                    fw_pop_meta.start_time.month == parsed["FWBatchDate"].month
                    and fw_pop_meta.start_time.year == parsed["FWBatchDate"].year
                ):
                    score += 5

            candidates.append(
                {
                    "SeaPopulationID": sea_pop_id,
                    "SeaPopulationName": names_by_pop.get(sea_pop_id, ""),
                    "SeaStartTime": sea_meta.start_time,
                    "SeaSite": grouping_by_container.get(sea_meta.container_id, {}).get("Site", ""),
                    "FWPopulationID": fw_pop_id,
                    "FWPopulationName": names_by_pop.get(fw_pop_id, ""),
                    "FWEndTime": fw_pop_meta.end_time,
                    "FWStartTime": fw_pop_meta.start_time,
                    "FWSite": grouping_by_container.get(fw_pop_meta.container_id, {}).get("Site", ""),
                    "FWContainerGroup": grouping_by_container.get(fw_pop_meta.container_id, {}).get("ContainerGroup", ""),
                    "DiffDays_FWEnd_to_SeaStart": diff_days,
                    "Score_Base": score,
                }
            )

    if not candidates:
        return set(), set()

    pairs = pd.DataFrame(candidates)
    sea_ids = set(pairs["SeaPopulationID"])
    fw_ids = set(pairs["FWPopulationID"])

    status_path = csv_dir / "status_values.csv"
    sea_best_time: dict[str, datetime] = {}
    sea_best_count: dict[str, float] = {}
    fw_best_time: dict[str, datetime] = {}
    fw_best_count: dict[str, float] = {}

    if status_path.exists():
        sea_info = (
            pairs[["SeaPopulationID", "SeaStartTime"]]
            .drop_duplicates()
            .rename(columns={"SeaPopulationID": "PopulationID", "SeaStartTime": "StartTime"})
        )
        fw_info = (
            pairs[["FWPopulationID", "FWEndTime"]]
            .drop_duplicates()
            .rename(columns={"FWPopulationID": "PopulationID", "FWEndTime": "EndTime"})
        )
        usecols = ["PopulationID", "StatusTime", "CurrentCount"]
        for chunk in pd.read_csv(status_path, usecols=usecols, chunksize=400_000):
            chunk = chunk[chunk["PopulationID"].isin(sea_ids.union(fw_ids))]
            if chunk.empty:
                continue
            chunk["StatusTime"] = pd.to_datetime(chunk["StatusTime"], errors="coerce")
            sea_chunk = chunk[chunk["PopulationID"].isin(sea_ids)].merge(sea_info, on="PopulationID", how="inner")
            if not sea_chunk.empty:
                sea_chunk = sea_chunk[sea_chunk["StatusTime"] >= sea_chunk["StartTime"]]
                if not sea_chunk.empty:
                    idx = sea_chunk.groupby("PopulationID")["StatusTime"].idxmin()
                    for _, row in sea_chunk.loc[idx].iterrows():
                        pid = row["PopulationID"]
                        st = row["StatusTime"]
                        if pid not in sea_best_time or st < sea_best_time[pid]:
                            sea_best_time[pid] = st
                            sea_best_count[pid] = row["CurrentCount"]
            fw_chunk = chunk[chunk["PopulationID"].isin(fw_ids)].merge(fw_info, on="PopulationID", how="inner")
            if not fw_chunk.empty:
                fw_chunk = fw_chunk[fw_chunk["StatusTime"] <= fw_chunk["EndTime"]]
                if not fw_chunk.empty:
                    idx = fw_chunk.groupby("PopulationID")["StatusTime"].idxmax()
                    for _, row in fw_chunk.loc[idx].iterrows():
                        pid = row["PopulationID"]
                        st = row["StatusTime"]
                        if pid not in fw_best_time or st > fw_best_time[pid]:
                            fw_best_time[pid] = st
                            fw_best_count[pid] = row["CurrentCount"]

    pairs["FWLastCount"] = pairs["FWPopulationID"].map(fw_best_count)
    pairs["FWLastCountTime"] = pairs["FWPopulationID"].map(fw_best_time)
    pairs["SeaFirstCount"] = pairs["SeaPopulationID"].map(sea_best_count)
    pairs["SeaFirstCountTime"] = pairs["SeaPopulationID"].map(sea_best_time)

    def ratio(row) -> float | None:
        if row["FWLastCount"] and row["SeaFirstCount"]:
            return float(row["SeaFirstCount"]) / float(row["FWLastCount"])
        return None

    pairs["CountRatio"] = pairs.apply(ratio, axis=1)
    pairs["Score"] = pairs["Score_Base"]
    for idx, row in pairs.iterrows():
        ratio_val = row["CountRatio"]
        if ratio_val is None:
            continue
        if 0.7 <= ratio_val <= 1.3:
            pairs.at[idx, "Score"] += 20
        elif 0.5 <= ratio_val <= 1.5:
            pairs.at[idx, "Score"] += 10

    pairs_sorted = pairs.sort_values(
        ["SeaPopulationID", "Score", "DiffDays_FWEnd_to_SeaStart"],
        ascending=[True, False, True],
    )
    best = pairs_sorted.groupby("SeaPopulationID").head(1)
    best = best[best["Score"] >= min_score]

    heuristic_fw_ids = set(best["FWPopulationID"].tolist())
    heuristic_sea_ids = set(best["SeaPopulationID"].tolist())

    # Write debug output
    report_path = output_dir / f"heuristic_fw_sea_links_{slug}.csv"
    pairs_sorted.to_csv(report_path, index=False)
    print(f"[heuristic] candidate report: {report_path}")
    print(f"[heuristic] selected links: {len(best)} (min_score={min_score})")

    return heuristic_sea_ids, heuristic_fw_ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Build full-lifecycle population members for an input batch")
    parser.add_argument("--batch-key", required=True, help="Input batch key (InputName|InputNumber|YearClass)")
    parser.add_argument(
        "--csv-dir",
        default=str(PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"),
        help="CSV directory (from bulk_extract_fishtalk.py)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "scripts" / "migration" / "output" / "input_stitching"),
        help="Output directory for stitched population files",
    )
    parser.add_argument("--max-gap-days", type=int, default=120, help="Max FW→Sea gap in days")
    parser.add_argument("--max-fw-batches", type=int, default=2, help="Select top N FW batches")
    parser.add_argument("--max-overlap-days", type=int, default=60, help="Allow FW batches overlapping sea start")
    parser.add_argument("--max-pre-smolt-batches", type=int, default=2, help="Select top N pre-smolt batches")
    parser.add_argument(
        "--max-pre-smolt-gap-days",
        type=int,
        default=180,
        help="Max gap between pre-smolt end and smolt start (days)",
    )
    parser.add_argument(
        "--max-pre-smolt-overlap-days",
        type=int,
        default=30,
        help="Allow pre-smolt batches overlapping smolt start (days)",
    )
    parser.add_argument(
        "--include-fw-batch",
        action="append",
        default=[],
        help="Explicit FW batch key(s) to include (repeatable)",
    )
    parser.add_argument("--skip-population-links", action="store_true", help="Ignore PopulationLink if available")
    parser.add_argument(
        "--heuristic-fw-sea",
        action="store_true",
        help="Non-canonical: attempt heuristic FW→Sea linking using hall + date + count alignment",
    )
    parser.add_argument("--heuristic-window-days", type=int, default=60, help="Heuristic FW window in days")
    parser.add_argument("--heuristic-min-score", type=int, default=70, help="Minimum heuristic score to accept")
    parser.add_argument(
        "--heuristic-include-smolt",
        action="store_true",
        help="Allow Smolt halls as FW candidates (default: Post-Smolt only)",
    )
    args = parser.parse_args()

    csv_dir = Path(args.csv_dir)
    output_dir = Path(args.output_dir)
    input_name, input_number, year_class = parse_batch_key(args.batch_key)

    input_records, input_by_pop = build_input_records(csv_dir)
    inputs_by_batch: dict[str, list[str]] = defaultdict(list)
    for record in input_records:
        batch_key = f"{record.input_name}|{record.input_number}|{record.year_class}"
        inputs_by_batch[batch_key].append(record.population_id)

    sea_key = f"{input_name}|{input_number}|{year_class}"
    sea_population_ids = inputs_by_batch.get(sea_key, [])
    if not sea_population_ids:
        print(f"[ERROR] No populations found for batch key {sea_key}")
        return 1

    pop_meta = build_population_meta(csv_dir)
    stages_by_pop = build_stage_index(csv_dir)
    names_by_pop = build_population_name_index(csv_dir)
    containers_by_id, org_units_by_id, grouping_by_container = build_container_indexes(csv_dir)
    slug = slugify(sea_key)

    heuristic_sea_ids: set[str] = set()
    heuristic_fw_ids: set[str] = set()
    if args.heuristic_fw_sea:
        heuristic_sea_ids, heuristic_fw_ids = build_heuristic_fw_sea_links(
            input_name=input_name,
            sea_population_ids=sea_population_ids,
            pop_meta=pop_meta,
            names_by_pop=names_by_pop,
            containers_by_id=containers_by_id,
            grouping_by_container=grouping_by_container,
            csv_dir=csv_dir,
            window_days=args.heuristic_window_days,
            min_score=args.heuristic_min_score,
            include_smolt=args.heuristic_include_smolt,
            output_dir=output_dir,
            slug=slug,
        )
        print(f"[heuristic] added sea populations: {len(heuristic_sea_ids)}")
        print(f"[heuristic] added FW populations: {len(heuristic_fw_ids)}")

    sea_start_times = [pop_meta.get(pid, PopulationMeta(pid, "", None, None)).start_time for pid in sea_population_ids]
    sea_start_times = [t for t in sea_start_times if t]
    sea_start = min(sea_start_times) if sea_start_times else None

    # Detect original yearclass + supplier codes from population names
    yearclass_counts = Counter()
    supplier_codes = Counter()
    for pid in sea_population_ids:
        name = names_by_pop.get(pid, "")
        yc = parse_yearclass_from_population_name(name)
        if yc:
            yearclass_counts[yc] += 1
        code = parse_supplier_code_from_population_name(name)
        if code:
            supplier_codes[code] += 1

    source_year_class = yearclass_counts.most_common(1)[0][0] if yearclass_counts else year_class
    supplier_code_set = {code for code, _ in supplier_codes.most_common(2)}

    # Build link graph if available
    link_graph = {}
    if not args.skip_population_links and (csv_dir / "population_links.csv").exists():
        link_graph = build_population_links(csv_dir)

    linked_population_ids: set[str] = set()
    if link_graph:
        queue = list(sea_population_ids)
        seen = set(queue)
        while queue:
            current = queue.pop()
            for neighbor in link_graph.get(current, set()):
                if neighbor in seen:
                    continue
                neighbor_input = input_by_pop.get(neighbor)
                if neighbor_input and neighbor_input.year_class == source_year_class:
                    seen.add(neighbor)
                    queue.append(neighbor)
        linked_population_ids = seen - set(sea_population_ids)

    # Build candidate FW batches
    candidate_batches: list[CandidateBatch] = []
    for batch_key, pop_ids in inputs_by_batch.items():
        batch_input_name, _, batch_year_class = parse_batch_key(batch_key)
        if batch_key == sea_key:
            continue
        if batch_year_class != source_year_class:
            continue

        stage_set = set()
        starts = []
        ends = []
        total_input = 0.0
        for pop_id in pop_ids:
            stage_info = stages_by_pop.get(pop_id)
            if stage_info:
                stage_set.update(stage_info.aquamind_stages)
            meta = pop_meta.get(pop_id)
            if meta and meta.start_time:
                starts.append(meta.start_time)
            if meta and meta.end_time:
                ends.append(meta.end_time)
            input_record = input_by_pop.get(pop_id)
            if input_record:
                total_input += input_record.input_count

        earliest = min(starts) if starts else None
        latest = max(ends) if ends else (max(starts) if starts else None)
        gap_days = (sea_start - latest).days if sea_start and latest else None
        linked_count = sum(1 for pid in pop_ids if pid in linked_population_ids)
        candidate_batches.append(
            CandidateBatch(
                batch_key=batch_key,
                population_ids=pop_ids,
                stage_set=stage_set,
                earliest_start=earliest,
                latest_end=latest,
                gap_days=gap_days,
                total_input=total_input,
                supplier_match=supplier_matches(batch_input_name, supplier_code_set),
                linked_population_count=linked_count,
            )
        )

    # Selection logic
    explicit_fw_batches = set(args.include_fw_batch or [])

    def gap_score(gap: int | None) -> int:
        if gap is None:
            return 99999
        if gap < 0 and abs(gap) <= args.max_overlap_days:
            return abs(gap)
        score = abs(gap)
        if gap < 0:
            score += 1000
        return score

    def smolt_rank(candidate: CandidateBatch) -> tuple:
        return (
            gap_score(candidate.gap_days),
            -candidate.linked_population_count,
            -int(candidate.supplier_match),
            -candidate.total_input,
            -candidate.population_count,
        )

    def pre_smolt_rank(candidate: CandidateBatch, gap_to_smolt: int | None, new_stage_count: int) -> tuple:
        return (
            -new_stage_count,
            gap_score(gap_to_smolt),
            -int(candidate.supplier_match),
            -candidate.total_input,
            -candidate.population_count,
        )

    linked_candidates = [c for c in candidate_batches if c.linked_population_count > 0]
    linked_candidates.sort(key=smolt_rank)
    smolt_candidates = [
        c
        for c in candidate_batches
        if c.has_fw and not c.has_sea and "Smolt" in c.stage_set
    ]
    smolt_candidates.sort(key=smolt_rank)
    ranked_candidates = sorted(candidate_batches, key=smolt_rank)

    selected_smolt: list[CandidateBatch] = []
    if explicit_fw_batches:
        selected_smolt = [c for c in candidate_batches if c.batch_key in explicit_fw_batches]
    elif linked_candidates:
        selected_smolt = linked_candidates[: args.max_fw_batches]
    else:
        for candidate in smolt_candidates:
            if candidate.gap_days is not None:
                if candidate.gap_days > args.max_gap_days:
                    continue
                if candidate.gap_days < -args.max_overlap_days:
                    continue
            selected_smolt.append(candidate)
            if len(selected_smolt) >= args.max_fw_batches:
                break

    smolt_start = None
    if selected_smolt:
        smolt_starts = [c.earliest_start for c in selected_smolt if c.earliest_start]
        smolt_start = min(smolt_starts) if smolt_starts else None
    if smolt_start is None:
        smolt_start = sea_start

    selected_stage_set: set[str] = set()
    for candidate in selected_smolt:
        selected_stage_set.update(candidate.stage_set)

    pre_smolt_candidates: list[tuple[CandidateBatch, int | None, int]] = []
    for candidate in candidate_batches:
        if candidate.has_sea:
            continue
        if not candidate.stage_set.intersection({"Egg&Alevin", "Fry", "Parr"}):
            continue
        if smolt_start and candidate.latest_end:
            gap_to_smolt = (smolt_start - candidate.latest_end).days
            if gap_to_smolt > args.max_pre_smolt_gap_days:
                continue
            if gap_to_smolt < -args.max_pre_smolt_overlap_days:
                continue
        else:
            gap_to_smolt = None
        new_stage_count = len(candidate.stage_set - selected_stage_set)
        pre_smolt_candidates.append((candidate, gap_to_smolt, new_stage_count))

    pre_smolt_candidates.sort(key=lambda item: pre_smolt_rank(item[0], item[1], item[2]))
    selected_pre_smolt = [
        candidate for candidate, _, _ in pre_smolt_candidates
        if candidate not in selected_smolt
    ][: args.max_pre_smolt_batches]

    selected_batches = selected_smolt + selected_pre_smolt

    selected_population_ids = set(sea_population_ids)
    if heuristic_sea_ids:
        selected_population_ids.update(heuristic_sea_ids)
    for candidate in selected_batches:
        selected_population_ids.update(candidate.population_ids)
    selected_population_ids.update(linked_population_ids)
    if heuristic_fw_ids:
        selected_population_ids.update(heuristic_fw_ids)

    # Output candidates report
    candidates_path = output_dir / f"full_lifecycle_candidates_{slug}.csv"
    candidate_rows = []
    for candidate in ranked_candidates:
        candidate_rows.append(
            {
                "batch_key": candidate.batch_key,
                "population_count": candidate.population_count,
                "stage_count": candidate.stage_count,
                "has_fw": candidate.has_fw,
                "has_sea": candidate.has_sea,
                "earliest_start": candidate.earliest_start.isoformat(sep=" ") if candidate.earliest_start else "",
                "latest_end": candidate.latest_end.isoformat(sep=" ") if candidate.latest_end else "",
                "gap_days": candidate.gap_days if candidate.gap_days is not None else "",
                "total_input": f"{candidate.total_input:,.0f}" if candidate.total_input else "",
                "supplier_match": candidate.supplier_match,
                "linked_population_count": candidate.linked_population_count,
                "selected": candidate in selected_batches,
            }
        )
    write_csv(
        candidates_path,
        fieldnames=[
            "batch_key",
            "population_count",
            "stage_count",
            "has_fw",
            "has_sea",
            "earliest_start",
            "latest_end",
            "gap_days",
            "total_input",
            "supplier_match",
            "linked_population_count",
            "selected",
        ],
        rows=candidate_rows,
    )

    # Output full lifecycle members
    members_path = output_dir / f"full_lifecycle_population_members_{slug}.csv"
    member_rows = []
    for pop_id in sorted(selected_population_ids):
        input_record = input_by_pop.get(pop_id)
        source_key = (
            f"{input_record.input_name}|{input_record.input_number}|{input_record.year_class}"
            if input_record
            else ""
        )
        meta = pop_meta.get(pop_id, PopulationMeta(pop_id, "", None, None))
        container = containers_by_id.get(meta.container_id, {})
        org_unit = org_units_by_id.get(container.get("OrgUnitID", ""), {})
        grouping = grouping_by_container.get(meta.container_id, {})

        stages = stages_by_pop.get(pop_id, PopulationStages(fishtalk_stages=[], aquamind_stages=[]))
        fishtalk_stages = ", ".join(stages.fishtalk_stages)
        aquamind_stages = ", ".join(stages.aquamind_stages)

        site = grouping.get("Site") or org_unit.get("Name", "")
        site_group = grouping.get("SiteGroup") or ""
        geography = determine_geography(site, site_group)

        hall_label = hall_label_from_group(grouping.get("ContainerGroup"))
        if not hall_label:
            hall_label = hall_label_from_official(container.get("OfficialID"))

        member_rows.append(
            {
                "batch_key": sea_key,
                "population_id": pop_id,
                "population_name": names_by_pop.get(pop_id, ""),
                "container_id": meta.container_id,
                "container_name": container.get("ContainerName", ""),
                "org_unit_name": org_unit.get("Name", ""),
                "geography": geography,
                "start_time": meta.start_time.isoformat(sep=" ") if meta.start_time else "",
                "end_time": meta.end_time.isoformat(sep=" ") if meta.end_time else "",
                "fishtalk_stages": fishtalk_stages,
                "aquamind_stages": aquamind_stages,
                "source_batch_key": source_key,
                "source_input_name": input_record.input_name if input_record else "",
                "source_year_class": input_record.year_class if input_record else "",
                "hall_label": hall_label,
                "official_id": container.get("OfficialID", ""),
                "heuristic_fw_sea": "true" if pop_id in heuristic_fw_ids or pop_id in heuristic_sea_ids else "",
            }
        )

    write_csv(
        members_path,
        fieldnames=[
            "batch_key",
            "population_id",
            "population_name",
            "container_id",
            "container_name",
            "org_unit_name",
            "geography",
            "start_time",
            "end_time",
            "fishtalk_stages",
            "aquamind_stages",
            "source_batch_key",
            "source_input_name",
            "source_year_class",
            "hall_label",
            "official_id",
            "heuristic_fw_sea",
        ],
        rows=member_rows,
    )

    print("\nFull lifecycle stitching report")
    print(f"Sea batch: {sea_key}")
    print(f"Sea populations: {len(sea_population_ids)}")
    print(f"Source yearclass (from names): {source_year_class}")
    if supplier_code_set:
        print(f"Supplier codes detected: {', '.join(sorted(supplier_code_set))}")
    print(f"Linked populations (PopulationLink): {len(linked_population_ids)}")
    print(f"Selected FW batches: {[c.batch_key for c in selected_batches]}")
    print(f"Total populations selected: {len(selected_population_ids)}")
    print(f"Candidates file: {candidates_path}")
    print(f"Members file: {members_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
