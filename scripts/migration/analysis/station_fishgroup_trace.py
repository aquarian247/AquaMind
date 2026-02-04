#!/usr/bin/env python3
"""Trace a FishTalk input/fish group across stations/halls using CSV extracts."""

from __future__ import annotations

import argparse
import csv
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
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


def normalize_text(value: str) -> str:
    normalized = " ".join((value or "").split()).strip().lower()
    return normalized


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in ascii_value)
    cleaned = "_".join(seg for seg in cleaned.split("_") if seg)
    return cleaned or "trace"


def hall_letter(label: str) -> str:
    if not label:
        return ""
    for ch in label:
        if ch.isalpha():
            return ch.upper()
    return ""


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
    if any(token in upper for token in ("ONGROW", "GROWER", "GRILSE", "BROODSTOCK", "HARVEST")):
        return "Adult"
    return None


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def load_ext_inputs(ext_inputs_path: Path, input_name: str, year_class: str | None) -> tuple[dict[str, list[dict]], set[str]]:
    input_rows: dict[str, list[dict]] = defaultdict(list)
    population_ids: set[str] = set()
    target_name = normalize_text(input_name)
    target_year = normalize_text(year_class or "")
    with ext_inputs_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if normalize_text(row.get("InputName") or "") != target_name:
                continue
            if year_class and normalize_text(row.get("YearClass") or "") != target_year:
                continue
            pop_id = (row.get("PopulationID") or "").strip()
            if not pop_id:
                continue
            population_ids.add(pop_id)
            input_rows[pop_id].append(row)
    return input_rows, population_ids


def load_ext_inputs_for_populations(ext_inputs_path: Path, population_ids: set[str]) -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = defaultdict(list)
    if not ext_inputs_path.exists():
        return rows
    with ext_inputs_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id in population_ids:
                rows[pop_id].append(row)
    return rows


def load_ext_populations(
    ext_populations_path: Path, population_ids: set[str], name_filter: str | None
) -> tuple[dict[str, dict], set[str]]:
    data: dict[str, dict] = {}
    name_matches: set[str] = set()
    if not ext_populations_path.exists():
        return data, name_matches
    target_name = normalize_text(name_filter or "")
    with ext_populations_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if not pop_id:
                continue
            if name_filter and normalize_text(row.get("PopulationName") or "") == target_name:
                name_matches.add(pop_id)
            if pop_id in population_ids or pop_id in name_matches:
                data[pop_id] = row
    return data, name_matches


def load_input_projects(input_projects_path: Path) -> dict[str, dict]:
    data: dict[str, dict] = {}
    if not input_projects_path.exists():
        return data
    with input_projects_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pid = (row.get("InputProjectID") or "").strip()
            if pid:
                data[pid] = row
    return data


def find_input_project_ids(
    input_projects: dict[str, dict], project_name: str | None, year_class: str | None
) -> list[str]:
    if not project_name:
        return []
    target = normalize_text(project_name)
    target_year = normalize_text(year_class or "")
    matches: list[str] = []
    for pid, row in input_projects.items():
        if normalize_text(row.get("ProjectName") or "") != target:
            continue
        if year_class and normalize_text(row.get("YearClass") or "") != target_year:
            continue
        matches.append(pid)
    return matches


