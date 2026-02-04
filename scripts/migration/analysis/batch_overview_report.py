#!/usr/bin/env python3
"""Generate a FishTalk batch overview report from CSV extracts.

CSV-only: uses files under scripts/migration/data/extract/.
Outputs a stage rollup CSV + Markdown summary with a Mermaid diagram.
"""

from __future__ import annotations

import argparse
import csv
import unicodedata
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path


DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
)


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


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in ascii_value)
    cleaned = "_".join(seg for seg in cleaned.split("_") if seg)
    return cleaned or "batch"


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
    if any(token in upper for token in ("ONGROW", "GROWER", "GRILSE", "BROODSTOCK")):
        return "Adult"
    return None


def load_population_ids(ext_inputs_path: Path, batch_key: str) -> list[str]:
    input_name, input_number, year_class = [part.strip() for part in batch_key.split("|")]
    population_ids: list[str] = []
    with ext_inputs_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if (row.get("InputName") or "").strip() != input_name:
                continue
            if (row.get("InputNumber") or "").strip() != input_number:
                continue
            if (row.get("YearClass") or "").strip() != year_class:
                continue
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id:
                population_ids.append(pop_id)
    return population_ids


def load_ext_inputs_for_populations(ext_inputs_path: Path, population_ids: set[str]) -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = defaultdict(list)
    with ext_inputs_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id in population_ids:
                rows[pop_id].append(row)
    return rows


def load_ext_populations_for_populations(ext_pops_path: Path, population_ids: set[str]) -> dict[str, dict]:
    data: dict[str, dict] = {}
    if not ext_pops_path.exists():
        return data
    with ext_pops_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id in population_ids:
                data[pop_id] = row
    return data


def load_populations(populations_path: Path, population_ids: set[str]) -> dict[str, dict]:
    info: dict[str, dict] = {}
    with populations_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id not in population_ids:
                continue
            info[pop_id] = {
                "container_id": (row.get("ContainerID") or "").strip(),
                "start_time": parse_dt((row.get("StartTime") or "").strip()),
                "end_time": parse_dt((row.get("EndTime") or "").strip()),
            }
    return info


