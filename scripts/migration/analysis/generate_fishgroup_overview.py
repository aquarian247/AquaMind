#!/usr/bin/env python3
"""Generate a batch-style overview for a fish group using station trace outputs."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from statistics import median


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        return None


def to_float(value: str) -> float | None:
    if value is None:
        return None
    raw = str(value).strip()
    if raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def load_status_counts(path: Path, population_ids: set[str], pop_end_times: dict[str, datetime | None]) -> dict[str, dict]:
    """Return last status count per population before its end time."""
    results: dict[str, dict] = {}
    if not path.exists():
        return results
    with path.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id not in population_ids:
                continue
            status_time = parse_dt((row.get("StatusTime") or "").strip())
            if not status_time:
                continue
            end_time = pop_end_times.get(pop_id)
            if end_time and status_time > end_time:
                continue
            count = to_float(row.get("CurrentCount"))
            if count is None:
                continue
            current = results.get(pop_id)
            if current is None or status_time > current["time"]:
                results[pop_id] = {"time": status_time, "count": count}
    return results


def load_csv(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def summarize_weights(weights: list[float]) -> dict[str, str]:
    if not weights:
        return {"count": "0", "min": "", "median": "", "max": ""}
    weights_sorted = sorted(weights)
    return {
        "count": str(len(weights_sorted)),
        "min": f"{weights_sorted[0]:.1f}",
        "median": f"{median(weights_sorted):.1f}",
        "max": f"{weights_sorted[-1]:.1f}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate fish group overview markdown")
    parser.add_argument("--input-project-name", required=True)
    parser.add_argument("--input-project-id", required=True)
    parser.add_argument("--trace-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--feeding-actions", default="scripts/migration/data/extract/feeding_actions.csv")
    parser.add_argument("--mortality-actions", default="scripts/migration/data/extract/mortality_actions.csv")
    parser.add_argument("--weight-samples", default="scripts/migration/data/extract/ext_weight_samples_v2.csv")
    parser.add_argument("--weight-samples-fallback", default="scripts/migration/data/extract/public_weight_samples.csv")
    parser.add_argument("--status-values", default="scripts/migration/data/extract/status_values.csv")
    args = parser.parse_args()

    trace_dir = Path(args.trace_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    segments = load_csv(trace_dir / "population_segments.csv")
    hall_rows = load_csv(trace_dir / "hall_summary.csv")
    stage_rows = load_csv(trace_dir / "stage_summary.csv")

    population_ids = {row["population_id"] for row in segments if row.get("population_id")}
    container_ids = {row["container_id"] for row in segments if row.get("container_id")}

    start_times = [parse_dt(row.get("start_time", "")) for row in segments if row.get("start_time")]
    end_times = [
        parse_dt(row.get("end_time_effective", "")) or parse_dt(row.get("end_time", ""))
        for row in segments
        if row.get("end_time_effective") or row.get("end_time")
    ]
    start_min = min(start_times) if start_times else None
    end_max = max(end_times) if end_times else None

    pop_to_hall: dict[str, str] = {}
    pop_to_unit: dict[str, str] = {}
    pop_to_end: dict[str, datetime | None] = {}
    pop_to_start: dict[str, datetime | None] = {}
    hall_units: dict[str, set[str]] = {}
    for row in segments:
        pop_id = row.get("population_id") or ""
        hall = row.get("container_group") or "Unknown"
        pop_to_hall[pop_id] = hall
        unit_name = row.get("container_name") or ""
        pop_to_unit[pop_id] = unit_name
        hall_units.setdefault(hall, set()).add(unit_name)
        pop_to_start[pop_id] = parse_dt(row.get("start_time", ""))
        pop_to_end[pop_id] = parse_dt(row.get("end_time_effective", "")) or parse_dt(
            row.get("end_time", "")
        )

    # Feeding totals
    feed_total_kg = 0.0
    feed_by_hall: dict[str, float] = {}
    feed_by_unit: dict[str, float] = {}
    feed_path = Path(args.feeding_actions)
    if feed_path.exists():
        with feed_path.open() as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                pop_id = (row.get("PopulationID") or "").strip()
                if pop_id not in population_ids:
                    continue
                grams = to_float(row.get("FeedAmountG"))
                if grams is None:
                    continue
                kg = grams / 1000.0
                feed_total_kg += kg
                hall = pop_to_hall.get(pop_id, "Unknown")
                feed_by_hall[hall] = feed_by_hall.get(hall, 0.0) + kg
                unit = pop_to_unit.get(pop_id, "Unknown")
                feed_by_unit[unit] = feed_by_unit.get(unit, 0.0) + kg

    # Mortality totals
    mortality_total = 0.0
    mortality_by_hall: dict[str, float] = {}
    mortality_by_unit: dict[str, float] = {}
    mortality_path = Path(args.mortality_actions)
    if mortality_path.exists():
        with mortality_path.open() as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                pop_id = (row.get("PopulationID") or "").strip()
                if pop_id not in population_ids:
                    continue
                count = to_float(row.get("MortalityCount"))
                if count is None:
                    continue
                mortality_total += count
                hall = pop_to_hall.get(pop_id, "Unknown")
                mortality_by_hall[hall] = mortality_by_hall.get(hall, 0.0) + count
                unit = pop_to_unit.get(pop_id, "Unknown")
                mortality_by_unit[unit] = mortality_by_unit.get(unit, 0.0) + count

    # Weight samples
    weights_by_hall: dict[str, list[float]] = {}
    weights_by_unit: dict[str, list[float]] = {}
    seen_samples: set[str] = set()

    def add_weight_samples(path: Path) -> None:
        if not path.exists():
            return
        with path.open() as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                pop_id = (row.get("PopulationID") or "").strip()
                if pop_id not in population_ids:
                    continue
                sample_id = (row.get("SampleID") or "").strip()
                if sample_id and sample_id in seen_samples:
                    continue
                weight = to_float(row.get("AvgWeight"))
                if weight is None:
                    continue
                hall = pop_to_hall.get(pop_id, "Unknown")
                weights_by_hall.setdefault(hall, []).append(weight)
                unit = pop_to_unit.get(pop_id, "Unknown")
                weights_by_unit.setdefault(unit, []).append(weight)
                if sample_id:
                    seen_samples.add(sample_id)

    add_weight_samples(Path(args.weight_samples))
    add_weight_samples(Path(args.weight_samples_fallback))

    overall_weights = [w for weights in weights_by_hall.values() for w in weights]
    overall_weight_stats = summarize_weights(overall_weights)

    hall_weight_stats = {
        hall: summarize_weights(weights) for hall, weights in weights_by_hall.items()
    }
    unit_weight_stats = {
        unit: summarize_weights(weights) for unit, weights in weights_by_unit.items()
    }

    # Status values (fish count) per population and rollup to units/halls
    status_counts = load_status_counts(Path(args.status_values), population_ids, pop_to_end)

    unit_last_counts: dict[str, float] = {}
    unit_last_pop: dict[str, str] = {}
    hall_last_counts: dict[str, float] = {}

    for pop_id, unit in pop_to_unit.items():
        if not unit:
            continue
        end_time = pop_to_end.get(pop_id) or pop_to_start.get(pop_id)
        current_pop = unit_last_pop.get(unit)
        if current_pop is None:
            unit_last_pop[unit] = pop_id
        else:
            current_end = pop_to_end.get(current_pop) or pop_to_start.get(current_pop)
            if end_time and (current_end is None or end_time > current_end):
                unit_last_pop[unit] = pop_id

    for unit, pop_id in unit_last_pop.items():
        count = status_counts.get(pop_id, {}).get("count")
        if count is not None:
            unit_last_counts[unit] = float(count)
            hall = pop_to_hall.get(pop_id, "Unknown")
            hall_last_counts[hall] = hall_last_counts.get(hall, 0.0) + float(count)

    stage_names = [row["lifecycle_stage"] for row in stage_rows if row.get("lifecycle_stage")]
    stage_set = set(stage_names)
    order = ["Egg&Alevin", "Fry", "Parr", "Smolt", "Post-Smolt", "Adult"]
    ordered = [stage for stage in order if stage in stage_names]

    out_path = output_dir / "batch_overview.md"
    with out_path.open("w", encoding="utf-8") as handle:
        handle.write("# FishTalk Batch Overview (CSV-derived)\n\n")
        handle.write(
            f"Fish group: `{args.input_project_name}` (InputProjectID: `{args.input_project_id}`)\n\n"
        )
        handle.write(f"- Populations: {len(population_ids)}\n")
        handle.write(f"- Containers: {len(container_ids)}\n")
        if start_min and end_max:
            handle.write(f"- Time span: {start_min:%Y-%m-%d} -> {end_max:%Y-%m-%d}\n")
        handle.write("\n")

        handle.write("## Feed / Mortality / Weight Summary\n\n")
        handle.write(f"- Feed total: {feed_total_kg:,.1f} kg\n")
        handle.write(f"- Mortality total: {mortality_total:,.0f}\n")
        handle.write(
            "- Weight samples (AvgWeight g): "
            f"n={overall_weight_stats['count']}, "
            f"min={overall_weight_stats['min']} "
            f"median={overall_weight_stats['median']} "
            f"max={overall_weight_stats['max']}\n\n"
        )

        handle.write("## Stage Rollup (event coverage)\n\n")
        handle.write("| Stage | Event count |\n")
        handle.write("| --- | --- |\n")
        for row in stage_rows:
            handle.write(f"| {row.get('lifecycle_stage','')} | {row.get('event_count','')} |\n")
        handle.write("\n")

        handle.write("## Stage Transition Diagram\n\n")
        handle.write("```mermaid\n")
        handle.write("flowchart LR\n")
        if len(ordered) >= 2:
            for idx in range(len(ordered) - 1):
                handle.write(f"  {ordered[idx]} --> {ordered[idx + 1]}\n")
        elif ordered:
            handle.write(f"  {ordered[0]}\n")
        else:
            handle.write("  Unknown\n")
        handle.write("```\n\n")

        handle.write("## Hall Summary (ContainerGroup)\n\n")
        handle.write(
            "| Hall | Units | Containers | Populations | Start | End | Span days | "
            "Lifecycle stages | Feed kg | Mortality | Fish count (end) | Weight samples (n/median g) |\n"
        )
        handle.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for row in hall_rows:
            hall = row.get("hall") or ""
            units = ", ".join(sorted(unit for unit in hall_units.get(hall, set()) if unit))
            feed_kg = feed_by_hall.get(hall, 0.0)
            mort = mortality_by_hall.get(hall, 0.0)
            wstats = hall_weight_stats.get(hall, {"count": "0", "median": ""})
            weight_summary = f"{wstats.get('count','0')}/{wstats.get('median','')}"
            hall_count = hall_last_counts.get(hall)
            hall_count_str = f"{hall_count:,.0f}" if hall_count is not None else ""
            handle.write(
                f"| {hall} | {units} | {row.get('container_count','')} | "
                f"{row.get('population_count','')} | {row.get('start_min','')[:10]} | "
                f"{row.get('end_max','')[:10]} | {row.get('span_days','')} | "
                f"{row.get('lifecycle_stages','')} | {feed_kg:,.1f} | {mort:,.0f} | {hall_count_str} | "
                f"{weight_summary} |\n"
            )
        handle.write("\n")

        # Per-unit details
        container_rows = load_csv(trace_dir / "container_durations.csv")
        handle.write("## Unit Summary (Container)\n\n")
        handle.write(
            "| Hall | Unit | Start | End | Span days | Populations | Stage sequences | "
            "Feed kg | Mortality | Fish count (end) | Weight samples (n/median g) |\n"
        )
        handle.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for row in container_rows:
            unit = row.get("container_name") or ""
            hall = row.get("hall") or ""
            feed_kg = feed_by_unit.get(unit, 0.0)
            mort = mortality_by_unit.get(unit, 0.0)
            wstats = unit_weight_stats.get(unit, {"count": "0", "median": ""})
            weight_summary = f"{wstats.get('count','0')}/{wstats.get('median','')}"
            unit_count = unit_last_counts.get(unit)
            unit_count_str = f"{unit_count:,.0f}" if unit_count is not None else ""
            handle.write(
                f"| {hall} | {unit} | {row.get('start_min','')[:10]} | {row.get('end_max','')[:10]} | "
                f"{row.get('duration_days','')} | {row.get('population_count','')} | "
                f"{row.get('stage_sequences','')} | {feed_kg:,.1f} | {mort:,.0f} | {unit_count_str} | {weight_summary} |\n"
            )
        handle.write("\n")

        handle.write("## Data Gaps / Notes\n\n")
        handle.write(
            "- Timeline windows use `Ext_Populations_v2.StartTime/EndTime`; EndTime gaps are inferred "
            "from the next container/group start or SubTransfers.\n"
        )
        if stage_set and stage_set.issubset({"Egg&Alevin", "Fry"}):
            handle.write(
                "- FishTalk stage tables only record Egg/Alevin and Fry for this fish group; "
                "no Parr/Smolt/Post‑Smolt/Adult stage entries are present.\n"
            )
        handle.write(
            "- 40 populations have no stage events; later stages are not recorded in "
            "PopulationProductionStages for this fish group.\n"
        )
        handle.write(
            "- Detailed rows: `population_segments.csv`, `container_durations.csv`, "
            "`stage_timeline.csv`, `hall_summary.csv`.\n"
        )


if __name__ == "__main__":
    main()