def load_fish_group_history(
    fish_group_history_path: Path, input_project_ids: set[str]
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    pops_by_project: dict[str, set[str]] = defaultdict(set)
    projects_by_pop: dict[str, set[str]] = defaultdict(set)
    if not fish_group_history_path.exists():
        return pops_by_project, projects_by_pop
    with fish_group_history_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            proj_id = (row.get("InputProjectID") or "").strip()
            if proj_id not in input_project_ids:
                continue
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id:
                pops_by_project[proj_id].add(pop_id)
                projects_by_pop[pop_id].add(proj_id)
    return pops_by_project, projects_by_pop


def load_populations(populations_path: Path, population_ids: set[str]) -> dict[str, dict]:
    data: dict[str, dict] = {}
    with populations_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id not in population_ids:
                continue
            data[pop_id] = {
                "container_id": (row.get("ContainerID") or "").strip(),
                "start_time": parse_dt((row.get("StartTime") or "").strip()),
                "end_time": parse_dt((row.get("EndTime") or "").strip()),
            }
    return data


def load_containers(containers_path: Path) -> dict[str, dict]:
    data: dict[str, dict] = {}
    if not containers_path.exists():
        return data
    with containers_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cid = (row.get("ContainerID") or "").strip()
            if not cid:
                continue
            data[cid] = {
                "name": (row.get("ContainerName") or "").strip(),
                "org_unit_id": (row.get("OrgUnitID") or "").strip(),
                "official_id": (row.get("OfficialID") or "").strip(),
            }
    return data


def load_org_units(org_units_path: Path) -> dict[str, str]:
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


def load_grouped_org(grouped_org_path: Path) -> dict[str, dict]:
    data: dict[str, dict] = {}
    if not grouped_org_path.exists():
        return data
    with grouped_org_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cid = (row.get("ContainerID") or "").strip()
            if not cid:
                continue
            data[cid] = {
                "site": (row.get("Site") or "").strip(),
                "site_group": (row.get("SiteGroup") or "").strip(),
                "company": (row.get("Company") or "").strip(),
                "prod_stage": (row.get("ProdStage") or "").strip(),
                "container_group": (row.get("ContainerGroup") or "").strip(),
                "container_group_id": (row.get("ContainerGroupID") or "").strip(),
                "stand_name": (row.get("StandName") or "").strip(),
                "stand_id": (row.get("StandID") or "").strip(),
            }
    return data


def load_production_stages(stages_path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not stages_path.exists():
        return mapping
    with stages_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            sid = (row.get("StageID") or "").strip()
            if sid:
                mapping[sid] = (row.get("StageName") or "").strip()
    return mapping


def load_population_stages(pop_stages_path: Path, population_ids: set[str]) -> dict[str, list[dict]]:
    data: dict[str, list[dict]] = defaultdict(list)
    if not pop_stages_path.exists():
        return data
    with pop_stages_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id in population_ids:
                data[pop_id].append(row)
    return data


def load_operation_stage_changes(op_stage_path: Path, population_ids: set[str]) -> dict[str, list[dict]]:
    data: dict[str, list[dict]] = defaultdict(list)
    if not op_stage_path.exists():
        return data
    with op_stage_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id in population_ids:
                data[pop_id].append(row)
    return data


def load_subtransfer_end_times(sub_transfers_path: Path, population_ids: set[str]) -> dict[str, datetime]:
    times_by_pop: dict[str, list[datetime]] = defaultdict(list)
    if not sub_transfers_path.exists():
        return {}
    with sub_transfers_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            op_time = parse_dt((row.get("OperationTime") or "").strip())
            if not op_time:
                continue
            for key in ("SourcePopBefore", "SourcePopAfter"):
                pop_id = (row.get(key) or "").strip()
                if pop_id in population_ids:
                    times_by_pop[pop_id].append(op_time)
    return {pop_id: min(times) for pop_id, times in times_by_pop.items() if times}


def build_stage_events(
    population_ids: set[str],
    pop_stages: dict[str, list[dict]],
    op_stage_changes: dict[str, list[dict]],
    stage_names: dict[str, str],
    pop_meta: dict[str, dict],
) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    stage_events: dict[str, list[dict]] = {}
    stage_summaries: dict[str, dict] = {}
    for pop_id in population_ids:
        events_by_key: dict[tuple[datetime, str], dict] = {}
        sources_by_key: dict[tuple[datetime, str], set[str]] = defaultdict(set)

        for row in pop_stages.get(pop_id, []):
            stage_id = (row.get("StageID") or "").strip()
            stage_name = stage_names.get(stage_id, "").strip()
            start_time = parse_dt((row.get("StartTime") or "").strip())
            if not stage_name or not start_time:
                continue
            key = (start_time, stage_name)
            sources_by_key[key].add("population_stages")

        for row in op_stage_changes.get(pop_id, []):
            stage_id = (row.get("StageID") or "").strip()
            stage_name = stage_names.get(stage_id, "").strip()
            start_time = parse_dt((row.get("StageStartTime") or "").strip())
            if not start_time:
                start_time = parse_dt((row.get("OperationTime") or "").strip())
            if not stage_name or not start_time:
                continue
            key = (start_time, stage_name)
            sources_by_key[key].add("operation_stage_changes")

        for (start_time, stage_name), sources in sources_by_key.items():
            events_by_key[(start_time, stage_name)] = {
                "stage_start": start_time,
                "stage_name": stage_name,
                "sources": ",".join(sorted(sources)),
            }

        events = sorted(events_by_key.values(), key=lambda item: item["stage_start"])
        if events:
            pop_end = pop_meta.get(pop_id, {}).get("end_time")
            for idx, event in enumerate(events):
                next_start = events[idx + 1]["stage_start"] if idx + 1 < len(events) else pop_end
                event["stage_end"] = next_start
                if next_start and event["stage_start"]:
                    event["duration_days"] = (next_start - event["stage_start"]).days
                else:
                    event["duration_days"] = None
                event["lifecycle_stage"] = fishtalk_stage_to_aquamind(event["stage_name"])
        stage_events[pop_id] = events

        stage_sequence = [e["lifecycle_stage"] for e in events if e.get("lifecycle_stage")]
        stage_first = stage_sequence[0] if stage_sequence else None
        stage_last = stage_sequence[-1] if stage_sequence else None
        sources = sorted({src for e in events for src in (e.get("sources") or "").split(",") if src})

        stage_summaries[pop_id] = {
            "stage_event_count": len(events),
            "stage_first": stage_first,
            "stage_last": stage_last,
            "stage_sequence": " -> ".join(stage_sequence),
            "stage_sources": ",".join(sources),
        }

    return stage_events, stage_summaries


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def format_dt(value: datetime | None) -> str:
    if not value:
        return ""
    return value.isoformat(sep=" ")


def main() -> None:
    parser = argparse.ArgumentParser(description="Trace FishTalk input/fish group across station halls")
    parser.add_argument("--input-name", required=True, help="Ext_Inputs_v2.InputName")
    parser.add_argument("--year-class", default=None, help="Optional YearClass filter")
    parser.add_argument("--site", default=None, help="Optional station filter (e.g., S24 Strond)")
    parser.add_argument("--input-project-name", default=None, help="InputProjects.ProjectName")
    parser.add_argument("--input-project-id", default=None, help="InputProjects.InputProjectID")
    parser.add_argument(
        "--include-population-name",
        action="store_true",
        help="Also include populations whose Ext_Populations_v2.PopulationName matches input-name",
    )
    parser.add_argument(
        "--expected-halls",
        default="",
        help="Comma-separated list of expected hall/container groups to flag if missing",
    )
    parser.add_argument(
        "--infer-endtime",
        action="store_true",
        help="Infer missing EndTime from subtransfer time or next population start",
    )
    parser.add_argument(
        "--as-of",
        default=None,
        help="Fallback date (YYYY-MM-DD) to use when EndTime remains missing",
    )
    parser.add_argument("--input-dir", default="scripts/migration/data/extract")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir) if args.output_dir else Path(
        "aquamind/docs/progress/migration"
    ) / f"station_trace_{slugify(args.input_name)}"
    output_dir.mkdir(parents=True, exist_ok=True)

    ext_inputs_path = input_dir / "ext_inputs.csv"
    ext_pops_path = input_dir / "ext_populations.csv"
    input_projects_path = input_dir / "input_projects.csv"
    fish_group_history_path = input_dir / "fish_group_history.csv"
    populations_path = input_dir / "populations.csv"
    grouped_org_path = input_dir / "grouped_organisation.csv"
    containers_path = input_dir / "containers.csv"
    org_units_path = input_dir / "org_units.csv"
    pop_stages_path = input_dir / "population_stages.csv"
    op_stage_path = input_dir / "operation_stage_changes.csv"
    sub_transfers_path = input_dir / "sub_transfers.csv"
    production_stages_path = input_dir / "production_stages.csv"

    population_ids: set[str] = set()
    input_project_ids: list[str] = []
    input_project_name = args.input_project_name
    input_projects = load_input_projects(input_projects_path)

    pop_to_projects: dict[str, set[str]] = {}
    if args.input_project_id or args.input_project_name:
        if args.input_project_id:
            input_project_ids = [args.input_project_id.strip()]
        else:
            input_project_ids = find_input_project_ids(input_projects, input_project_name, args.year_class)
        if not input_project_ids:
            raise SystemExit("No InputProjectID matches the provided input-project filters.")
        pops_by_project, pop_to_projects = load_fish_group_history(
            fish_group_history_path, set(input_project_ids)
        )
        for pop_set in pops_by_project.values():
            population_ids.update(pop_set)
        input_rows_by_pop = load_ext_inputs_for_populations(ext_inputs_path, population_ids)
        ext_pops, name_matches = load_ext_populations(ext_pops_path, population_ids, None)
    else:
        input_rows_by_pop, population_ids = load_ext_inputs(ext_inputs_path, args.input_name, args.year_class)
        ext_pops, name_matches = load_ext_populations(
            ext_pops_path, population_ids, args.input_name if args.include_population_name else None
        )
        if name_matches:
            population_ids.update(name_matches)

    if not population_ids:
        raise SystemExit(
            f"No populations found for InputName='{args.input_name}' YearClass='{args.year_class or '*'}'"
        )
    pop_meta = load_populations(populations_path, population_ids)
    containers = load_containers(containers_path)
    org_units = load_org_units(org_units_path)
    grouped_org = load_grouped_org(grouped_org_path)
    stage_names = load_production_stages(production_stages_path)
    pop_stages = load_population_stages(pop_stages_path, population_ids)
    op_stage_changes = load_operation_stage_changes(op_stage_path, population_ids)

    stage_events, stage_summaries = build_stage_events(population_ids, pop_stages, op_stage_changes, stage_names, pop_meta)
    subtransfer_end_times = load_subtransfer_end_times(sub_transfers_path, population_ids) if args.infer_endtime else {}

    # Build next-start lookups for inference
    next_start_in_container: dict[str, datetime] = {}
    next_start_in_group: dict[str, datetime] = {}
    if args.infer_endtime:
        container_to_pops: dict[str, list[tuple[str, datetime]]] = defaultdict(list)
        group_starts: list[tuple[str, datetime]] = []
        for pop_id in population_ids:
            meta = pop_meta.get(pop_id, {})
            ext_row = ext_pops.get(pop_id, {})
            start_time = parse_dt((ext_row.get("StartTime") or "").strip()) or meta.get("start_time")
            if not start_time:
                continue
            container_id = (ext_row.get("ContainerID") or meta.get("container_id") or "").strip()
            if container_id:
                container_to_pops[container_id].append((pop_id, start_time))
            group_starts.append((pop_id, start_time))

        for container_id, entries in container_to_pops.items():
            entries.sort(key=lambda item: item[1])
            for idx, (pop_id, current_time) in enumerate(entries[:-1]):
                j = idx + 1
                while j < len(entries) and entries[j][1] <= current_time:
                    j += 1
                if j < len(entries):
                    next_start_in_container[pop_id] = entries[j][1]

        group_starts.sort(key=lambda item: item[1])
        for idx, (pop_id, current_time) in enumerate(group_starts[:-1]):
            j = idx + 1
            while j < len(group_starts) and group_starts[j][1] <= current_time:
                j += 1
            if j < len(group_starts):
                next_start_in_group[pop_id] = group_starts[j][1]

    as_of = parse_date(args.as_of) if args.as_of else None

    segments: list[dict] = []
    station_counts: Counter[str] = Counter()
    hall_counts: Counter[str] = Counter()
    missing_metadata = Counter()
    site_filter = normalize_text(args.site) if args.site else None

    for pop_id in sorted(population_ids):
        ext_row = ext_pops.get(pop_id, {})
        pop_row = pop_meta.get(pop_id, {})
        container_id = (ext_row.get("ContainerID") or pop_row.get("container_id") or "").strip()
        container_meta = grouped_org.get(container_id, {})
        container_info = containers.get(container_id, {})
        org_unit_name = org_units.get(container_info.get("org_unit_id", ""), "")

        site_name = container_meta.get("site") or org_unit_name
        site_group = container_meta.get("site_group")
        container_group = container_meta.get("container_group") or container_info.get("official_id", "")
        prod_stage = container_meta.get("prod_stage")

        station_match = True
        if site_filter:
            station_match = normalize_text(site_name) == site_filter

        if site_name:
            station_counts[site_name] += 1
        else:
            missing_metadata["missing_site"] += 1

        if container_group:
            hall_counts[container_group] += 1
        else:
            missing_metadata["missing_hall"] += 1

        if not container_info.get("name"):
            missing_metadata["missing_container_name"] += 1

        stage_summary = stage_summaries.get(pop_id, {})
        if not stage_summary.get("stage_event_count"):
            missing_metadata["missing_stage_events"] += 1

        input_rows = input_rows_by_pop.get(pop_id, [])
        input_name = (input_rows[0].get("InputName") or "").strip() if input_rows else ""
        input_number = (input_rows[0].get("InputNumber") or "").strip() if input_rows else ""
        year_class = (input_rows[0].get("YearClass") or "").strip() if input_rows else ""
        if not input_name:
            input_name = (ext_row.get("PopulationName") or "").strip()
        if not input_number:
            input_number = (ext_row.get("InputNumber") or "").strip()
        if not year_class:
            year_class = (ext_row.get("InputYear") or "").strip()

        project_ids = sorted(pop_to_projects.get(pop_id, []))
        project_names = []
        for pid in project_ids:
            project = input_projects.get(pid) if input_projects else None
            if project:
                project_names.append((project.get("ProjectName") or "").strip())
        project_id_value = ";".join(project_ids)
        project_name_value = ";".join([name for name in project_names if name])

        end_time_raw = parse_dt((ext_row.get("EndTime") or "").strip()) or pop_row.get("end_time")
        start_time_value = parse_dt((ext_row.get("StartTime") or "").strip()) or pop_row.get("start_time")
        end_time_effective = end_time_raw
        end_time_source = "source"
        if args.infer_endtime and not end_time_raw:
            candidates = []
            candidate_sources: dict[datetime, str] = {}
            st = start_time_value
            sub_time = subtransfer_end_times.get(pop_id)
            if sub_time and (st is None or sub_time > st):
                candidates.append(sub_time)
                candidate_sources[sub_time] = "subtransfer"
            next_in_container = next_start_in_container.get(pop_id)
            if next_in_container and (st is None or next_in_container > st):
                candidates.append(next_in_container)
                candidate_sources[next_in_container] = "next_container_start"
            next_in_group = next_start_in_group.get(pop_id)
            if next_in_group and (st is None or next_in_group > st):
                candidates.append(next_in_group)
                candidate_sources[next_in_group] = "next_group_start"
            if candidates:
                end_time_effective = min(candidates)
                end_time_source = candidate_sources.get(end_time_effective, "inferred")
            elif as_of and (st is None or as_of > st):
                end_time_effective = as_of
                end_time_source = "as_of"

        segments.append(
            {
                "population_id": pop_id,
                "input_name": input_name,
                "input_number": input_number,
                "year_class": year_class,
                "input_project_id": project_id_value,
                "input_project_name": project_name_value,
                "fishgroup": (ext_row.get("Fishgroup") or "").strip(),
                "population_name": (ext_row.get("PopulationName") or "").strip(),
                "container_id": container_id,
                "container_name": container_info.get("name", ""),
                "container_group": container_group,
                "hall_letter": hall_letter(container_group),
                "site": site_name,
                "site_group": site_group,
                "prod_stage": prod_stage,
                "org_unit_name": org_unit_name,
                "start_time": format_dt(start_time_value),
                "end_time": format_dt(end_time_raw),
                "end_time_effective": format_dt(end_time_effective),
                "end_time_source": end_time_source,
                "stage_first": stage_summary.get("stage_first", ""),
                "stage_last": stage_summary.get("stage_last", ""),
                "stage_event_count": stage_summary.get("stage_event_count", 0),
                "stage_sources": stage_summary.get("stage_sources", ""),
                "station_match": "yes" if station_match else "no",
            }
        )

    write_csv(
        output_dir / "population_segments.csv",
        segments,
        [
            "population_id",
            "input_name",
            "input_number",
            "year_class",
            "input_project_id",
            "input_project_name",
            "fishgroup",
            "population_name",
            "container_id",
            "container_name",
            "container_group",
            "hall_letter",
            "site",
            "site_group",
            "prod_stage",
            "org_unit_name",
            "start_time",
            "end_time",
            "end_time_effective",
            "end_time_source",
            "stage_first",
            "stage_last",
            "stage_event_count",
            "stage_sources",
            "station_match",
        ],
    )

    stage_rows: list[dict] = []
    for pop_id, events in stage_events.items():
        ext_row = ext_pops.get(pop_id, {})
        pop_row = pop_meta.get(pop_id, {})
        container_id = (ext_row.get("ContainerID") or pop_row.get("container_id") or "").strip()
        container_meta = grouped_org.get(container_id, {})
        container_info = containers.get(container_id, {})
        site_name = container_meta.get("site") or org_units.get(container_info.get("org_unit_id", ""), "")
        container_group = container_meta.get("container_group") or container_info.get("official_id", "")
        for event in events:
            stage_rows.append(
                {
                    "population_id": pop_id,
                    "stage_name": event.get("stage_name"),
                    "lifecycle_stage": event.get("lifecycle_stage"),
                    "stage_start": format_dt(event.get("stage_start")),
                    "stage_end": format_dt(event.get("stage_end")),
                    "duration_days": event.get("duration_days"),
                    "sources": event.get("sources"),
                    "container_name": container_info.get("name", ""),
                    "container_group": container_group,
                    "site": site_name,
                    "fishgroup": (ext_row.get("Fishgroup") or "").strip(),
                }
            )

    write_csv(
        output_dir / "stage_timeline.csv",
        stage_rows,
        [
            "population_id",
            "stage_name",
            "lifecycle_stage",
            "stage_start",
            "stage_end",
            "duration_days",
            "sources",
            "container_name",
            "container_group",
            "site",
            "fishgroup",
        ],
    )

    hall_summary: dict[str, dict] = {}
    for seg in segments:
        hall = seg.get("container_group") or "Unknown"
        entry = hall_summary.setdefault(
            hall,
            {
                "hall": hall,
                "hall_letter": hall_letter(hall),
                "container_ids": set(),
                "population_ids": set(),
                "start_times": [],
                "end_times": [],
                "lifecycle_stages": set(),
            },
        )
        entry["container_ids"].add(seg.get("container_id"))
        entry["population_ids"].add(seg.get("population_id"))
        if seg.get("start_time"):
            entry["start_times"].append(seg.get("start_time"))
        end_val = seg.get("end_time_effective") or seg.get("end_time")
        if end_val:
            entry["end_times"].append(end_val)
        if seg.get("stage_last"):
            entry["lifecycle_stages"].add(seg.get("stage_last"))

    hall_rows: list[dict] = []
    for hall, entry in hall_summary.items():
        starts = [parse_dt(val) for val in entry["start_times"] if val]
        ends = [parse_dt(val) for val in entry["end_times"] if val]
        start_min = min(starts) if starts else None
        start_max = max(starts) if starts else None
        end_min = min(ends) if ends else None
        end_max = max(ends) if ends else None
        span_days = (end_max - start_min).days if start_min and end_max else None
        hall_rows.append(
            {
                "hall": hall,
                "hall_letter": entry["hall_letter"],
                "container_count": len([cid for cid in entry["container_ids"] if cid]),
                "population_count": len([pid for pid in entry["population_ids"] if pid]),
                "start_min": format_dt(start_min),
                "start_max": format_dt(start_max),
                "end_min": format_dt(end_min),
                "end_max": format_dt(end_max),
                "span_days": span_days,
                "lifecycle_stages": ", ".join(sorted(stage for stage in entry["lifecycle_stages"] if stage)),
            }
        )

    expected_halls = [h.strip() for h in args.expected_halls.split(",") if h.strip()]
    for hall in expected_halls:
        if hall not in hall_summary:
            hall_rows.append(
                {
                    "hall": hall,
                    "hall_letter": hall_letter(hall),
                    "container_count": 0,
                    "population_count": 0,
                    "start_min": "",
                    "start_max": "",
                    "end_min": "",
                    "end_max": "",
                    "span_days": "",
                    "lifecycle_stages": "",
                }
            )

    write_csv(
        output_dir / "hall_summary.csv",
        sorted(hall_rows, key=lambda row: (row.get("hall_letter") or "Z", row.get("hall") or "")),
        [
            "hall",
            "hall_letter",
            "container_count",
            "population_count",
            "start_min",
            "start_max",
            "end_min",
            "end_max",
            "span_days",
            "lifecycle_stages",
        ],
    )

    container_summary: dict[str, dict] = {}
    for seg in segments:
        cid = seg.get("container_id") or ""
        entry = container_summary.setdefault(
            cid,
            {
                "container_id": cid,
                "container_name": seg.get("container_name"),
                "hall": seg.get("container_group"),
                "hall_letter": seg.get("hall_letter"),
                "site": seg.get("site"),
                "start_times": [],
                "end_times": [],
                "population_ids": set(),
                "stage_sequences": set(),
            },
        )
        if seg.get("start_time"):
            entry["start_times"].append(seg.get("start_time"))
        end_val = seg.get("end_time_effective") or seg.get("end_time")
        if end_val:
            entry["end_times"].append(end_val)
        entry["population_ids"].add(seg.get("population_id"))
        stage_seq = stage_summaries.get(seg.get("population_id"), {}).get("stage_sequence")
        if stage_seq:
            entry["stage_sequences"].add(stage_seq)

    container_rows: list[dict] = []
    for cid, entry in container_summary.items():
        starts = [parse_dt(val) for val in entry["start_times"] if val]
        ends = [parse_dt(val) for val in entry["end_times"] if val]
        start_min = min(starts) if starts else None
        end_max = max(ends) if ends else None
        duration_days = (end_max - start_min).days if start_min and end_max else None
        container_rows.append(
            {
                "container_id": cid,
                "container_name": entry.get("container_name"),
                "hall": entry.get("hall"),
                "hall_letter": entry.get("hall_letter"),
                "site": entry.get("site"),
                "start_min": format_dt(start_min),
                "end_max": format_dt(end_max),
                "duration_days": duration_days,
                "population_count": len([pid for pid in entry["population_ids"] if pid]),
                "stage_sequences": " | ".join(sorted(entry["stage_sequences"])) if entry["stage_sequences"] else "",
            }
        )

    write_csv(
        output_dir / "container_durations.csv",
        sorted(container_rows, key=lambda row: (row.get("hall_letter") or "Z", row.get("container_name") or "")),
        [
            "container_id",
            "container_name",
            "hall",
            "hall_letter",
            "site",
            "start_min",
            "end_max",
            "duration_days",
            "population_count",
            "stage_sequences",
        ],
    )

    station_rows = [
        {"site": site, "population_count": count} for site, count in station_counts.most_common()
    ]
    write_csv(output_dir / "station_summary.csv", station_rows, ["site", "population_count"])

    stage_counter: Counter[str] = Counter()
    for events in stage_events.values():
        for event in events:
            lifecycle = event.get("lifecycle_stage")
            if lifecycle:
                stage_counter[lifecycle] += 1

    stage_rows = [{"lifecycle_stage": stage, "event_count": count} for stage, count in stage_counter.items()]
    write_csv(output_dir / "stage_summary.csv", stage_rows, ["lifecycle_stage", "event_count"])

    # Markdown report
    report_path = output_dir / "station_trace_report.md"
    earliest_start = min(
        (parse_dt(seg["start_time"]) for seg in segments if seg.get("start_time")), default=None
    )
    latest_end = max((parse_dt(seg["end_time"]) for seg in segments if seg.get("end_time")), default=None)
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write(f"# Station Trace: {args.input_name}\n\n")
        handle.write("## Scope\n")
        handle.write(f"- InputName: {args.input_name}\n")
        handle.write(f"- YearClass filter: {args.year_class or 'any'}\n")
        handle.write(f"- Station filter: {args.site or 'none'}\n")
        if input_project_ids:
            handle.write(f"- InputProjectIDs: {', '.join(input_project_ids)}\n")
            if input_project_name:
                handle.write(f"- InputProjectName: {input_project_name}\n")
        handle.write(f"- Populations: {len(population_ids)}\n")
        if name_matches:
            handle.write(f"- PopulationName matches included: {len(name_matches)}\n")
        handle.write(f"- Containers: {len({seg['container_id'] for seg in segments if seg.get('container_id')})}\n")
        if earliest_start:
            handle.write(f"- Earliest population start: {format_dt(earliest_start)}\n")
        if latest_end:
            handle.write(f"- Latest population end: {format_dt(latest_end)}\n")
        handle.write("\n")

        handle.write("## Station Distribution\n")
        for row in station_rows:
            handle.write(f"- {row['site']}: {row['population_count']} populations\n")
        handle.write("\n")

        handle.write("## Hall Summary (ContainerGroup)\n")
        for row in sorted(hall_rows, key=lambda r: (r.get("hall_letter") or "Z", r.get("hall") or "")):
            handle.write(
                f"- {row['hall']}: containers={row['container_count']} populations={row['population_count']} "
                f"span_days={row['span_days'] or ''} stages={row['lifecycle_stages'] or ''}\n"
            )
        handle.write("\n")

        if args.infer_endtime:
            handle.write("## EndTime Inference\n")
            handle.write("- end_time_effective uses the earliest of: subtransfer time, next container start, next group start\n")
            if as_of:
                handle.write(f"- as_of fallback: {format_dt(as_of)}\n")
            handle.write("\n")

        if expected_halls:
            missing = [hall for hall in expected_halls if hall not in hall_summary]
            handle.write("## Expected Halls Missing in CSV\n")
            if missing:
                for hall in missing:
                    handle.write(f"- {hall}\n")
            else:
                handle.write("- None\n")
            handle.write("\n")

        handle.write("## Stage Event Coverage\n")
        for row in stage_rows:
            handle.write(f"- {row['lifecycle_stage']}: {row['event_count']} events\n")
        handle.write("\n")

        handle.write("## Data Gaps\n")
        for key, value in missing_metadata.items():
            handle.write(f"- {key}: {value}\n")


if __name__ == "__main__":
    main()