def load_containers(containers_path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not containers_path.exists():
        return mapping
    with containers_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cid = (row.get("ContainerID") or "").strip()
            if cid:
                mapping[cid] = (row.get("ContainerName") or "").strip()
    return mapping


def load_container_org_units(containers_path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not containers_path.exists():
        return mapping
    with containers_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cid = (row.get("ContainerID") or "").strip()
            if not cid:
                continue
            org_unit = (row.get("OrgUnitID") or "").strip()
            if org_unit:
                mapping[cid] = org_unit
    return mapping


def load_org_unit_names(org_units_path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not org_units_path.exists():
        return mapping
    with org_units_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            oid = (row.get("OrgUnitID") or "").strip()
            if oid:
                mapping[oid] = (row.get("Name") or "").strip()
    return mapping


def load_container_metadata(grouped_org_path: Path) -> dict[str, dict]:
    mapping: dict[str, dict] = {}
    if not grouped_org_path.exists():
        return mapping
    with grouped_org_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cid = (row.get("ContainerID") or "").strip()
            if not cid:
                continue
            mapping[cid] = {
                "prod_stage": (row.get("ProdStage") or "").strip(),
                "site": (row.get("Site") or "").strip(),
                "site_group": (row.get("SiteGroup") or "").strip(),
                "company": (row.get("Company") or "").strip(),
            }
    return mapping


def normalize_token(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def parse_year_token(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) == 2:
        return f"20{digits}"
    return digits


def parse_population_name(name: str) -> dict[str, str]:
    """Parse PopulationName like '11 S24 SF MAI 24 (MAR 23)'."""
    raw = name or ""
    in_parens = ""
    if "(" in raw and ")" in raw:
        in_parens = raw[raw.find("(") + 1 : raw.find(")")]
    tokens = [t for t in raw.replace("(", " ").replace(")", " ").split() if t]
    supplier_codes = {"BM", "BF", "SF", "AG"}
    supplier = ""
    month_token = ""
    year_token = ""
    for tok in tokens:
        if tok.upper() in supplier_codes:
            supplier = tok.upper()
    # Heuristic: month token is often 3-letter, year token is numeric
    for tok in tokens:
        if tok.isdigit() and len(tok) in (2, 4):
            year_token = tok
        elif tok.isalpha() and len(tok) <= 4 and tok.upper() not in supplier_codes:
            month_token = tok.upper()
    year_class = ""
    if in_parens:
        # e.g., "MAR 23" or "2023"
        parts = in_parens.split()
        for part in reversed(parts):
            digits = parse_year_token(part)
            if digits:
                year_class = digits
                break
    return {
        "supplier_code": supplier,
        "month_token": month_token,
        "year_token": parse_year_token(year_token) if year_token else "",
        "year_class": year_class,
    }


def build_ext_inputs_index(ext_inputs_path: Path) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = defaultdict(list)
    with ext_inputs_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            year_class = (row.get("YearClass") or "").strip()
            index[year_class].append(row)
    return index


def build_ext_inputs_batch_summary(ext_inputs_path: Path) -> dict[str, dict]:
    summary: dict[str, dict] = {}
    with ext_inputs_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            input_name = (row.get("InputName") or "").strip()
            input_number = (row.get("InputNumber") or "").strip()
            year_class = (row.get("YearClass") or "").strip()
            if not input_name or not input_number or not year_class:
                continue
            key = f"{input_name}|{input_number}|{year_class}"
            entry = summary.setdefault(
                key,
                {
                    "start_times": [],
                    "population_ids": set(),
                    "input_count_sum": 0.0,
                },
            )
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id:
                entry["population_ids"].add(pop_id)
            try:
                entry["input_count_sum"] += float(row.get("InputCount") or 0.0)
            except ValueError:
                pass
            ts = parse_dt((row.get("StartTime") or "").strip())
            if ts:
                entry["start_times"].append(ts)
    return summary


SUPPLIER_KEYWORDS = {
    "BM": ["BENCHMARK", "BM"],
    "BF": ["BAKKAFROST", "BF"],
    "SF": ["STOFNFISKUR", "SF"],
    "AG": ["AQUAGEN", "AG"],
}


def score_input_candidate(row: dict, *, hints: dict) -> int:
    score = 0
    input_name = (row.get("InputName") or "").upper()
    input_number = (row.get("InputNumber") or "").strip()
    year_class = (row.get("YearClass") or "").strip()
    hint_year_class = hints.get("year_class", "")
    if hint_year_class and year_class == hint_year_class:
        score += 5
    supplier_code = hints.get("supplier_code", "")
    if supplier_code:
        for token in SUPPLIER_KEYWORDS.get(supplier_code, []):
            if token in input_name:
                score += 3
                break
    month_token = hints.get("month_token", "")
    if month_token and month_token.upper() in input_name:
        score += 2
    year_token = hints.get("year_token", "")
    if year_token and year_token in input_name:
        score += 2
    input_number_hint = hints.get("input_number", "")
    if input_number_hint and input_number == input_number_hint:
        score += 1
    return score


FAROE_SITEGROUPS = {"WEST", "NORTH", "SOUTH"}


def geography_from_sitegroup(site_group: str) -> str:
    if not site_group:
        return ""
    upper = site_group.strip().upper()
    if upper in FAROE_SITEGROUPS:
        return "Faroe Islands"
    return "Scotland"


def load_stage_names(production_stages_path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with production_stages_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stage_id = (row.get("StageID") or "").strip()
            if stage_id:
                mapping[stage_id] = (row.get("StageName") or "").strip()
    return mapping


def load_population_stage_events(
    population_stages_path: Path,
    population_ids: set[str],
) -> dict[str, list[tuple[datetime, str]]]:
    events: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    with population_stages_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id not in population_ids:
                continue
            ts = parse_dt((row.get("StartTime") or "").strip())
            if ts is None:
                continue
            stage_id = (row.get("StageID") or "").strip()
            events[pop_id].append((ts, stage_id))
    for pop_id in events:
        events[pop_id].sort(key=lambda item: item[0])
    return events


def load_operation_stage_events(
    operation_stage_changes_path: Path,
    population_ids: set[str],
) -> dict[str, list[tuple[datetime, str]]]:
    events: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    if not operation_stage_changes_path.exists():
        return events
    with operation_stage_changes_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id not in population_ids:
                continue
            ts = parse_dt((row.get("StageStartTime") or "").strip())
            if ts is None:
                ts = parse_dt((row.get("OperationTime") or "").strip())
            if ts is None:
                continue
            stage_id = (row.get("StageID") or "").strip()
            events[pop_id].append((ts, stage_id))
    for pop_id in events:
        events[pop_id].sort(key=lambda item: item[0])
    return events


def load_population_links(
    population_links_path: Path,
    population_ids: set[str] | None = None,
) -> dict[str, set[str]]:
    links: dict[str, set[str]] = defaultdict(set)
    if not population_links_path.exists():
        return links
    with population_links_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            src = (row.get("FromPopulationID") or "").strip()
            dst = (row.get("ToPopulationID") or "").strip()
            if not src or not dst:
                continue
            if population_ids is None or src in population_ids or dst in population_ids:
                links[src].add(dst)
                links[dst].add(src)
    return links


def expand_population_links(
    links: dict[str, set[str]],
    seed_ids: set[str],
    *,
    max_depth: int,
) -> set[str]:
    visited = set(seed_ids)
    frontier = set(seed_ids)
    for _ in range(max_depth):
        next_frontier = set()
        for node in frontier:
            for neighbor in links.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
        if not next_frontier:
            break
        frontier = next_frontier
    return visited


def load_status_snapshots(status_path: Path, population_ids: set[str]) -> tuple[dict[str, list[datetime]], dict[str, list[tuple[int, Decimal]]]]:
    times: dict[str, list[datetime]] = defaultdict(list)
    values: dict[str, list[tuple[int, Decimal]]] = defaultdict(list)
    with status_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id not in population_ids:
                continue
            ts = parse_dt((row.get("StatusTime") or "").strip())
            if ts is None:
                continue
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
            times[pop_id].append(ts)
            values[pop_id].append((count, biomass))
    return times, values


def snapshot_at_or_after(times: list[datetime], values: list[tuple[int, Decimal]], ts: datetime) -> tuple[int, Decimal]:
    if not times:
        return 0, Decimal("0.00")
    pos = bisect_left(times, ts)
    if pos < len(values):
        return values[pos]
    return values[-1]


def snapshot_at_or_before(times: list[datetime], values: list[tuple[int, Decimal]], ts: datetime) -> tuple[int, Decimal]:
    if not times:
        return 0, Decimal("0.00")
    pos = bisect_right(times, ts)
    if pos > 0:
        return values[pos - 1]
    return values[0]


def snapshot_first_nonzero_after(times: list[datetime], values: list[tuple[int, Decimal]], ts: datetime) -> tuple[int, Decimal]:
    if not times:
        return 0, Decimal("0.00")
    pos = bisect_left(times, ts)
    for idx in range(pos, len(values)):
        count, biom = values[idx]
        if count > 0 or biom > 0:
            return count, biom
    return values[pos] if pos < len(values) else values[-1]


def snapshot_last_nonzero_before(times: list[datetime], values: list[tuple[int, Decimal]], ts: datetime) -> tuple[int, Decimal]:
    if not times:
        return 0, Decimal("0.00")
    pos = bisect_right(times, ts)
    for idx in range(pos - 1, -1, -1):
        count, biom = values[idx]
        if count > 0 or biom > 0:
            return count, biom
    return values[pos - 1] if pos > 0 else values[0]


def load_events(path: Path, population_ids: set[str], *, time_col: str) -> dict[str, list[tuple[datetime, dict]]]:
    events: dict[str, list[tuple[datetime, dict]]] = defaultdict(list)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id not in population_ids:
                continue
            ts = parse_dt((row.get(time_col) or "").strip())
            if ts is None:
                continue
            events[pop_id].append((ts, row))
    for pop_id in events:
        events[pop_id].sort(key=lambda item: item[0])
    return events


def build_stage_intervals(
    population_ids: list[str],
    pop_info: dict[str, dict],
    stage_events: dict[str, list[tuple[datetime, str]]],
    stage_name_by_id: dict[str, str],
    snapshot_times: dict[str, list[datetime]],
    *,
    stage_source_label: str,
) -> list[dict]:
    intervals: list[dict] = []
    for pop_id in population_ids:
        info = pop_info.get(pop_id, {})
        pop_start = info.get("start_time")
        pop_end = info.get("end_time")
        events = stage_events.get(pop_id, [])
        if not events:
            if pop_start is None and pop_end is None:
                continue
            intervals.append(
                {
                    "population_id": pop_id,
                    "container_id": info.get("container_id", ""),
                    "stage_id": "",
                    "stage_name": "Unknown",
                    "aquamind_stage": "Unknown",
                    "start_time": pop_start,
                    "end_time": pop_end,
                }
            )
            continue
        for idx, (start, stage_id) in enumerate(events):
            end = events[idx + 1][0] if idx + 1 < len(events) else pop_end
            if end is None:
                times = snapshot_times.get(pop_id, [])
                end = times[-1] if times else start
            elif end <= start:
                times = snapshot_times.get(pop_id, [])
                if times and times[-1] > start:
                    end = times[-1]
            stage_name = stage_name_by_id.get(stage_id, "")
            aquamind_stage = fishtalk_stage_to_aquamind(stage_name) or "Unknown"
            intervals.append(
                {
                    "population_id": pop_id,
                    "container_id": info.get("container_id", ""),
                    "stage_id": stage_id,
                    "stage_name": stage_name or "Unknown",
                    "aquamind_stage": aquamind_stage,
                    "start_time": start,
                    "end_time": end,
                    "stage_source": stage_source_label,
                }
            )
    return intervals


def build_report(
    batch_key: str,
    csv_dir: Path,
    output_dir: Path,
    *,
    include_linked: bool,
    link_depth: int,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    population_ids = load_population_ids(csv_dir / "ext_inputs.csv", batch_key)
    base_pop_set = set(population_ids)
    pop_id_set = set(population_ids)
    links = load_population_links(csv_dir / "population_links.csv", None if include_linked else pop_id_set)
    linked_populations = set()
    if include_linked:
        expanded = expand_population_links(links, base_pop_set, max_depth=link_depth)
        linked_populations = expanded - base_pop_set
        pop_id_set.update(linked_populations)
        population_ids = sorted(pop_id_set)
    pop_info = load_populations(csv_dir / "populations.csv", pop_id_set)
    container_names = load_containers(csv_dir / "containers.csv")
    container_org_units = load_container_org_units(csv_dir / "containers.csv")
    org_unit_names = load_org_unit_names(csv_dir / "org_units.csv")
    container_metadata = load_container_metadata(csv_dir / "grouped_organisation.csv")
    ext_inputs_by_pop = load_ext_inputs_for_populations(csv_dir / "ext_inputs.csv", pop_id_set)
    ext_inputs_index = build_ext_inputs_index(csv_dir / "ext_inputs.csv")
    ext_inputs_batch_summary = build_ext_inputs_batch_summary(csv_dir / "ext_inputs.csv")
    ext_pops_by_pop = load_ext_populations_for_populations(csv_dir / "ext_populations.csv", pop_id_set)
    stage_name_by_id = load_stage_names(csv_dir / "production_stages.csv")
    op_stage_events = load_operation_stage_events(csv_dir / "operation_stage_changes.csv", pop_id_set)
    pop_stage_events = load_population_stage_events(csv_dir / "population_stages.csv", pop_id_set)
    snapshot_times, snapshot_values = load_status_snapshots(csv_dir / "status_values.csv", pop_id_set)

    feeding_events = load_events(csv_dir / "feeding_actions.csv", pop_id_set, time_col="FeedingTime")
    mortality_events = load_events(csv_dir / "mortality_actions.csv", pop_id_set, time_col="OperationStartTime")

    intervals: list[dict] = []
    for pop_id in population_ids:
        if pop_id in op_stage_events:
            intervals.extend(
                build_stage_intervals(
                    [pop_id],
                    pop_info,
                    {pop_id: op_stage_events[pop_id]},
                    stage_name_by_id,
                    snapshot_times,
                    stage_source_label="operation_stage_changes",
                )
            )
        else:
            intervals.extend(
                build_stage_intervals(
                    [pop_id],
                    pop_info,
                    {pop_id: pop_stage_events.get(pop_id, [])},
                    stage_name_by_id,
                    snapshot_times,
                    stage_source_label="population_stages",
                )
            )

    stage_rollup: dict[str, dict] = {}
    stage_edges: dict[tuple[str, str], int] = defaultdict(int)
    duration_rows: list[dict] = []

    # Build per-pop interval lists to derive transitions
    intervals_by_pop: dict[str, list[dict]] = defaultdict(list)
    for interval in intervals:
        intervals_by_pop[interval["population_id"]].append(interval)
    for pop_id in intervals_by_pop:
        intervals_by_pop[pop_id].sort(key=lambda item: item["start_time"] or datetime.min)

    for pop_id, pop_intervals in intervals_by_pop.items():
        for idx, interval in enumerate(pop_intervals):
            stage_key = interval["aquamind_stage"]
            stage_data = stage_rollup.setdefault(
                stage_key,
                {
                    "stage": stage_key,
                    "stage_name": interval["stage_name"],
                    "intervals": 0,
                    "population_ids": set(),
                    "container_ids": set(),
                    "start_min": None,
                    "end_max": None,
                    "entry_count_sum": 0,
                    "entry_biomass_sum": Decimal("0.00"),
                    "exit_count_sum": 0,
                    "exit_biomass_sum": Decimal("0.00"),
                    "feed_kg": 0.0,
                    "mortality_count": 0,
                    "mortality_biomass": 0.0,
                },
            )

            start = interval["start_time"]
            end = interval["end_time"] or interval["start_time"]
            if start is None:
                continue

            stage_data["intervals"] += 1
            stage_data["population_ids"].add(pop_id)
            if interval["container_id"]:
                stage_data["container_ids"].add(interval["container_id"])

            if stage_data["start_min"] is None or start < stage_data["start_min"]:
                stage_data["start_min"] = start
            if stage_data["end_max"] is None or end > stage_data["end_max"]:
                stage_data["end_max"] = end

            times = snapshot_times.get(pop_id, [])
            values = snapshot_values.get(pop_id, [])
            entry_count, entry_biomass = snapshot_first_nonzero_after(times, values, start)
            exit_count, exit_biomass = snapshot_last_nonzero_before(times, values, end)

            stage_data["entry_count_sum"] += entry_count
            stage_data["entry_biomass_sum"] += entry_biomass
            stage_data["exit_count_sum"] += exit_count
            stage_data["exit_biomass_sum"] += exit_biomass

            duration_days = (end - start).total_seconds() / 86400.0 if end and start else 0.0
            duration_rows.append(
                {
                    "stage": stage_key,
                    "stage_name": stage_data["stage_name"],
                    "population_id": pop_id,
                    "container_id": interval["container_id"],
                    "container_name": container_names.get(interval["container_id"], ""),
                    "start_time": start.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": end.strftime("%Y-%m-%d %H:%M:%S") if end else "",
                    "duration_days": f"{duration_days:.2f}",
                    "stage_source": interval.get("stage_source", ""),
                }
            )

            # Feed & mortality within interval
            feed_total = 0.0
            for ts, row in feeding_events.get(pop_id, []):
                if start <= ts <= end:
                    try:
                        feed_total += float(row.get("FeedAmountG") or 0.0) / 1000.0
                    except ValueError:
                        continue
            stage_data["feed_kg"] += feed_total

            mort_count = 0
            mort_biom = 0.0
            for ts, row in mortality_events.get(pop_id, []):
                if start <= ts <= end:
                    try:
                        mort_count += int(float(row.get("MortalityCount") or 0))
                    except ValueError:
                        pass
                    try:
                        mort_biom += float(row.get("MortalityBiomass") or 0.0)
                    except ValueError:
                        pass
            stage_data["mortality_count"] += mort_count
            stage_data["mortality_biomass"] += mort_biom

            # Build transition edges using next interval
            if idx + 1 < len(pop_intervals):
                next_interval = pop_intervals[idx + 1]
                from_stage = stage_key
                to_stage = next_interval["aquamind_stage"]
                next_start = next_interval["start_time"]
                if next_start and from_stage and to_stage:
                    next_entry_count, _ = snapshot_first_nonzero_after(
                        snapshot_times.get(pop_id, []),
                        snapshot_values.get(pop_id, []),
                        next_start,
                    )
                    stage_edges[(from_stage, to_stage)] += next_entry_count

    # Weight samples
    weight_samples: list[float] = []
    for sample_path in ("ext_weight_samples_v2.csv", "public_weight_samples.csv"):
        path = csv_dir / sample_path
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                pop_id = (row.get("PopulationID") or "").strip()
                if pop_id not in pop_id_set:
                    continue
                weight_val = row.get("AvgWeight")
                if weight_val in (None, ""):
                    continue
                try:
                    weight_samples.append(float(weight_val))
                except ValueError:
                    continue

    rollup_rows = []
    for stage_key, data in stage_rollup.items():
        entry_count_sum = data["entry_count_sum"]
        exit_count_sum = data["exit_count_sum"]
        entry_biomass_sum = data["entry_biomass_sum"]
        exit_biomass_sum = data["exit_biomass_sum"]
        avg_weight_start = (entry_biomass_sum * Decimal("1000") / entry_count_sum) if entry_count_sum else None
        avg_weight_end = (exit_biomass_sum * Decimal("1000") / exit_count_sum) if exit_count_sum else None
        rollup_rows.append(
            {
                "stage": stage_key,
                "stage_name": data["stage_name"],
                "intervals": data["intervals"],
                "population_count": len(data["population_ids"]),
                "container_count": len(data["container_ids"]),
                "stage_start": data["start_min"].strftime("%Y-%m-%d") if data["start_min"] else "",
                "stage_end": data["end_max"].strftime("%Y-%m-%d") if data["end_max"] else "",
                "entry_count_sum": entry_count_sum,
                "exit_count_sum": exit_count_sum,
                "avg_weight_start_g": f"{avg_weight_start:.1f}" if avg_weight_start else "",
                "avg_weight_end_g": f"{avg_weight_end:.1f}" if avg_weight_end else "",
                "feed_kg": f"{data['feed_kg']:.1f}",
                "mortality_count": data["mortality_count"],
                "mortality_biomass": f"{data['mortality_biomass']:.1f}",
                "container_ids": ";".join(sorted(data["container_ids"])),
            }
        )

    rollup_rows.sort(key=lambda row: row["stage"])

    rollup_csv = output_dir / "stage_rollup.csv"
    with rollup_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rollup_rows[0].keys()) if rollup_rows else [])
        if rollup_rows:
            writer.writeheader()
            writer.writerows(rollup_rows)

    duration_csv = output_dir / "stage_durations.csv"
    if duration_rows:
        with duration_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "stage",
                    "stage_name",
                    "population_id",
                    "container_id",
                    "container_name",
                    "start_time",
                    "end_time",
                    "duration_days",
                    "stage_source",
                ],
            )
            writer.writeheader()
            writer.writerows(duration_rows)

    # Aggregate per-container durations
    container_duration_rows: list[dict] = []
    if duration_rows:
        grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in duration_rows:
            grouped[(row["stage"], row["container_id"])].append(row)
        for (stage_key, container_id), rows in grouped.items():
            starts = [parse_dt(r["start_time"]) for r in rows if r.get("start_time")]
            ends = [parse_dt(r["end_time"]) for r in rows if r.get("end_time")]
            if not starts:
                continue
            min_start = min(starts)
            max_end = max(ends) if ends else min_start
            duration_days = (max_end - min_start).total_seconds() / 86400.0 if max_end and min_start else 0.0
            container_duration_rows.append(
                {
                    "stage": stage_key,
                    "stage_name": rows[0].get("stage_name", ""),
                    "container_id": container_id,
                    "container_name": rows[0].get("container_name", ""),
                    "start_time": min_start.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": max_end.strftime("%Y-%m-%d %H:%M:%S") if max_end else "",
                    "duration_days": f"{duration_days:.2f}",
                    "interval_count": len(rows),
                }
            )

    container_duration_csv = output_dir / "stage_container_durations.csv"
    if container_duration_rows:
        with container_duration_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "stage",
                    "stage_name",
                    "container_id",
                    "container_name",
                    "start_time",
                    "end_time",
                    "duration_days",
                    "interval_count",
                ],
            )
            writer.writeheader()
            writer.writerows(container_duration_rows)

    # Build Mermaid diagram
    if stage_edges:
        diagram_lines = ["flowchart LR"]
        for (src, dst), count in sorted(stage_edges.items()):
            diagram_lines.append(f"  {src.replace('&', '')} -->|{count}| {dst.replace('&', '')}")
    else:
        diagram_lines = ["flowchart LR", "  Adult"]

    # Summary timestamps
    start_times = [info["start_time"] for info in pop_info.values() if info.get("start_time")]
    end_times = [info["end_time"] for info in pop_info.values() if info.get("end_time")]
    batch_start = min(start_times).strftime("%Y-%m-%d") if start_times else ""
    batch_end = max(end_times).strftime("%Y-%m-%d") if end_times else ""
    batch_start_dt = min(start_times) if start_times else None

    # Growth samples stats
    weight_summary = ""
    if weight_samples:
        weight_samples.sort()
        weight_summary = (
            f"min={weight_samples[0]:.0f}g, "
            f"median={weight_samples[len(weight_samples)//2]:.0f}g, "
            f"max={weight_samples[-1]:.0f}g, n={len(weight_samples)}"
        )
    # Linked batch candidates (egg origins)
    linked_batches: dict[str, dict] = {}
    if include_linked:
        linked_set = pop_id_set - base_pop_set
        for pop_id in linked_set:
            for row in ext_inputs_by_pop.get(pop_id, []):
                input_name = (row.get("InputName") or "").strip()
                input_number = (row.get("InputNumber") or "").strip()
                year_class = (row.get("YearClass") or "").strip()
                if not input_name or not input_number or not year_class:
                    continue
                key = f"{input_name}|{input_number}|{year_class}"
                batch = linked_batches.setdefault(
                    key,
                    {
                        "input_name": input_name,
                        "input_number": input_number,
                        "year_class": year_class,
                        "population_ids": set(),
                        "input_count_sum": 0.0,
                        "start_times": [],
                    },
                )
                batch["population_ids"].add(pop_id)
                try:
                    batch["input_count_sum"] += float(row.get("InputCount") or 0.0)
                except ValueError:
                    pass
                ts = parse_dt((row.get("StartTime") or "").strip())
                if ts:
                    batch["start_times"].append(ts)

    linked_batch_rows = []
    for key, batch in linked_batches.items():
        starts = batch["start_times"]
        linked_batch_rows.append(
            {
                "batch_key": key,
                "population_count": len(batch["population_ids"]),
                "input_count_sum": f"{batch['input_count_sum']:.0f}",
                "earliest_start": min(starts).strftime("%Y-%m-%d") if starts else "",
                "latest_start": max(starts).strftime("%Y-%m-%d") if starts else "",
            }
        )
    linked_batch_rows.sort(key=lambda row: row["population_count"], reverse=True)

    linked_batch_csv = output_dir / "linked_batch_candidates.csv"
    if linked_batch_rows:
        with linked_batch_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "batch_key",
                    "population_count",
                    "input_count_sum",
                    "earliest_start",
                    "latest_start",
                ],
            )
            writer.writeheader()
            writer.writerows(linked_batch_rows)

    # Linked population candidates (fallback when Ext_Inputs_v2 is missing)
    linked_population_rows: list[dict] = []
    candidate_batch_scores: dict[str, dict] = {}
    if include_linked:
        linked_set = pop_id_set - base_pop_set
        for pop_id in sorted(linked_set):
            pop_row = pop_info.get(pop_id, {})
            ext_row = ext_pops_by_pop.get(pop_id, {})
            ext_inputs_rows = ext_inputs_by_pop.get(pop_id, [])
            input_name = (ext_inputs_rows[0].get("InputName") or "").strip() if ext_inputs_rows else ""
            input_number = (ext_inputs_rows[0].get("InputNumber") or "").strip() if ext_inputs_rows else ""
            year_class = (ext_inputs_rows[0].get("YearClass") or "").strip() if ext_inputs_rows else ""
            population_name = (ext_row.get("PopulationName") or "").strip()
            name_hints = parse_population_name(population_name)
            if not name_hints.get("year_class"):
                name_hints["year_class"] = parse_year_token((ext_row.get("InputYear") or "").strip())
            if not name_hints.get("year_class"):
                fishgroup = (ext_row.get("Fishgroup") or "").strip()
                if fishgroup:
                    name_hints["year_class"] = parse_year_token(fishgroup[:2])
            if not name_hints.get("year_class"):
                start_dt = pop_row.get("start_time")
                if start_dt:
                    name_hints["year_class"] = str(start_dt.year)
            name_hints["input_number"] = (ext_row.get("InputNumber") or "").strip()

            # Determine environment from container ProdStage
            container_id = pop_row.get("container_id", "")
            meta = container_metadata.get(container_id, {})
            prod_stage = meta.get("prod_stage", "")
            env_class = "SEA" if prod_stage.upper() in {"SEA", "MARINE"} else ("FW" if prod_stage else "")
            org_unit_id = container_org_units.get(container_id, "")
            org_unit_name = org_unit_names.get(org_unit_id, "")

            candidate_keys = []
            candidate_pool = []
            if name_hints.get("year_class"):
                candidate_pool = ext_inputs_index.get(name_hints["year_class"], [])
            else:
                # Fallback to all ext_inputs rows if year_class unknown
                for rows in ext_inputs_index.values():
                    candidate_pool.extend(rows)

            scored_candidates = []
            for row in candidate_pool:
                score = score_input_candidate(row, hints=name_hints)
                if score <= 0:
                    continue
                key = f"{(row.get('InputName') or '').strip()}|{(row.get('InputNumber') or '').strip()}|{(row.get('YearClass') or '').strip()}"
                scored_candidates.append((score, key))
            scored_candidates.sort(key=lambda item: item[0], reverse=True)
            for score, key in scored_candidates[:3]:
                candidate_keys.append(key)
                entry = candidate_batch_scores.setdefault(
                    key,
                    {"score_sum": 0, "population_ids": set()},
                )
                entry["score_sum"] += score
                entry["population_ids"].add(pop_id)

            stage_source = ""
            stage_name = ""
            aquamind_stage = ""
            if pop_id in op_stage_events and op_stage_events[pop_id]:
                stage_source = "operation_stage_changes"
                stage_name = stage_name_by_id.get(op_stage_events[pop_id][0][1], "")
                aquamind_stage = fishtalk_stage_to_aquamind(stage_name) or ""
            elif pop_id in pop_stage_events and pop_stage_events[pop_id]:
                stage_source = "population_stages"
                stage_name = stage_name_by_id.get(pop_stage_events[pop_id][0][1], "")
                aquamind_stage = fishtalk_stage_to_aquamind(stage_name) or ""

            linked_population_rows.append(
                {
                    "population_id": pop_id,
                    "container_id": pop_row.get("container_id", ""),
                    "container_name": container_names.get(container_id, ""),
                    "prod_stage": prod_stage,
                    "environment": env_class,
                    "site": meta.get("site", ""),
                    "site_group": meta.get("site_group", ""),
                    "company": meta.get("company", ""),
                    "org_unit_id": org_unit_id,
                    "org_unit_name": org_unit_name,
                    "start_time": pop_row.get("start_time").strftime("%Y-%m-%d %H:%M:%S") if pop_row.get("start_time") else "",
                    "end_time": pop_row.get("end_time").strftime("%Y-%m-%d %H:%M:%S") if pop_row.get("end_time") else "",
                    "input_name": input_name,
                    "input_number": input_number,
                    "year_class": year_class,
                    "population_name": population_name,
                    "input_year": (ext_row.get("InputYear") or "").strip(),
                    "input_number_ext": (ext_row.get("InputNumber") or "").strip(),
                    "fishgroup": (ext_row.get("Fishgroup") or "").strip(),
                    "inferred_supplier_code": name_hints.get("supplier_code", ""),
                    "inferred_month": name_hints.get("month_token", ""),
                    "inferred_year": name_hints.get("year_token", ""),
                    "inferred_year_class": name_hints.get("year_class", ""),
                    "candidate_batch_keys": ";".join(candidate_keys),
                    "stage_name": stage_name,
                    "aquamind_stage": aquamind_stage,
                    "stage_source": stage_source,
                }
            )

    linked_population_csv = output_dir / "linked_population_candidates.csv"
    if linked_population_rows:
        with linked_population_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "population_id",
                    "container_id",
                    "container_name",
                    "prod_stage",
                    "environment",
                    "site",
                    "site_group",
                    "company",
                    "org_unit_id",
                    "org_unit_name",
                    "start_time",
                    "end_time",
                    "input_name",
                    "input_number",
                    "year_class",
                    "population_name",
                    "input_year",
                    "input_number_ext",
                    "fishgroup",
                    "inferred_supplier_code",
                    "inferred_month",
                    "inferred_year",
                    "inferred_year_class",
                    "candidate_batch_keys",
                    "stage_name",
                    "aquamind_stage",
                    "stage_source",
                ],
            )
            writer.writeheader()
            writer.writerows(linked_population_rows)

    # Base batch geography (dominant site group)
    base_geography_counts: dict[str, int] = defaultdict(int)
    for pop_id in base_pop_set:
        container_id = pop_info.get(pop_id, {}).get("container_id", "")
        meta = container_metadata.get(container_id, {})
        geo = geography_from_sitegroup(meta.get("site_group", ""))
        if geo:
            base_geography_counts[geo] += 1
    base_geography = max(base_geography_counts, key=base_geography_counts.get) if base_geography_counts else ""

    candidate_batch_rows = []
    candidate_batch_rows_filtered = []
    rejected_rows = []
    for key, entry in candidate_batch_scores.items():
        candidate_pop_ids_full = list(ext_inputs_batch_summary.get(key, {}).get("population_ids", []))
        candidate_info_full = load_populations(csv_dir / "populations.csv", set(candidate_pop_ids_full))

        candidate_geo_counts: dict[str, int] = defaultdict(int)
        candidate_env_counts: dict[str, int] = defaultdict(int)
        candidate_station_counts: dict[str, int] = defaultdict(int)
        for pop_id in candidate_pop_ids_full:
            container_id = candidate_info_full.get(pop_id, {}).get("container_id", "")
            meta = container_metadata.get(container_id, {})
            prod_stage = meta.get("prod_stage", "").upper()
            env = "SEA" if prod_stage in {"SEA", "MARINE"} else ("FW" if prod_stage else "")
            if env:
                candidate_env_counts[env] += 1
            geo = geography_from_sitegroup(meta.get("site_group", ""))
            if geo:
                candidate_geo_counts[geo] += 1
            station_name = meta.get("site") or org_unit_names.get(container_org_units.get(container_id, ""), "")
            if station_name:
                candidate_station_counts[station_name] += 1
        candidate_geo = max(candidate_geo_counts, key=candidate_geo_counts.get) if candidate_geo_counts else ""
        env_fw_pct = candidate_env_counts.get("FW", 0) / max(1, sum(candidate_env_counts.values()))
        station_count = len(candidate_station_counts)

        summary = ext_inputs_batch_summary.get(key, {})
        start_times = summary.get("start_times", [])
        min_input_start = min(start_times) if start_times else None
        days_to_sea = None
        if batch_start_dt and min_input_start:
            days_to_sea = (batch_start_dt - min_input_start).days

        if not candidate_geo:
            geography_match = "unknown"
        else:
            geography_match = "yes" if (base_geography and candidate_geo == base_geography) else "no"
        time_window_ok = "yes" if (days_to_sea is None or days_to_sea >= 180) else "no"
        reasons = []
        if geography_match == "no":
            reasons.append("geo_mismatch")
        if geography_match == "unknown":
            reasons.append("geo_unknown")
        if env_fw_pct < 0.8:
            reasons.append("not_fw")
        if time_window_ok != "yes":
            reasons.append("too_short")
        rejection_reason = ";".join(reasons)

        row = {
            "batch_key": key,
            "score_sum": entry["score_sum"],
            "linked_population_count": len(entry["population_ids"]),
            "population_count": len(candidate_pop_ids_full),
            "candidate_geography": candidate_geo,
            "base_geography": base_geography,
            "geography_match": geography_match,
            "fw_env_pct": f"{env_fw_pct*100:.1f}",
            "days_to_sea_start": str(days_to_sea) if days_to_sea is not None else "",
            "time_window_ok": time_window_ok,
            "rejection_reason": rejection_reason,
            "station_count": station_count,
        }
        candidate_batch_rows.append(row)
        if geography_match == "yes" and time_window_ok == "yes" and env_fw_pct >= 0.8:
            candidate_batch_rows_filtered.append(row)
        else:
            rejected_rows.append(row)

    candidate_batch_rows.sort(key=lambda row: row["score_sum"], reverse=True)
    candidate_batch_rows_filtered.sort(key=lambda row: row["score_sum"], reverse=True)

    candidate_batch_csv = output_dir / "egg_origin_candidates.csv"
    if candidate_batch_rows:
        with candidate_batch_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "batch_key",
                    "score_sum",
                    "linked_population_count",
                    "population_count",
                    "candidate_geography",
                    "base_geography",
                    "geography_match",
                    "fw_env_pct",
                    "days_to_sea_start",
                    "time_window_ok",
                    "rejection_reason",
                    "station_count",
                ],
            )
            writer.writeheader()
            writer.writerows(candidate_batch_rows)

    # Validate top candidate batches with FW heuristics
    validation_rows: list[dict] = []
    for candidate in candidate_batch_rows_filtered[:3]:
        candidate_key = candidate["batch_key"]
        candidate_pop_ids = load_population_ids(csv_dir / "ext_inputs.csv", candidate_key)
        if not candidate_pop_ids:
            continue
        candidate_pop_set = set(candidate_pop_ids)
        candidate_info = load_populations(csv_dir / "populations.csv", candidate_pop_set)
        candidate_stage_events = load_operation_stage_events(csv_dir / "operation_stage_changes.csv", candidate_pop_set)
        fallback_stage_events = load_population_stage_events(csv_dir / "population_stages.csv", candidate_pop_set)
        candidate_snap_times, candidate_snap_vals = load_status_snapshots(csv_dir / "status_values.csv", candidate_pop_set)

        # Stage intervals for candidate
        candidate_intervals: list[dict] = []
        for pop_id in candidate_pop_ids:
            if pop_id in candidate_stage_events:
                candidate_intervals.extend(
                    build_stage_intervals(
                        [pop_id],
                        candidate_info,
                        {pop_id: candidate_stage_events[pop_id]},
                        stage_name_by_id,
                        candidate_snap_times,
                        stage_source_label="operation_stage_changes",
                    )
                )
            else:
                candidate_intervals.extend(
                    build_stage_intervals(
                        [pop_id],
                        candidate_info,
                        {pop_id: fallback_stage_events.get(pop_id, [])},
                        stage_name_by_id,
                        candidate_snap_times,
                        stage_source_label="population_stages",
                    )
                )

        # FW site distribution
        fw_sites = []
        container_ids = set()
        for pop_id in candidate_pop_ids:
            container_id = candidate_info.get(pop_id, {}).get("container_id", "")
            if not container_id:
                continue
            container_ids.add(container_id)
            meta = container_metadata.get(container_id, {})
            prod_stage = meta.get("prod_stage", "").upper()
            if prod_stage and prod_stage not in {"SEA", "MARINE"}:
                site = meta.get("site", "")
                if site:
                    fw_sites.append(site)
        site_counts: dict[str, int] = defaultdict(int)
        for site in fw_sites:
            site_counts[site] += 1
        dominant_site = ""
        dominant_site_pct = ""
        if site_counts:
            dominant_site = max(site_counts, key=site_counts.get)
            dominant_site_pct = f"{(site_counts[dominant_site] / max(1, len(fw_sites)) * 100):.1f}"

        # Stage duration medians for FW stages
        fw_stage_durations: dict[str, list[float]] = defaultdict(list)
        for interval in candidate_intervals:
            stage = interval.get("aquamind_stage", "")
            if stage in {"Egg&Alevin", "Fry", "Parr", "Smolt", "Post-Smolt"}:
                start = interval.get("start_time")
                end = interval.get("end_time") or start
                if start and end:
                    duration = (end - start).total_seconds() / 86400.0
                    fw_stage_durations[stage].append(duration)
        fw_stage_summary = []
        for stage, durations in fw_stage_durations.items():
            durations.sort()
            median = durations[len(durations) // 2] if durations else 0.0
            fw_stage_summary.append(f"{stage}:{median:.1f}d")
        fw_stage_summary_text = ";".join(sorted(fw_stage_summary))

        # Upward jump check (population counts increasing)
        upward_populations = 0
        upward_events = 0
        for pop_id in candidate_pop_ids:
            times = candidate_snap_times.get(pop_id, [])
            values = candidate_snap_vals.get(pop_id, [])
            if len(values) < 2:
                continue
            prev = values[0][0]
            local_up = 0
            for count, _ in values[1:]:
                if count > prev:
                    local_up += 1
                prev = count
            if local_up:
                upward_populations += 1
                upward_events += local_up
        upward_pop_pct = f"{(upward_populations / max(1, len(candidate_pop_ids)) * 100):.1f}"

        validation_rows.append(
            {
                "batch_key": candidate_key,
                "linked_population_count": candidate.get("linked_population_count", ""),
                "population_count": len(candidate_pop_ids),
                "container_count": len(container_ids),
                "fw_site_count": len(site_counts),
                "dominant_fw_site": dominant_site,
                "dominant_fw_site_pct": dominant_site_pct,
                "fw_stage_median_days": fw_stage_summary_text,
                "upward_jump_pop_pct": upward_pop_pct,
                "upward_jump_events": upward_events,
                "candidate_geography": candidate.get("candidate_geography", ""),
                "base_geography": candidate.get("base_geography", ""),
                "days_to_sea_start": candidate.get("days_to_sea_start", ""),
            }
        )

    validation_csv = output_dir / "egg_origin_candidate_validation.csv"
    if validation_rows:
        with validation_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "batch_key",
                    "linked_population_count",
                    "population_count",
                    "container_count",
                    "fw_site_count",
                    "dominant_fw_site",
                    "dominant_fw_site_pct",
                    "fw_stage_median_days",
                    "upward_jump_pop_pct",
                    "upward_jump_events",
                    "candidate_geography",
                    "base_geography",
                    "days_to_sea_start",
                ],
            )
            writer.writeheader()
            writer.writerows(validation_rows)

    report_path = output_dir / "batch_overview.md"
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write(f"# FishTalk Batch Overview (CSV-derived)\n\n")
        handle.write(f"Batch key: `{batch_key}`\n\n")
        handle.write(f"- Populations: {len(population_ids)}\n")
        handle.write(f"- Containers: {len({info.get('container_id') for info in pop_info.values() if info.get('container_id')})}\n")
        handle.write(f"- Time span: {batch_start} -> {batch_end}\n\n")
        handle.write("## Stage Rollup\n\n")
        if rollup_rows:
            handle.write("| Stage | Stage name | Pops | Containers | Start | End | Entry count | Exit count | Avg wt start (g) | Avg wt end (g) | Feed kg | Mortality count |\n")
            handle.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
            for row in rollup_rows:
                handle.write(
                    f"| {row['stage']} | {row['stage_name']} | {row['population_count']} | {row['container_count']} | "
                    f"{row['stage_start']} | {row['stage_end']} | {row['entry_count_sum']} | {row['exit_count_sum']} | "
                    f"{row['avg_weight_start_g']} | {row['avg_weight_end_g']} | {row['feed_kg']} | {row['mortality_count']} |\n"
                )
        else:
            handle.write("_No stage data found in population_stages.csv for this batch._\n")

        handle.write("\n## Stage Transition Diagram\n\n")
        handle.write("```mermaid\n")
        handle.write("\n".join(diagram_lines))
        handle.write("\n```\n\n")

        if include_linked:
            handle.write("## Linked Batch Candidates (via PopulationLink)\n\n")
            if linked_batch_rows:
                handle.write("| Batch key | Populations | Input count | Earliest input | Latest input |\n")
                handle.write("| --- | --- | --- | --- | --- |\n")
                for row in linked_batch_rows:
                    handle.write(
                        f"| {row['batch_key']} | {row['population_count']} | {row['input_count_sum']} | {row['earliest_start']} | {row['latest_start']} |\n"
                    )
            else:
                handle.write("_No linked batches with Ext_Inputs_v2 rows were found._\n")
            handle.write("\n")
            if linked_population_rows:
                handle.write("Linked population details are in `linked_population_candidates.csv`.\n\n")
            if candidate_batch_rows:
                handle.write("Egg-origin candidate batches (with geography/time flags) are in `egg_origin_candidates.csv`.\n")
            if validation_rows:
                handle.write("Candidate validation summary is in `egg_origin_candidate_validation.csv`.\n\n")
            else:
                handle.write("\n")

        if include_linked and candidate_batch_rows:
            handle.write("## Egg-Origin Candidate Batches (Heuristic)\n\n")
            if candidate_batch_rows_filtered:
                handle.write("| Batch key | Score | Linked pops | Candidate pops | Geo match | FW env % | Days to sea |\n")
                handle.write("| --- | --- | --- | --- | --- | --- | --- |\n")
                for row in candidate_batch_rows_filtered[:10]:
                    handle.write(
                        f"| {row['batch_key']} | {row['score_sum']} | {row['linked_population_count']} | {row['population_count']} | "
                        f"{row['geography_match']} | {row['fw_env_pct']} | {row['days_to_sea_start']} |\n"
                    )
                handle.write("\n")
            else:
                handle.write("_No candidates passed geo + FW filters. See rejected list below._\n\n")
            if rejected_rows:
                handle.write("### Rejected Candidates (Reason)\n\n")
                handle.write("| Batch key | Geo match | FW env % | Days to sea | Stations | Linked pops | Reason |\n")
                handle.write("| --- | --- | --- | --- | --- | --- | --- |\n")
                for row in rejected_rows[:10]:
                    handle.write(
                        f"| {row['batch_key']} | {row['geography_match']} | {row['fw_env_pct']} | "
                        f"{row['days_to_sea_start']} | {row['station_count']} | {row['linked_population_count']} | {row['rejection_reason']} |\n"
                    )
                handle.write("\n")

        if include_linked and validation_rows:
            handle.write("## Egg-Origin Candidate Validation (Heuristics)\n\n")
            handle.write("| Batch key | Linked pops | Pops | Containers | FW sites | Dominant FW site | Dominant % | FW stage medians | Upward jump pops | Upward jump events | Geo | Days to sea |\n")
            handle.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
            for row in validation_rows:
                handle.write(
                    f"| {row['batch_key']} | {row['linked_population_count']} | {row['population_count']} | {row['container_count']} | {row['fw_site_count']} | "
                    f"{row['dominant_fw_site']} | {row['dominant_fw_site_pct']} | {row['fw_stage_median_days']} | "
                    f"{row['upward_jump_pop_pct']}% | {row['upward_jump_events']} | {row['candidate_geography']} | {row['days_to_sea_start']} |\n"
                )
            handle.write("\n")

        # Stage duration summary
        handle.write("## Stage Durations (days)\n\n")
        if duration_rows:
            duration_by_stage: dict[str, list[float]] = defaultdict(list)
            for row in duration_rows:
                try:
                    duration_by_stage[row["stage"]].append(float(row["duration_days"]))
                except ValueError:
                    continue
            handle.write("| Stage | Interval count | Min | Median | Max | Avg |\n")
            handle.write("| --- | --- | --- | --- | --- | --- |\n")
            for stage_key, durations in sorted(duration_by_stage.items()):
                durations.sort()
                count = len(durations)
                median = durations[count // 2] if count else 0.0
                avg = sum(durations) / count if count else 0.0
                handle.write(
                    f"| {stage_key} | {count} | {durations[0]:.1f} | {median:.1f} | {durations[-1]:.1f} | {avg:.1f} |\n"
                )
            handle.write("\nDetailed durations per population/container are in `stage_durations.csv`.\n")
            if container_duration_rows:
                handle.write("Aggregated per-container durations are in `stage_container_durations.csv`.\n\n")
            else:
                handle.write("\n")
        else:
            handle.write("_No duration data available._\n\n")

        handle.write("## Growth Sample Weights (AvgWeight)\n\n")
        if weight_summary:
            handle.write(f"{weight_summary}\n\n")
        else:
            handle.write("_No weight samples found for this batch in ext_weight_samples_v2.csv or public_weight_samples.csv._\n\n")

        handle.write("## Data Gaps / Notes\n\n")
        handle.write("- Stage rollup uses population_stages.csv; if stage entries are sparse (e.g., only Ongrowing), the diagram will collapse to one stage.\n")
        handle.write("- Stage changes prefer operation_stage_changes.csv when present; fallback is population_stages.csv.\n")
        edges_touching = sum(len(links.get(pid, [])) for pid in base_pop_set)
        handle.write(
            f"- PopulationLink edges touching this batch: {edges_touching} (linked outside batch: {len(linked_populations)}; link depth={link_depth}).\n"
        )
        handle.write("- Some populations have identical StartTime/EndTime in populations.csv, which yields zero-length intervals; use per-container aggregation to interpret stage occupancy.\n")
        if include_linked and linked_population_rows:
            handle.write("- Linked populations without Ext_Inputs_v2 rows can be inspected in linked_population_candidates.csv (PopulationName/InputYear hints).\n")
            missing_meta = sum(
                1 for row in linked_population_rows
                if not row.get("prod_stage") and not row.get("site") and not row.get("site_group") and not row.get("org_unit_name")
            )
            if missing_meta:
                handle.write(
                    f"- {missing_meta} linked populations lack container metadata (ProdStage/Site/SiteGroup/OrgUnit); geography inference is limited.\n"
                )
        elif include_linked:
            handle.write("- Linked populations did not yield Ext_Inputs_v2 rows; check linked_population_candidates.csv for fallbacks if present.\n")
        handle.write("- Feed totals are derived from feeding_actions.csv (grams -> kg).\n")
        handle.write("- Mortality totals are derived from mortality_actions.csv.\n")
        handle.write("- Treatments, lice, and health journal records are not available in the current CSV extract set.\n")
        handle.write("- Container lists per stage are written to stage_rollup.csv for detailed inspection.\n")

        handle.write("\n## Next Steps (Egg-Origin Trace)\n\n")
        handle.write("1) Generate/inspect `linked_population_candidates.csv` (run with --include-linked-populations) for FW hints (PopulationName / InputYear / Fishgroup / container names).\n")
        handle.write("2) If no Ext_Inputs_v2 rows exist for linked populations, parse `ext_populations.csv` PopulationName to infer supplier + year-class, then search Ext_Inputs_v2 for matching InputName/YearClass.\n")
        handle.write("3) Filter candidate FW batches by container ProdStage (from grouped_organisation.csv) to ensure FW vs SEA separation.\n")
        handle.write("4) Use OperationProductionStageChange + population_stages to validate FW stage progression (Egg→Fry→Parr→Smolt) before linking to sea batch.\n")
        handle.write("5) Confirm container timelines align with FW→Sea transfer windows (populations Start/EndTime and SubTransfers edges).\n")

    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a FishTalk batch overview report from CSV extracts.")
    parser.add_argument("--batch-key", required=True, help="Input batch key: InputName|InputNumber|YearClass")
    parser.add_argument("--csv-dir", required=True, help="CSV extract directory")
    parser.add_argument("--output-dir", required=True, help="Output directory for report artifacts")
    parser.add_argument(
        "--include-linked-populations",
        action="store_true",
        help="Include populations linked via PopulationLink (one-hop) in the report",
    )
    parser.add_argument(
        "--link-depth",
        type=int,
        default=1,
        help="Depth of PopulationLink expansion when --include-linked-populations is set (default: 1)",
    )
    args = parser.parse_args()

    report_path = build_report(
        args.batch_key,
        Path(args.csv_dir),
        Path(args.output_dir),
        include_linked=args.include_linked_populations,
        link_depth=args.link_depth,
    )
    print(f"Wrote report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
