#!/usr/bin/env python3
"""Build FW->Sea marine-ingress candidate matrix with auditable evidence.

Evidence ladder implemented (tooling-only):
1) Canonical first: Ext_Transfers + SubTransfers lineage signals.
2) If canonical S*->A* is absent for an FW endpoint, emit provisional
   temporal+geography candidates using FW terminal depletion X and sea fill/start Y
   in [X, X+2 days] (or [X, X+3] only with explicit justification).
3) Exclude L*->S*, FW->FW, and Marine->Marine from FW->Sea ingress inference.

This script does not alter runtime models/APIs.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CSV_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "aquamind"
    / "docs"
    / "progress"
    / "migration"
    / "analysis_reports"
    / datetime.utcnow().strftime("%Y-%m-%d")
)
DEFAULT_INPUT_BATCHES_CSV = (
    PROJECT_ROOT / "scripts" / "migration" / "output" / "input_stitching" / "input_batches.csv"
)

DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
)

SITE_CODE_RE = re.compile(r"\b([A-Za-z]+[0-9]{1,3})\b")
SEA_RING_RE = re.compile(r"^\s*([A-Za-z]?[0-9]{2})\b")
FAROE_SITEGROUPS = {"west", "north", "south"}
SEA_STAGE_TOKENS = {"adult", "post-smolt", "post smolt"}


@dataclass(frozen=True)
class PopContext:
    population_id: str
    container_id: str
    population_name: str
    start_time: datetime | None
    end_time: datetime | None
    site: str
    site_group: str
    prod_stage: str
    container_group: str
    geography: str
    site_code: str
    stage_class: str
    component: str


@dataclass
class CanonicalPairMetrics:
    ext_transfer_rows: int = 0
    transferred_count_sum: float = 0.0
    transferred_biomass_sum_kg: float = 0.0


@dataclass
class LineageMetrics:
    subtransfer_rows: int = 0
    operation_time_min: datetime | None = None
    operation_time_max: datetime | None = None

    def update(self, operation_time: datetime | None) -> None:
        self.subtransfer_rows += 1
        if operation_time is None:
            return
        if self.operation_time_min is None or operation_time < self.operation_time_min:
            self.operation_time_min = operation_time
        if self.operation_time_max is None or operation_time > self.operation_time_max:
            self.operation_time_max = operation_time


@dataclass(frozen=True)
class EndpointSignal:
    timestamp: datetime | None
    primary_signal: str
    signal_count: int
    signals: dict[str, str]


@dataclass(frozen=True)
class InputBatchMeta:
    batch_key: str
    earliest_start: datetime | None
    latest_activity: datetime | None
    aquamind_stages: tuple[str, ...]
    geographies: tuple[str, ...]
    is_valid: bool


def normalize(value: str | None) -> str:
    return (value or "").strip()


def parse_dt(value: str | None) -> datetime | None:
    raw = normalize(value)
    if not raw:
        return None
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def dt_to_str(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat(sep=" ")


def parse_float(value: str | None) -> float:
    raw = normalize(value)
    if not raw:
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def parse_bool(value: str | None) -> bool:
    return normalize(value).lower() in {"1", "true", "yes", "y"}


def parse_multi_tokens(value: str | None) -> tuple[str, ...]:
    raw = normalize(value)
    if not raw:
        return tuple()
    tokens = [normalize(token) for token in raw.split(",")]
    cleaned = sorted({token for token in tokens if token})
    return tuple(cleaned)


def has_sea_stage(meta: InputBatchMeta) -> bool:
    for stage in meta.aquamind_stages:
        stage_norm = normalize(stage).lower()
        if stage_norm in SEA_STAGE_TOKENS:
            return True
    return False


def subtract_months(value: date, months: int) -> date:
    if months <= 0:
        return value
    year = value.year
    month = value.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def floor_months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def parse_site_code(site_name: str) -> str:
    match = SITE_CODE_RE.search(normalize(site_name))
    return match.group(1).upper() if match else ""


def infer_sea_ring(population_name: str) -> str:
    match = SEA_RING_RE.search(normalize(population_name))
    return match.group(1).upper() if match else ""


def derive_geography(site_group: str, site_name: str) -> str:
    site_group_norm = normalize(site_group).lower()
    if site_group_norm in FAROE_SITEGROUPS:
        return "Faroe Islands"
    if site_group_norm:
        return "Scotland"

    site_code = parse_site_code(site_name)
    if site_code.startswith("FW"):
        return "Scotland"
    if site_code.startswith(("S", "A", "L")):
        return "Faroe Islands"
    return "Unknown"


def classify_prod_stage(prod_stage: str) -> str:
    upper = normalize(prod_stage).upper()
    if not upper:
        return "unknown"
    if "MARINE" in upper or upper == "SEA":
        return "marine"
    if "HATCHERY" in upper or "FRESH" in upper or "SMOLT" in upper:
        return "fw"
    return "unknown"


def iter_csv_rows(path: Path) -> Any:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def load_input_batch_meta(path: Path) -> dict[str, InputBatchMeta]:
    if not path.exists():
        return {}
    batch_meta: dict[str, InputBatchMeta] = {}
    for row in iter_csv_rows(path):
        batch_key = normalize(row.get("batch_key"))
        if not batch_key:
            continue
        batch_meta[batch_key] = InputBatchMeta(
            batch_key=batch_key,
            earliest_start=parse_dt(row.get("earliest_start")),
            latest_activity=parse_dt(row.get("latest_activity")),
            aquamind_stages=parse_multi_tokens(row.get("aquamind_stages")),
            geographies=parse_multi_tokens(row.get("geographies")),
            is_valid=parse_bool(row.get("is_valid")),
        )
    return batch_meta


def load_population_contexts(csv_dir: Path) -> dict[str, PopContext]:
    populations_path = csv_dir / "populations.csv"
    grouped_path = csv_dir / "grouped_organisation.csv"
    ext_pop_path = csv_dir / "ext_populations.csv"
    ext_inputs_path = csv_dir / "ext_inputs.csv"

    if not populations_path.exists():
        raise FileNotFoundError(f"Missing required CSV: {populations_path}")
    if not grouped_path.exists():
        raise FileNotFoundError(f"Missing required CSV: {grouped_path}")

    population_base: dict[str, dict[str, Any]] = {}
    for row in iter_csv_rows(populations_path):
        pop_id = normalize(row.get("PopulationID"))
        if not pop_id:
            continue
        population_base[pop_id] = {
            "container_id": normalize(row.get("ContainerID")),
            "start_time": parse_dt(row.get("StartTime")),
            "end_time": parse_dt(row.get("EndTime")),
        }

    population_names: dict[str, str] = {}
    if ext_pop_path.exists():
        for row in iter_csv_rows(ext_pop_path):
            pop_id = normalize(row.get("PopulationID"))
            if pop_id and pop_id in population_base:
                population_names[pop_id] = normalize(row.get("PopulationName"))

    grouped_by_container: dict[str, dict[str, str]] = {}
    for row in iter_csv_rows(grouped_path):
        container_id = normalize(row.get("ContainerID"))
        if container_id and container_id not in grouped_by_container:
            grouped_by_container[container_id] = row

    batch_keys_by_population: defaultdict[str, set[str]] = defaultdict(set)
    if ext_inputs_path.exists():
        for row in iter_csv_rows(ext_inputs_path):
            pop_id = normalize(row.get("PopulationID"))
            if not pop_id:
                continue
            input_name = normalize(row.get("InputName"))
            input_number = normalize(row.get("InputNumber"))
            year_class = normalize(row.get("YearClass"))
            if input_name and input_number and year_class:
                batch_keys_by_population[pop_id].add(
                    f"{input_name}|{input_number}|{year_class}"
                )

    contexts: dict[str, PopContext] = {}
    for pop_id, base in population_base.items():
        container_id = base["container_id"]
        grouped = grouped_by_container.get(container_id, {})
        site = normalize(grouped.get("Site"))
        site_group = normalize(grouped.get("SiteGroup"))
        prod_stage = normalize(grouped.get("ProdStage"))
        container_group = normalize(grouped.get("ContainerGroup"))
        geography = derive_geography(site_group, site)
        site_code = parse_site_code(site)
        stage_class = classify_prod_stage(prod_stage)
        component_keys = sorted(batch_keys_by_population.get(pop_id) or [])
        component = component_keys[0] if component_keys else ""

        contexts[pop_id] = PopContext(
            population_id=pop_id,
            container_id=container_id,
            population_name=population_names.get(pop_id, ""),
            start_time=base["start_time"],
            end_time=base["end_time"],
            site=site,
            site_group=site_group,
            prod_stage=prod_stage,
            container_group=container_group,
            geography=geography,
            site_code=site_code,
            stage_class=stage_class,
            component=component,
        )
    return contexts


def load_canonical_pairs(
    csv_dir: Path,
    contexts: dict[str, PopContext],
) -> tuple[dict[tuple[str, str], CanonicalPairMetrics], Counter[str]]:
    ext_transfers_path = csv_dir / "ext_transfers.csv"
    if not ext_transfers_path.exists():
        raise FileNotFoundError(f"Missing required CSV: {ext_transfers_path}")

    canonical_pairs: dict[tuple[str, str], CanonicalPairMetrics] = {}
    flow_counter: Counter[str] = Counter()

    for row in iter_csv_rows(ext_transfers_path):
        src = normalize(row.get("SourcePop"))
        dst = normalize(row.get("DestPop"))
        if not src or not dst:
            continue
        src_ctx = contexts.get(src)
        dst_ctx = contexts.get(dst)
        if src_ctx is None or dst_ctx is None:
            flow_counter["missing_context"] += 1
            continue

        # Keep only FW-sourced rows for FW->Sea ingress matrix.
        if src_ctx.stage_class != "fw":
            flow_counter["excluded_non_fw_source"] += 1
            continue

        key = (src, dst)
        metrics = canonical_pairs.setdefault(key, CanonicalPairMetrics())
        metrics.ext_transfer_rows += 1
        metrics.transferred_count_sum += parse_float(row.get("TransferredCount"))
        metrics.transferred_biomass_sum_kg += parse_float(row.get("TransferredBiomassKg"))

        if src_ctx.site_code.startswith("L") and dst_ctx.site_code.startswith("S"):
            flow_counter["l_to_s"] += 1
        if src_ctx.stage_class == "fw" and dst_ctx.stage_class == "fw":
            flow_counter["fw_to_fw"] += 1
        if src_ctx.stage_class == "marine" and dst_ctx.stage_class == "marine":
            flow_counter["marine_to_marine"] += 1
    return canonical_pairs, flow_counter


def scan_subtransfer_signals(
    csv_dir: Path,
    contexts: dict[str, PopContext],
    fw_population_ids: set[str],
    sea_population_ids: set[str],
    canonical_pair_keys: set[tuple[str, str]],
) -> tuple[
    dict[tuple[str, str], LineageMetrics],
    dict[str, datetime],
    dict[str, datetime],
]:
    path = csv_dir / "sub_transfers.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing required CSV: {path}")

    pair_lineage: dict[tuple[str, str], LineageMetrics] = {}
    fw_transfer_out_last: dict[str, datetime] = {}
    sea_transfer_in_first: dict[str, datetime] = {}

    for row in iter_csv_rows(path):
        src_before = normalize(row.get("SourcePopBefore"))
        dst_before = normalize(row.get("DestPopBefore"))
        dst_after = normalize(row.get("DestPopAfter"))
        operation_time = parse_dt(row.get("OperationTime"))

        if src_before and dst_after and (src_before, dst_after) in canonical_pair_keys:
            metrics = pair_lineage.setdefault((src_before, dst_after), LineageMetrics())
            metrics.update(operation_time)

        if operation_time is not None:
            if src_before in fw_population_ids:
                current = fw_transfer_out_last.get(src_before)
                if current is None or operation_time > current:
                    fw_transfer_out_last[src_before] = operation_time
            if dst_before in fw_population_ids:
                current = fw_transfer_out_last.get(dst_before)
                if current is None or operation_time > current:
                    fw_transfer_out_last[dst_before] = operation_time

            if dst_after in sea_population_ids:
                src_ctx = contexts.get(src_before)
                if src_ctx and src_ctx.stage_class == "fw":
                    current = sea_transfer_in_first.get(dst_after)
                    if current is None or operation_time < current:
                        sea_transfer_in_first[dst_after] = operation_time

    return pair_lineage, fw_transfer_out_last, sea_transfer_in_first


def scan_event_last_times(
    path: Path,
    *,
    population_field: str,
    time_field: str,
    population_filter: set[str],
) -> dict[str, datetime]:
    if not path.exists():
        return {}

    last_times: dict[str, datetime] = {}
    for row in iter_csv_rows(path):
        pop_id = normalize(row.get(population_field))
        if not pop_id or pop_id not in population_filter:
            continue
        ts = parse_dt(row.get(time_field))
        if ts is None:
            continue
        current = last_times.get(pop_id)
        if current is None or ts > current:
            last_times[pop_id] = ts
    return last_times


def scan_status_signals(
    path: Path,
    *,
    population_filter: set[str],
) -> tuple[dict[str, datetime], dict[str, datetime]]:
    if not path.exists():
        return {}, {}

    min_nonzero: dict[str, datetime] = {}
    max_zero: dict[str, datetime] = {}

    for row in iter_csv_rows(path):
        pop_id = normalize(row.get("PopulationID"))
        if not pop_id or pop_id not in population_filter:
            continue
        ts = parse_dt(row.get("StatusTime"))
        if ts is None:
            continue
        count = parse_float(row.get("CurrentCount"))
        biomass = parse_float(row.get("CurrentBiomassKg"))
        nonzero = (count > 0.0) or (biomass > 0.0)
        if nonzero:
            existing = min_nonzero.get(pop_id)
            if existing is None or ts < existing:
                min_nonzero[pop_id] = ts
        else:
            existing = max_zero.get(pop_id)
            if existing is None or ts > existing:
                max_zero[pop_id] = ts
    return min_nonzero, max_zero


def build_fw_terminal_signal(
    *,
    context: PopContext,
    transfer_out_last: datetime | None,
    culling_last: datetime | None,
    mortality_last: datetime | None,
    status_zero_after_nonzero: datetime | None,
) -> EndpointSignal:
    signal_times: dict[str, datetime] = {}
    if context.end_time is not None:
        signal_times["segment_end_time"] = context.end_time
    if transfer_out_last is not None:
        signal_times["transfer_out_last_time"] = transfer_out_last
    if culling_last is not None:
        signal_times["culling_last_time"] = culling_last
    if mortality_last is not None:
        signal_times["mortality_last_time"] = mortality_last
    if status_zero_after_nonzero is not None:
        signal_times["status_zero_after_nonzero_time"] = status_zero_after_nonzero

    if not signal_times:
        return EndpointSignal(
            timestamp=None,
            primary_signal="",
            signal_count=0,
            signals={},
        )

    x_ts = max(signal_times.values())
    primary_keys = sorted(
        key for key, value in signal_times.items() if value == x_ts
    )
    return EndpointSignal(
        timestamp=x_ts,
        primary_signal="|".join(primary_keys),
        signal_count=len(signal_times),
        signals={key: dt_to_str(value) for key, value in sorted(signal_times.items())},
    )


def build_sea_fill_signal(
    *,
    context: PopContext,
    status_first_nonzero: datetime | None,
    transfer_in_first: datetime | None,
) -> EndpointSignal:
    signal_times: dict[str, datetime] = {}
    if context.start_time is not None:
        signal_times["segment_start_time"] = context.start_time
    if status_first_nonzero is not None:
        signal_times["status_first_nonzero_time"] = status_first_nonzero
    if transfer_in_first is not None:
        signal_times["fw_transfer_in_first_time"] = transfer_in_first

    if not signal_times:
        return EndpointSignal(
            timestamp=None,
            primary_signal="",
            signal_count=0,
            signals={},
        )

    y_ts = min(signal_times.values())
    primary_keys = sorted(
        key for key, value in signal_times.items() if value == y_ts
    )
    return EndpointSignal(
        timestamp=y_ts,
        primary_signal="|".join(primary_keys),
        signal_count=len(signal_times),
        signals={key: dt_to_str(value) for key, value in sorted(signal_times.items())},
    )


def format_delta_days(x_ts: datetime | None, y_ts: datetime | None) -> str:
    if x_ts is None or y_ts is None:
        return ""
    delta = (y_ts - x_ts).total_seconds() / 86400.0
    return f"{delta:.3f}"


def is_s_to_a_boundary(src_code: str, dst_code: str) -> bool:
    return src_code.startswith("S") and dst_code.startswith("A")


def classify_canonical(
    *,
    src_ctx: PopContext,
    dst_ctx: PopContext,
    boundary: bool,
    same_geography: bool,
    lineage_rows: int,
) -> str:
    if src_ctx.stage_class == "fw" and dst_ctx.stage_class == "fw":
        return "reverse_flow_fw_only"
    if boundary and src_ctx.stage_class == "fw" and dst_ctx.stage_class == "marine":
        if same_geography and lineage_rows > 0:
            return "true_candidate"
        return "sparse_evidence"
    return "unclassified_nonzero_candidate"


def classify_provisional(
    *,
    delta_days: float,
    fw_signal_count: int,
    sea_signal_count: int,
) -> str:
    if delta_days <= 1.0 and fw_signal_count >= 2 and sea_signal_count >= 2:
        return "true_candidate"
    if delta_days <= 2.0 and fw_signal_count >= 1 and sea_signal_count >= 1:
        return "sparse_evidence"
    return "unclassified_nonzero_candidate"


def build_row(
    *,
    geography: str,
    fw_ctx: PopContext,
    sea_ctx: PopContext,
    fw_signal: EndpointSignal,
    sea_signal: EndpointSignal,
    evidence_type: str,
    boundary: bool,
    classification: str,
    canonical_metrics: CanonicalPairMetrics | None = None,
    lineage_metrics: LineageMetrics | None = None,
    same_geography: bool,
    temporal_window_days: int | None = None,
    temporal_window_justification: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "geography": geography,
        "fw_site": fw_ctx.site,
        "fw_hall": fw_ctx.container_group,
        "fw_container_id": fw_ctx.container_id,
        "fw_population_id": fw_ctx.population_id,
        "fw_component": fw_ctx.component,
        "sea_area": sea_ctx.site,
        "sea_ring": infer_sea_ring(sea_ctx.population_name),
        "sea_container_id": sea_ctx.container_id,
        "sea_population_id": sea_ctx.population_id,
        "sea_component": sea_ctx.component,
        "x_fw_terminal_depletion": dt_to_str(fw_signal.timestamp),
        "y_sea_fill_start": dt_to_str(sea_signal.timestamp),
        "delta_days": format_delta_days(fw_signal.timestamp, sea_signal.timestamp),
        "evidence_type": evidence_type,
        "boundary_check_s_to_a": str(boundary).lower(),
        "classification": classification,
        "source_stage_class": fw_ctx.stage_class,
        "dest_stage_class": sea_ctx.stage_class,
        "source_site_code": fw_ctx.site_code,
        "dest_site_code": sea_ctx.site_code,
        "same_geography": str(same_geography).lower(),
        "fw_terminal_primary_signal": fw_signal.primary_signal,
        "fw_terminal_signal_count": fw_signal.signal_count,
        "fw_terminal_evidence": json.dumps(fw_signal.signals, sort_keys=True),
        "sea_fill_primary_signal": sea_signal.primary_signal,
        "sea_fill_signal_count": sea_signal.signal_count,
        "sea_fill_evidence": json.dumps(sea_signal.signals, sort_keys=True),
        "canonical_ext_transfer_rows": 0,
        "canonical_transferred_count_sum": "",
        "canonical_transferred_biomass_kg_sum": "",
        "lineage_subtransfer_rows": 0,
        "lineage_operation_time_min": "",
        "lineage_operation_time_max": "",
        "temporal_window_days": temporal_window_days or "",
        "temporal_window_justification": temporal_window_justification or "",
    }

    if canonical_metrics is not None:
        row["canonical_ext_transfer_rows"] = canonical_metrics.ext_transfer_rows
        row["canonical_transferred_count_sum"] = (
            f"{canonical_metrics.transferred_count_sum:.3f}"
        )
        row["canonical_transferred_biomass_kg_sum"] = (
            f"{canonical_metrics.transferred_biomass_sum_kg:.3f}"
        )

    if lineage_metrics is not None:
        row["lineage_subtransfer_rows"] = lineage_metrics.subtransfer_rows
        row["lineage_operation_time_min"] = dt_to_str(lineage_metrics.operation_time_min)
        row["lineage_operation_time_max"] = dt_to_str(lineage_metrics.operation_time_max)

    return row


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_markdown(
    *,
    csv_path: Path,
    summary: dict[str, Any],
    top_rows: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# FW->Sea Marine Ingress Candidate Matrix")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(f"- Source CSV dir: `{summary['csv_dir']}`")
    lines.append(f"- Candidate matrix CSV: `{csv_path}`")
    lines.append(f"- Provisional temporal window days: `{summary['provisional_window_days']}`")
    if summary.get("window_extension_justification"):
        lines.append(
            f"- +3-day extension justification: `{summary['window_extension_justification']}`"
        )
    lines.append("")
    lines.append("## Topline")
    lines.append("")
    lines.append(f"- Total rows: `{summary['row_count']}`")
    lines.append(f"- Canonical rows: `{summary['canonical_row_count']}`")
    lines.append(f"- Provisional rows: `{summary['provisional_row_count']}`")
    lines.append(
        f"- Boundary S*->A* true rows: `{summary['boundary_true_row_count']}`"
    )
    lines.append("")
    lines.append("## Classification Counts")
    lines.append("")
    for key, value in sorted(
        (summary.get("classification_counts") or {}).items(),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("## Evidence-Type Counts")
    lines.append("")
    for key, value in sorted(
        (summary.get("evidence_type_counts") or {}).items(),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"- `{key}`: {value}")
    tier_summary = summary.get("marine_linkage_age_tier") or {}
    if tier_summary:
        lines.append("")
        lines.append("## Marine Age-Aware Tier Gate")
        lines.append("")
        lines.append(
            f"- Age gate: `<{tier_summary.get('fw_age_gate_months', '')} months` "
            f"from cutoff `{tier_summary.get('backup_cutoff_date', '')}` "
            f"(window start `{tier_summary.get('fw_age_gate_window_start_date', '')}`)"
        )
        lines.append(
            f"- Sea cohorts under age gate: `{tier_summary.get('sea_under_age_gate_count', 0)}`"
        )
        for key, value in sorted(
            (tier_summary.get("tier_counts") or {}).items(),
            key=lambda item: (-item[1], item[0]),
        ):
            lines.append(f"- Tier `{key}`: {value}")
    lines.append("")
    lines.append("## Explicitly Excluded Flow Families")
    lines.append("")
    excluded = summary.get("excluded_flow_counts") or {}
    lines.append(f"- `L* -> S*`: {excluded.get('l_to_s', 0)}")
    lines.append(f"- `FW -> FW`: {excluded.get('fw_to_fw', 0)}")
    lines.append(f"- `Marine -> Marine`: {excluded.get('marine_to_marine', 0)}")
    lines.append("")
    lines.append("## Top Candidate Rows")
    lines.append("")
    lines.append(
        "| evidence | class | geography | fw population | sea population | delta_days | boundary | fw component | sea component |"
    )
    lines.append(
        "| --- | --- | --- | --- | --- | ---: | --- | --- | --- |"
    )
    for row in top_rows:
        lines.append(
            f"| {row['evidence_type']} | {row['classification']} | {row['geography']} | "
            f"{row['fw_population_id']} | {row['sea_population_id']} | "
            f"{row['delta_days'] or 'n/a'} | {row['boundary_check_s_to_a']} | "
            f"{row['fw_component'] or '-'} | {row['sea_component'] or '-'} |"
        )
    lines.append("")
    lines.append("## Pilot Recommendation")
    lines.append("")
    pilot = summary.get("pilot_recommendation") or {}
    if pilot:
        lines.append(
            f"- Recommended evidence: `{pilot.get('evidence_type', '')}` "
            f"class=`{pilot.get('classification', '')}`"
        )
        lines.append(
            f"- FW endpoint: `{pilot.get('fw_population_id', '')}` "
            f"(component `{pilot.get('fw_component', '') or '-'}`)"
        )
        lines.append(
            f"- Sea endpoint: `{pilot.get('sea_population_id', '')}` "
            f"(component `{pilot.get('sea_component', '') or '-'}`)"
        )
        lines.append(f"- Delta days: `{pilot.get('delta_days', 'n/a')}`")
    else:
        lines.append("- No pilot-eligible row found with non-empty FW+Sea component keys.")
    lines.append("")
    lines.append("## Guardrail Note")
    lines.append("")
    lines.append(
        "- Provisional rows are migration-tooling evidence only and not runtime truth."
    )
    return "\n".join(lines) + "\n"


def build_marine_linkage_tier_rows(
    *,
    matrix_rows: list[dict[str, Any]],
    input_batch_meta: dict[str, InputBatchMeta],
    backup_cutoff_date: date,
    fw_age_gate_months: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    window_start_date = subtract_months(backup_cutoff_date, fw_age_gate_months)
    credible_classes = {"true_candidate", "sparse_evidence"}

    linkage_by_sea: defaultdict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in matrix_rows:
        if normalize(row.get("boundary_check_s_to_a")) != "true":
            continue
        if normalize(row.get("classification")) not in credible_classes:
            continue
        sea_component = normalize(row.get("sea_component"))
        fw_component = normalize(row.get("fw_component"))
        if not sea_component or not fw_component:
            continue

        sea_links = linkage_by_sea[sea_component]
        fw_link = sea_links.setdefault(
            fw_component,
            {
                "row_count": 0,
                "classification_counts": Counter(),
                "evidence_type_counts": Counter(),
                "delta_days_min": None,
                "delta_days_max": None,
                "sample_fw_population_id": normalize(row.get("fw_population_id")),
                "sample_sea_population_id": normalize(row.get("sea_population_id")),
            },
        )
        fw_link["row_count"] += 1
        fw_link["classification_counts"][normalize(row.get("classification"))] += 1
        fw_link["evidence_type_counts"][normalize(row.get("evidence_type"))] += 1

        delta_raw = normalize(row.get("delta_days"))
        if delta_raw:
            try:
                delta = float(delta_raw)
            except ValueError:
                delta = None
            if delta is not None:
                if fw_link["delta_days_min"] is None or delta < fw_link["delta_days_min"]:
                    fw_link["delta_days_min"] = delta
                if fw_link["delta_days_max"] is None or delta > fw_link["delta_days_max"]:
                    fw_link["delta_days_max"] = delta

    sea_under_age_gate: list[str] = []
    sea_out_of_age_gate: list[str] = []
    for batch_key, meta in input_batch_meta.items():
        if meta.earliest_start is None:
            continue
        if not has_sea_stage(meta):
            continue
        if meta.earliest_start.date() >= window_start_date:
            sea_under_age_gate.append(batch_key)
        else:
            sea_out_of_age_gate.append(batch_key)

    tier_rows: list[dict[str, Any]] = []
    tier_counts: Counter[str] = Counter()
    recommended_action_counts: Counter[str] = Counter()
    linked_fw_in_scope_component_set: set[str] = set()
    linked_fw_out_scope_component_set: set[str] = set()
    linked_fw_unknown_scope_component_set: set[str] = set()

    for sea_component in sorted(sea_under_age_gate):
        sea_meta = input_batch_meta.get(sea_component)
        if sea_meta is None or sea_meta.earliest_start is None:
            continue

        linked_fw_map = linkage_by_sea.get(sea_component) or {}
        linked_fw_components = sorted(linked_fw_map.keys())
        fw_in_scope: list[str] = []
        fw_out_of_scope: list[str] = []
        fw_unknown_scope: list[str] = []
        evidence_counts: Counter[str] = Counter()
        classification_counts: Counter[str] = Counter()
        linkage_row_count = 0
        delta_min: float | None = None
        delta_max: float | None = None

        for fw_component, link_payload in linked_fw_map.items():
            linkage_row_count += int(link_payload.get("row_count") or 0)
            evidence_counts.update(link_payload.get("evidence_type_counts") or {})
            classification_counts.update(link_payload.get("classification_counts") or {})

            local_delta_min = link_payload.get("delta_days_min")
            local_delta_max = link_payload.get("delta_days_max")
            if isinstance(local_delta_min, float):
                if delta_min is None or local_delta_min < delta_min:
                    delta_min = local_delta_min
            if isinstance(local_delta_max, float):
                if delta_max is None or local_delta_max > delta_max:
                    delta_max = local_delta_max

            fw_meta = input_batch_meta.get(fw_component)
            if fw_meta is None or fw_meta.earliest_start is None:
                fw_unknown_scope.append(fw_component)
                linked_fw_unknown_scope_component_set.add(fw_component)
                continue
            if fw_meta.earliest_start.date() >= window_start_date:
                fw_in_scope.append(fw_component)
                linked_fw_in_scope_component_set.add(fw_component)
            else:
                fw_out_of_scope.append(fw_component)
                linked_fw_out_scope_component_set.add(fw_component)

        if fw_in_scope:
            tier = "linked_fw_in_scope"
            action = "eligible_for_marine_wave"
        elif linked_fw_components:
            tier = "linked_fw_out_of_scope"
            action = "requires_fw_scope_exception_or_targeted_backfill"
        else:
            tier = "unlinked_sea"
            action = "hold_for_linkage_confirmation"

        tier_counts[tier] += 1
        recommended_action_counts[action] += 1

        age_days = (backup_cutoff_date - sea_meta.earliest_start.date()).days
        age_months_floor = floor_months_between(
            sea_meta.earliest_start.date(), backup_cutoff_date
        )

        tier_rows.append(
            {
                "sea_component": sea_component,
                "sea_earliest_start": dt_to_str(sea_meta.earliest_start),
                "sea_latest_activity": dt_to_str(sea_meta.latest_activity),
                "sea_aquamind_stages": ", ".join(sea_meta.aquamind_stages),
                "sea_geographies": ", ".join(sea_meta.geographies),
                "sea_age_days_at_cutoff": age_days,
                "sea_age_months_floor_at_cutoff": age_months_floor,
                "sea_under_age_gate": "true",
                "linked_fw_component_count": len(linked_fw_components),
                "linked_fw_in_scope_count": len(fw_in_scope),
                "linked_fw_out_of_scope_count": len(fw_out_of_scope),
                "linked_fw_unknown_scope_count": len(fw_unknown_scope),
                "linked_fw_in_scope_examples": "; ".join(fw_in_scope[:10]),
                "linked_fw_out_of_scope_examples": "; ".join(fw_out_of_scope[:10]),
                "linked_fw_unknown_scope_examples": "; ".join(fw_unknown_scope[:10]),
                "linkage_row_count": linkage_row_count,
                "linkage_delta_days_min": (
                    f"{delta_min:.3f}" if isinstance(delta_min, float) else ""
                ),
                "linkage_delta_days_max": (
                    f"{delta_max:.3f}" if isinstance(delta_max, float) else ""
                ),
                "linkage_evidence_type_counts": json.dumps(
                    dict(sorted(evidence_counts.items())),
                    sort_keys=True,
                ),
                "linkage_classification_counts": json.dumps(
                    dict(sorted(classification_counts.items())),
                    sort_keys=True,
                ),
                "linkage_tier": tier,
                "recommended_action": action,
            }
        )

    tier_rows.sort(
        key=lambda row: (
            0
            if row["linkage_tier"] == "linked_fw_in_scope"
            else 1
            if row["linkage_tier"] == "linked_fw_out_of_scope"
            else 2,
            row["sea_component"],
        )
    )

    summary = {
        "backup_cutoff_date": str(backup_cutoff_date),
        "fw_age_gate_months": fw_age_gate_months,
        "fw_age_gate_window_start_date": str(window_start_date),
        "sea_total_with_stage_signal": len(sea_under_age_gate) + len(sea_out_of_age_gate),
        "sea_under_age_gate_count": len(sea_under_age_gate),
        "sea_out_of_age_gate_count": len(sea_out_of_age_gate),
        "tier_counts": dict(
            sorted(tier_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "recommended_action_counts": dict(
            sorted(recommended_action_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "linked_fw_in_scope_component_count": len(linked_fw_in_scope_component_set),
        "linked_fw_out_of_scope_component_count": len(linked_fw_out_scope_component_set),
        "linked_fw_unknown_scope_component_count": len(
            linked_fw_unknown_scope_component_set
        ),
    }
    return tier_rows, summary


def build_marine_linkage_tier_markdown(
    *,
    tier_csv_path: Path,
    tier_rows: list[dict[str, Any]],
    tier_summary: dict[str, Any],
) -> str:
    lines: list[str] = []
    lines.append("# Marine Linkage Age-Aware Tier Gate")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(
        f"- Backup cutoff date: `{tier_summary.get('backup_cutoff_date', '')}`"
    )
    lines.append(
        f"- FW age gate: `<{tier_summary.get('fw_age_gate_months', '')} months` "
        f"(window start `{tier_summary.get('fw_age_gate_window_start_date', '')}`)"
    )
    lines.append(f"- Tier CSV: `{tier_csv_path}`")
    lines.append("")
    lines.append("## Topline")
    lines.append("")
    lines.append(
        f"- Sea cohorts with sea-stage signal: `{tier_summary.get('sea_total_with_stage_signal', 0)}`"
    )
    lines.append(
        f"- Sea cohorts under age gate: `{tier_summary.get('sea_under_age_gate_count', 0)}`"
    )
    lines.append(
        f"- Sea cohorts out of age gate: `{tier_summary.get('sea_out_of_age_gate_count', 0)}`"
    )
    lines.append("")
    lines.append("## Tier Counts")
    lines.append("")
    for key, value in sorted(
        (tier_summary.get("tier_counts") or {}).items(),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("## Recommended Action Counts")
    lines.append("")
    for key, value in sorted(
        (tier_summary.get("recommended_action_counts") or {}).items(),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append(
        "| tier | sea component | age months (floor) | linked FW in-scope | linked FW out-of-scope | linked FW unknown | action |"
    )
    lines.append(
        "| --- | --- | ---: | ---: | ---: | ---: | --- |"
    )
    for row in tier_rows[:100]:
        lines.append(
            f"| {row['linkage_tier']} | {row['sea_component']} | "
            f"{row['sea_age_months_floor_at_cutoff']} | "
            f"{row['linked_fw_in_scope_count']} | "
            f"{row['linked_fw_out_of_scope_count']} | "
            f"{row['linked_fw_unknown_scope_count']} | "
            f"{row['recommended_action']} |"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build FW->Sea marine ingress candidate matrix (canonical + provisional)"
    )
    parser.add_argument(
        "--csv-dir",
        default=str(DEFAULT_CSV_DIR),
        help="FishTalk extract CSV directory",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for matrix artifacts",
    )
    parser.add_argument(
        "--output-prefix",
        default=f"fwsea_marine_ingress_candidate_matrix_{datetime.utcnow().strftime('%Y-%m-%d')}",
        help="Artifact filename prefix",
    )
    parser.add_argument(
        "--provisional-window-days",
        type=int,
        default=2,
        choices=(2, 3),
        help="Temporal window for provisional candidates (default: 2; 3 requires justification)",
    )
    parser.add_argument(
        "--window-extension-justification",
        default="",
        help="Required when --provisional-window-days=3",
    )
    parser.add_argument(
        "--max-provisional-per-fw-endpoint",
        type=int,
        default=0,
        help="Optional cap per FW endpoint (0 = no cap)",
    )
    parser.add_argument(
        "--top-candidate-limit",
        type=int,
        default=30,
        help="Rows to include in markdown top-candidate table",
    )
    parser.add_argument(
        "--input-batches-csv",
        default=str(DEFAULT_INPUT_BATCHES_CSV),
        help="Input stitching batch metadata CSV (for age-aware marine tier partitioning)",
    )
    parser.add_argument(
        "--backup-cutoff-date",
        default="2026-01-22",
        help="Backup cutoff date (YYYY-MM-DD) used for age gate",
    )
    parser.add_argument(
        "--fw-age-gate-months",
        type=int,
        default=30,
        help="FW age gate in months for marine tier partitioning (default: 30)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.provisional_window_days == 3 and not normalize(
        args.window_extension_justification
    ):
        raise SystemExit(
            "--window-extension-justification is required when --provisional-window-days=3"
        )
    if args.fw_age_gate_months <= 0:
        raise SystemExit("--fw-age-gate-months must be > 0")

    backup_cutoff_dt = parse_dt(args.backup_cutoff_date)
    if backup_cutoff_dt is None:
        raise SystemExit(
            f"Invalid --backup-cutoff-date '{args.backup_cutoff_date}'. Use YYYY-MM-DD."
        )
    backup_cutoff_date = backup_cutoff_dt.date()

    csv_dir = Path(args.csv_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("[1/8] Loading population context...")
    contexts = load_population_contexts(csv_dir)
    fw_population_ids = {
        pop_id for pop_id, ctx in contexts.items() if ctx.stage_class == "fw"
    }
    sea_population_ids = {
        pop_id for pop_id, ctx in contexts.items() if ctx.stage_class == "marine"
    }
    print(
        f"      contexts={len(contexts)} fw={len(fw_population_ids)} sea={len(sea_population_ids)}"
    )

    print("[2/8] Loading canonical Ext_Transfers pairs...")
    canonical_pairs, excluded_flow_counter = load_canonical_pairs(csv_dir, contexts)
    print(f"      canonical_pairs={len(canonical_pairs)}")

    print("[3/8] Scanning SubTransfers lineage + transfer signals...")
    pair_lineage, fw_transfer_out_last, sea_transfer_in_first = scan_subtransfer_signals(
        csv_dir,
        contexts,
        fw_population_ids,
        sea_population_ids,
        set(canonical_pairs.keys()),
    )
    print(
        "      lineage_pairs="
        f"{len(pair_lineage)} fw_transfer_out={len(fw_transfer_out_last)} sea_transfer_in={len(sea_transfer_in_first)}"
    )

    print("[4/8] Scanning culling/mortality closure signals...")
    fw_culling_last = scan_event_last_times(
        csv_dir / "culling.csv",
        population_field="PopulationID",
        time_field="OperationStartTime",
        population_filter=fw_population_ids,
    )
    fw_mortality_last = scan_event_last_times(
        csv_dir / "mortality_actions.csv",
        population_field="PopulationID",
        time_field="OperationStartTime",
        population_filter=fw_population_ids,
    )
    print(
        f"      culling_signals={len(fw_culling_last)} mortality_signals={len(fw_mortality_last)}"
    )

    print("[5/8] Scanning status depletion/fill signals...")
    status_nonzero_min, status_zero_max = scan_status_signals(
        csv_dir / "status_values.csv",
        population_filter=fw_population_ids | sea_population_ids,
    )
    fw_status_zero_after_nonzero: dict[str, datetime] = {}
    for pop_id in fw_population_ids:
        first_nonzero = status_nonzero_min.get(pop_id)
        last_zero = status_zero_max.get(pop_id)
        if first_nonzero is None or last_zero is None:
            continue
        if last_zero >= first_nonzero:
            fw_status_zero_after_nonzero[pop_id] = last_zero
    sea_status_first_nonzero = {
        pop_id: status_nonzero_min[pop_id]
        for pop_id in sea_population_ids
        if pop_id in status_nonzero_min
    }
    print(
        "      fw_status_zero_after_nonzero="
        f"{len(fw_status_zero_after_nonzero)} sea_status_first_nonzero={len(sea_status_first_nonzero)}"
    )

    print("[6/8] Building endpoint X/Y signals...")
    fw_terminal_signals: dict[str, EndpointSignal] = {}
    for pop_id in fw_population_ids:
        ctx = contexts[pop_id]
        fw_terminal_signals[pop_id] = build_fw_terminal_signal(
            context=ctx,
            transfer_out_last=fw_transfer_out_last.get(pop_id),
            culling_last=fw_culling_last.get(pop_id),
            mortality_last=fw_mortality_last.get(pop_id),
            status_zero_after_nonzero=fw_status_zero_after_nonzero.get(pop_id),
        )

    sea_fill_signals: dict[str, EndpointSignal] = {}
    for pop_id in sea_population_ids:
        ctx = contexts[pop_id]
        sea_fill_signals[pop_id] = build_sea_fill_signal(
            context=ctx,
            status_first_nonzero=sea_status_first_nonzero.get(pop_id),
            transfer_in_first=sea_transfer_in_first.get(pop_id),
        )

    print("[7/8] Constructing canonical + provisional matrix rows...")
    rows: list[dict[str, Any]] = []
    canonical_fw_boundary_sources: set[str] = set()

    for (src, dst), canonical_metrics in canonical_pairs.items():
        src_ctx = contexts.get(src)
        dst_ctx = contexts.get(dst)
        if src_ctx is None or dst_ctx is None:
            continue
        fw_signal = fw_terminal_signals.get(src) or EndpointSignal(None, "", 0, {})
        sea_signal = sea_fill_signals.get(dst) or EndpointSignal(None, "", 0, {})
        boundary = is_s_to_a_boundary(src_ctx.site_code, dst_ctx.site_code)
        same_geography = (
            src_ctx.geography != "Unknown"
            and dst_ctx.geography != "Unknown"
            and src_ctx.geography == dst_ctx.geography
        )
        lineage_metrics = pair_lineage.get((src, dst)) or LineageMetrics()
        classification = classify_canonical(
            src_ctx=src_ctx,
            dst_ctx=dst_ctx,
            boundary=boundary,
            same_geography=same_geography,
            lineage_rows=lineage_metrics.subtransfer_rows,
        )
        if boundary and classification in {"true_candidate", "sparse_evidence"}:
            canonical_fw_boundary_sources.add(src)

        rows.append(
            build_row(
                geography=src_ctx.geography or dst_ctx.geography,
                fw_ctx=src_ctx,
                sea_ctx=dst_ctx,
                fw_signal=fw_signal,
                sea_signal=sea_signal,
                evidence_type="canonical",
                boundary=boundary,
                classification=classification,
                canonical_metrics=canonical_metrics,
                lineage_metrics=lineage_metrics,
                same_geography=same_geography,
            )
        )

    sea_by_geo_day: defaultdict[str, defaultdict[date, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for pop_id in sea_population_ids:
        sea_ctx = contexts[pop_id]
        if not sea_ctx.site_code.startswith("A"):
            continue
        if not normalize(sea_ctx.component):
            continue
        y_signal = sea_fill_signals.get(pop_id)
        if y_signal is None or y_signal.timestamp is None:
            continue
        if sea_ctx.geography == "Unknown":
            continue
        sea_by_geo_day[sea_ctx.geography][y_signal.timestamp.date()].append(pop_id)

    max_per_fw = max(args.max_provisional_per_fw_endpoint, 0)
    for pop_id in sorted(fw_population_ids):
        fw_ctx = contexts[pop_id]
        if not fw_ctx.site_code.startswith("S"):
            continue
        if not normalize(fw_ctx.component):
            continue
        if pop_id in canonical_fw_boundary_sources:
            continue
        fw_signal = fw_terminal_signals.get(pop_id)
        if fw_signal is None or fw_signal.timestamp is None:
            continue
        if fw_ctx.geography == "Unknown":
            continue

        selected_for_fw = 0
        x_ts = fw_signal.timestamp
        for day_offset in range(0, args.provisional_window_days + 1):
            candidate_day = (x_ts + timedelta(days=day_offset)).date()
            for sea_pop_id in sea_by_geo_day[fw_ctx.geography].get(candidate_day, []):
                sea_ctx = contexts[sea_pop_id]
                sea_signal = sea_fill_signals.get(sea_pop_id)
                if sea_signal is None or sea_signal.timestamp is None:
                    continue
                y_ts = sea_signal.timestamp
                delta_days = (y_ts - x_ts).total_seconds() / 86400.0
                if delta_days < 0 or delta_days > float(args.provisional_window_days):
                    continue

                classification = classify_provisional(
                    delta_days=delta_days,
                    fw_signal_count=fw_signal.signal_count,
                    sea_signal_count=sea_signal.signal_count,
                )
                rows.append(
                    build_row(
                        geography=fw_ctx.geography,
                        fw_ctx=fw_ctx,
                        sea_ctx=sea_ctx,
                        fw_signal=fw_signal,
                        sea_signal=sea_signal,
                        evidence_type="provisional_temporal_geography",
                        boundary=True,
                        classification=classification,
                        same_geography=True,
                        temporal_window_days=args.provisional_window_days,
                        temporal_window_justification=normalize(
                            args.window_extension_justification
                        ),
                    )
                )
                selected_for_fw += 1
                if max_per_fw > 0 and selected_for_fw >= max_per_fw:
                    break
            if max_per_fw > 0 and selected_for_fw >= max_per_fw:
                break

    def evidence_rank(value: str) -> int:
        if value == "canonical":
            return 0
        if value == "provisional_temporal_geography":
            return 1
        return 9

    def row_delta(row: dict[str, Any]) -> float:
        try:
            return abs(float(row.get("delta_days") or 9999))
        except ValueError:
            return 9999.0

    class_rank_map = {
        "true_candidate": 0,
        "sparse_evidence": 1,
        "reverse_flow_fw_only": 2,
        "unclassified_nonzero_candidate": 3,
    }

    rows.sort(
        key=lambda row: (
            class_rank_map.get(row["classification"], 9),
            evidence_rank(row["evidence_type"]),
            row_delta(row),
            row["fw_population_id"],
            row["sea_population_id"],
        )
    )

    classification_counts = Counter(row["classification"] for row in rows)
    evidence_type_counts = Counter(row["evidence_type"] for row in rows)
    boundary_true_row_count = sum(
        1 for row in rows if row["boundary_check_s_to_a"] == "true"
    )
    canonical_row_count = evidence_type_counts.get("canonical", 0)
    provisional_row_count = evidence_type_counts.get(
        "provisional_temporal_geography", 0
    )

    pilot_candidates = [
        row
        for row in rows
        if row["classification"] == "true_candidate"
        and row["boundary_check_s_to_a"] == "true"
        and normalize(row.get("fw_component"))
        and normalize(row.get("sea_component"))
    ]
    pilot_recommendation = pilot_candidates[0] if pilot_candidates else {}

    input_batch_meta = load_input_batch_meta(Path(args.input_batches_csv))
    tier_rows, tier_summary = build_marine_linkage_tier_rows(
        matrix_rows=rows,
        input_batch_meta=input_batch_meta,
        backup_cutoff_date=backup_cutoff_date,
        fw_age_gate_months=args.fw_age_gate_months,
    )

    summary = {
        "generated_at_utc": dt_to_str(datetime.utcnow()),
        "csv_dir": str(csv_dir),
        "input_batches_csv": str(Path(args.input_batches_csv)),
        "row_count": len(rows),
        "canonical_row_count": canonical_row_count,
        "provisional_row_count": provisional_row_count,
        "boundary_true_row_count": boundary_true_row_count,
        "classification_counts": dict(
            sorted(classification_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "evidence_type_counts": dict(
            sorted(evidence_type_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "excluded_flow_counts": {
            "l_to_s": int(excluded_flow_counter.get("l_to_s", 0)),
            "fw_to_fw": int(excluded_flow_counter.get("fw_to_fw", 0)),
            "marine_to_marine": int(excluded_flow_counter.get("marine_to_marine", 0)),
            "excluded_non_fw_source": int(
                excluded_flow_counter.get("excluded_non_fw_source", 0)
            ),
        },
        "provisional_window_days": args.provisional_window_days,
        "window_extension_justification": normalize(args.window_extension_justification),
        "pilot_recommendation": pilot_recommendation,
        "pilot_candidate_count": len(pilot_candidates),
        "marine_linkage_age_tier": tier_summary,
    }

    top_rows = rows[: max(args.top_candidate_limit, 0)]
    prefix = normalize(args.output_prefix) or "fwsea_marine_ingress_candidate_matrix"
    csv_path = output_dir / f"{prefix}.csv"
    md_path = output_dir / f"{prefix}.md"
    json_path = output_dir / f"{prefix}.summary.json"
    tier_csv_path = output_dir / f"{prefix}.marine_linkage_age_tiers.csv"
    tier_md_path = output_dir / f"{prefix}.marine_linkage_age_tiers.md"
    tier_json_path = output_dir / f"{prefix}.marine_linkage_age_tiers.summary.json"

    print("[8/8] Writing artifacts...")
    write_csv(csv_path, rows)
    md_payload = build_markdown(csv_path=csv_path, summary=summary, top_rows=top_rows)
    md_path.write_text(md_payload, encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(tier_csv_path, tier_rows)
    tier_md_payload = build_marine_linkage_tier_markdown(
        tier_csv_path=tier_csv_path,
        tier_rows=tier_rows,
        tier_summary=tier_summary,
    )
    tier_md_path.write_text(tier_md_payload, encoding="utf-8")
    tier_json_path.write_text(
        json.dumps(tier_summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {tier_csv_path}")
    print(f"Wrote {tier_md_path}")
    print(f"Wrote {tier_json_path}")
    if summary["pilot_recommendation"]:
        rec = summary["pilot_recommendation"]
        print(
            "Pilot recommendation:"
            f" evidence={rec.get('evidence_type')} fw_component={rec.get('fw_component')}"
            f" sea_component={rec.get('sea_component')}"
        )
    else:
        print("Pilot recommendation: none with non-empty FW+Sea component keys.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

