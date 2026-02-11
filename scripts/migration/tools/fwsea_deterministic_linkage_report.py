#!/usr/bin/env python3
"""Deterministic FW->Sea linkage evidence report from bulk extract CSVs.

This is migration tooling only. It does not alter migration policy or runtime behavior.

Required extract inputs:
- internal_delivery.csv
- internal_delivery_operations.csv
- internal_delivery_actions.csv
- internal_delivery_action_metadata.csv (ActionMetaData params 184/220)
- population_links.csv
- sub_transfers.csv
- populations.csv
- grouped_organisation.csv
- contacts.csv
- contact_types.csv
- transport_carriers.csv
- ext_transporters.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CSV_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"


def normalize(value: str | None) -> str:
    return (value or "").strip()


def load_csv_rows(path: Path, *, required: bool = True) -> list[dict[str, str]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required CSV file: {path}")
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_component_scope(
    *,
    report_dir: Path | None,
    component_key: str | None,
    component_id: str | None,
) -> dict | None:
    if report_dir is None:
        return None
    members_path = report_dir / "population_members.csv"
    rows = load_csv_rows(members_path, required=True)

    wanted_key = normalize(component_key)
    wanted_id = normalize(component_id)
    if not wanted_key and not wanted_id:
        keys = {normalize(row.get("component_key")) for row in rows if normalize(row.get("component_key"))}
        ids = {normalize(row.get("component_id")) for row in rows if normalize(row.get("component_id"))}
        if len(keys) == 1:
            wanted_key = next(iter(keys))
        elif len(ids) == 1:
            wanted_id = next(iter(ids))
        else:
            raise ValueError(
                "Provide --component-key or --component-id when report has multiple components."
            )

    population_ids: set[str] = set()
    resolved_key = wanted_key or None
    resolved_id = wanted_id or None
    for row in rows:
        row_key = normalize(row.get("component_key"))
        row_id = normalize(row.get("component_id"))
        if wanted_key and row_key != wanted_key:
            continue
        if wanted_id and row_id != wanted_id:
            continue
        population_id = normalize(row.get("population_id"))
        if population_id:
            population_ids.add(population_id)
        if resolved_key is None and row_key:
            resolved_key = row_key
        if resolved_id is None and row_id:
            resolved_id = row_id

    if not population_ids:
        raise ValueError(
            f"No population members found for component_key={wanted_key!r} component_id={wanted_id!r}"
        )

    return {
        "component_key": resolved_key or "",
        "component_id": resolved_id or "",
        "population_ids": population_ids,
    }


def classify_prod_stage(value: str) -> str:
    upper = normalize(value).upper()
    if "MARINE" in upper:
        return "marine"
    if "HATCHERY" in upper or "FRESH" in upper or "FW" in upper:
        return "fw"
    return "unknown"


def parse_param_string_xml(raw_xml: str) -> dict[str, str]:
    text = normalize(raw_xml)
    if not text:
        return {"parseable": "0", "trip_id": "", "compartment": "", "carrier": ""}

    parseable = "0"
    trip_id = ""
    compartment = ""
    carrier = ""

    # Regex fallback is robust for lightly malformed XML fragments.
    for pattern, field_name in (
        (r"<TripID>\s*([^<]+?)\s*</TripID>", "trip_id"),
        (r"<CompartmentID>\s*([^<]+?)\s*</CompartmentID>", "compartment"),
        (r"<CompartmentNr>\s*([^<]+?)\s*</CompartmentNr>", "compartment"),
        (r"<TransporterID>\s*([^<]+?)\s*</TransporterID>", "carrier"),
        (r"<CarrierID>\s*([^<]+?)\s*</CarrierID>", "carrier"),
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        value = normalize(match.group(1))
        if field_name == "trip_id" and not trip_id:
            trip_id = value
        elif field_name == "compartment" and not compartment:
            compartment = value
        elif field_name == "carrier" and not carrier:
            carrier = value

    try:
        ET.fromstring(text)
        parseable = "1"
    except ET.ParseError:
        parseable = "0"

    return {
        "parseable": parseable,
        "trip_id": trip_id,
        "compartment": compartment,
        "carrier": carrier,
    }


def build_markdown(summary: dict) -> str:
    lines: list[str] = []
    lines.append("# FWSEA Deterministic Linkage Tooling Report")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(f"- CSV directory: `{summary['csv_dir']}`")
    lines.append(f"- InternalDelivery rows: {summary['internal_delivery']['row_count']}")
    lines.append(f"- SalesOperationIDs: {summary['internal_delivery']['sales_operation_count']}")
    lines.append(f"- InputOperationIDs (non-null): {summary['internal_delivery']['input_operation_non_null_count']}")
    lines.append(
        f"- InputOperationIDs matched in operations extract: "
        f"{summary['internal_delivery']['input_operation_matched_count']}/"
        f"{summary['internal_delivery']['input_operation_non_null_count']}"
    )
    component_scope = summary.get("component_scope")
    if component_scope:
        lines.append(
            f"- Component scope: `{component_scope.get('component_key')}` "
            f"(id `{component_scope.get('component_id') or 'n/a'}`), "
            f"{component_scope.get('population_count', 0)} populations"
        )
    else:
        lines.append("- Component scope: none (global InternalDelivery view)")

    lines.append("")
    lines.append("## Stage-Class Pairing (InternalDelivery rows)")
    lines.append("")
    lines.append("| sales/input stage class | rows |")
    lines.append("| --- | ---: |")
    for key, count in sorted(
        (summary["internal_delivery"].get("stage_pair_counts") or {}).items(),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"| {key} | {count} |")

    lines.append("")
    lines.append("## ActionMetaData Parameters (InternalDelivery ops)")
    lines.append("")
    p184 = summary["metadata"].get("parameter_184") or {}
    p220 = summary["metadata"].get("parameter_220") or {}
    lines.append(
        f"- Parameter 184 rows: {p184.get('row_count', 0)} "
        f"(parseable XML: {p184.get('parseable_xml_rows', 0)}, trip_id rows: {p184.get('trip_id_rows', 0)})"
    )
    lines.append(
        f"- Parameter 184 compartment fields: {p184.get('compartment_rows', 0)}, "
        f"carrier/transporter fields: {p184.get('carrier_rows', 0)}"
    )
    lines.append(
        f"- Parameter 220 rows: {p220.get('row_count', 0)} "
        f"(distinct GUIDs: {p220.get('distinct_guid_count', 0)})"
    )
    lines.append(
        f"- Parameter 220 GUID->Contact matches: {p220.get('guid_contact_match_count', 0)} "
        f"(unmatched GUIDs: {p220.get('guid_unmatched_count', 0)})"
    )
    lines.append(
        f"- Parameter 220 GUID->TransportCarrier matches: {p220.get('guid_transport_carrier_match_count', 0)}"
    )
    lines.append(
        f"- Parameter 220 GUID->Ext_Transporters matches: {p220.get('guid_ext_transporter_match_count', 0)}"
    )

    top_contact_hits = p220.get("top_contact_hits") or []
    if top_contact_hits:
        lines.append("")
        lines.append("| Top parameter-220 contact hits | rows | contact types |")
        lines.append("| --- | ---: | --- |")
        for row in top_contact_hits:
            lines.append(
                f"| {row.get('contact_name') or row.get('contact_id') or '-'} "
                f"(`{row.get('contact_id') or '-'}`) | {row.get('row_count', 0)} | "
                f"{', '.join(row.get('contact_type_ids') or []) or '-'} |"
            )

    lines.append("")
    lines.append("## Operation Overlap Diagnostics")
    lines.append("")
    overlap = summary.get("operation_overlap") or {}
    lines.append("| overlap metric | count |")
    lines.append("| --- | ---: |")
    lines.append(f"| SalesOperationID present in SubTransfers | {overlap.get('sales_in_sub_transfers', 0)} |")
    lines.append(f"| InputOperationID present in SubTransfers | {overlap.get('input_in_sub_transfers', 0)} |")
    lines.append(f"| SalesOperationID present in PopulationLink | {overlap.get('sales_in_population_link', 0)} |")
    lines.append(f"| InputOperationID present in PopulationLink | {overlap.get('input_in_population_link', 0)} |")

    if component_scope:
        comp = summary.get("component_scope") or {}
        lines.append("")
        lines.append("## Component Scope Diagnostics")
        lines.append("")
        lines.append(f"- InternalDelivery rows touching component populations: {comp.get('row_touch_count', 0)}")
        lines.append(f"- Sales operations touching component populations: {comp.get('sales_operation_touch_count', 0)}")
        lines.append(f"- Input operations touching component populations: {comp.get('input_operation_touch_count', 0)}")

    lines.append("")
    lines.append("## Deterministic Conclusion")
    lines.append("")
    lines.append(
        "- Tooling evidence supports operation-level FW->Sea context in InternalDelivery/ActionMetaData. "
        "This report does not make or apply migration-policy/runtime linkage changes."
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic FWSEA linkage evidence from extract CSVs"
    )
    parser.add_argument(
        "--csv-dir",
        default=str(DEFAULT_CSV_DIR),
        help="CSV extract directory (default: scripts/migration/data/extract)",
    )
    parser.add_argument("--output", required=True, help="Output markdown path")
    parser.add_argument("--summary-json", help="Optional JSON summary output path")
    parser.add_argument(
        "--report-dir",
        help="Optional component report directory containing population_members.csv",
    )
    parser.add_argument("--component-key", help="Optional component key for --report-dir scope")
    parser.add_argument("--component-id", help="Optional component id for --report-dir scope")
    parser.add_argument("--max-contact-examples", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_dir = Path(args.csv_dir)

    internal_delivery_rows = load_csv_rows(csv_dir / "internal_delivery.csv")
    operation_rows = load_csv_rows(csv_dir / "internal_delivery_operations.csv")
    action_rows = load_csv_rows(csv_dir / "internal_delivery_actions.csv")
    metadata_rows = load_csv_rows(csv_dir / "internal_delivery_action_metadata.csv")
    population_link_rows = load_csv_rows(csv_dir / "population_links.csv")
    sub_transfer_rows = load_csv_rows(csv_dir / "sub_transfers.csv")
    population_rows = load_csv_rows(csv_dir / "populations.csv")
    grouped_rows = load_csv_rows(csv_dir / "grouped_organisation.csv")
    contact_rows = load_csv_rows(csv_dir / "contacts.csv")
    contact_type_rows = load_csv_rows(csv_dir / "contact_types.csv")
    transport_carrier_rows = load_csv_rows(csv_dir / "transport_carriers.csv")
    ext_transporter_rows = load_csv_rows(csv_dir / "ext_transporters.csv")

    component_scope_data = load_component_scope(
        report_dir=Path(args.report_dir) if args.report_dir else None,
        component_key=args.component_key,
        component_id=args.component_id,
    )
    component_population_ids = (
        set(component_scope_data["population_ids"]) if component_scope_data else set()
    )

    operation_id_set = {
        normalize(row.get("OperationID")) for row in operation_rows if normalize(row.get("OperationID"))
    }
    sales_operation_ids: set[str] = set()
    input_operation_ids: set[str] = set()

    op_population_ids: defaultdict[str, set[str]] = defaultdict(set)
    for row in action_rows:
        op_id = normalize(row.get("OperationID"))
        pop_id = normalize(row.get("PopulationID"))
        if op_id and pop_id:
            op_population_ids[op_id].add(pop_id)

    population_container_id: dict[str, str] = {}
    for row in population_rows:
        pop_id = normalize(row.get("PopulationID"))
        container_id = normalize(row.get("ContainerID"))
        if pop_id:
            population_container_id[pop_id] = container_id

    grouped_by_container: dict[str, dict[str, str]] = {}
    for row in grouped_rows:
        container_id = normalize(row.get("ContainerID"))
        if container_id and container_id not in grouped_by_container:
            grouped_by_container[container_id] = row

    op_stage_class: dict[str, str] = {}

    def classify_operation(op_id: str) -> str:
        if op_id in op_stage_class:
            return op_stage_class[op_id]
        classes: set[str] = set()
        for pop_id in op_population_ids.get(op_id, set()):
            container_id = population_container_id.get(pop_id, "")
            grouped = grouped_by_container.get(container_id) or {}
            classes.add(classify_prod_stage(normalize(grouped.get("ProdStage"))))
        if "marine" in classes:
            op_stage_class[op_id] = "marine"
        elif "fw" in classes:
            op_stage_class[op_id] = "fw"
        else:
            op_stage_class[op_id] = "unknown"
        return op_stage_class[op_id]

    stage_pair_counts: Counter[str] = Counter()
    input_op_non_null_count = 0
    input_op_matched_count = 0

    component_row_touch_count = 0
    component_sales_touch_ops: set[str] = set()
    component_input_touch_ops: set[str] = set()

    for row in internal_delivery_rows:
        sales_op = normalize(row.get("SalesOperationID"))
        input_op = normalize(row.get("InputOperationID"))
        if sales_op:
            sales_operation_ids.add(sales_op)
        if input_op:
            input_operation_ids.add(input_op)
            input_op_non_null_count += 1
            if input_op in operation_id_set:
                input_op_matched_count += 1

        sales_class = classify_operation(sales_op) if sales_op else "unknown"
        input_class = classify_operation(input_op) if input_op else "unknown"
        stage_pair_counts[f"sales={sales_class}, input={input_class}"] += 1

        if component_population_ids:
            sales_pops = op_population_ids.get(sales_op, set())
            input_pops = op_population_ids.get(input_op, set())
            sales_touch = bool(sales_pops & component_population_ids)
            input_touch = bool(input_pops & component_population_ids)
            if sales_touch or input_touch:
                component_row_touch_count += 1
            if sales_touch and sales_op:
                component_sales_touch_ops.add(sales_op)
            if input_touch and input_op:
                component_input_touch_ops.add(input_op)

    sub_transfer_ops = {
        normalize(row.get("OperationID")) for row in sub_transfer_rows if normalize(row.get("OperationID"))
    }
    population_link_ops = {
        normalize(row.get("OperationID")) for row in population_link_rows if normalize(row.get("OperationID"))
    }
    operation_overlap = {
        "sales_in_sub_transfers": len(sales_operation_ids & sub_transfer_ops),
        "input_in_sub_transfers": len(input_operation_ids & sub_transfer_ops),
        "sales_in_population_link": len(sales_operation_ids & population_link_ops),
        "input_in_population_link": len(input_operation_ids & population_link_ops),
    }

    param184_rows = [row for row in metadata_rows if normalize(row.get("ParameterID")) == "184"]
    param220_rows = [row for row in metadata_rows if normalize(row.get("ParameterID")) == "220"]

    parseable_xml_rows = 0
    trip_id_rows = 0
    compartment_rows = 0
    carrier_rows = 0
    for row in param184_rows:
        # Prefer SQL-parsed fields when present (avoids sqlcmd text truncation issues).
        sql_parseable = normalize(row.get("XmlParseable"))
        trip_id = normalize(row.get("TripID"))
        compartment = normalize(row.get("CompartmentID")) or normalize(row.get("CompartmentNr"))
        carrier = normalize(row.get("TransporterID")) or normalize(row.get("CarrierID"))

        if not (sql_parseable or trip_id or compartment or carrier):
            fallback = parse_param_string_xml(normalize(row.get("ParameterString")))
            sql_parseable = fallback["parseable"]
            trip_id = trip_id or fallback["trip_id"]
            compartment = compartment or fallback["compartment"]
            carrier = carrier or fallback["carrier"]

        if sql_parseable == "1":
            parseable_xml_rows += 1
        if trip_id:
            trip_id_rows += 1
        if compartment:
            compartment_rows += 1
        if carrier:
            carrier_rows += 1

    contact_by_id = {
        normalize(row.get("ContactID")): row for row in contact_rows if normalize(row.get("ContactID"))
    }
    contact_types_by_id: defaultdict[str, set[str]] = defaultdict(set)
    for row in contact_type_rows:
        contact_id = normalize(row.get("ContactID"))
        type_id = normalize(row.get("ContactTypeID"))
        if contact_id and type_id:
            contact_types_by_id[contact_id].add(type_id)

    carrier_ids = {
        normalize(row.get("TransportCarrierID"))
        for row in transport_carrier_rows
        if normalize(row.get("TransportCarrierID"))
    }
    ext_transporter_ids = {
        normalize(row.get("TransporterID")) for row in ext_transporter_rows if normalize(row.get("TransporterID"))
    }

    param220_guids = [normalize(row.get("ParameterGuid")) for row in param220_rows if normalize(row.get("ParameterGuid"))]
    distinct_param220_guids = set(param220_guids)
    guid_contact_matches = {guid for guid in distinct_param220_guids if guid in contact_by_id}
    guid_transport_carrier_matches = {guid for guid in distinct_param220_guids if guid in carrier_ids}
    guid_ext_transporter_matches = {guid for guid in distinct_param220_guids if guid in ext_transporter_ids}
    unmatched_guids = distinct_param220_guids - guid_contact_matches

    contact_hit_counter: Counter[str] = Counter()
    for guid in param220_guids:
        if guid in guid_contact_matches:
            contact_hit_counter[guid] += 1

    max_examples = max(args.max_contact_examples, 0)
    top_contact_hits: list[dict[str, object]] = []
    for contact_id, hit_count in contact_hit_counter.most_common(max_examples):
        contact = contact_by_id.get(contact_id) or {}
        top_contact_hits.append(
            {
                "contact_id": contact_id,
                "contact_name": normalize(contact.get("Name")),
                "row_count": hit_count,
                "contact_type_ids": sorted(contact_types_by_id.get(contact_id, set())),
            }
        )

    summary: dict[str, object] = {
        "csv_dir": str(csv_dir),
        "internal_delivery": {
            "row_count": len(internal_delivery_rows),
            "sales_operation_count": len(sales_operation_ids),
            "input_operation_non_null_count": input_op_non_null_count,
            "input_operation_matched_count": input_op_matched_count,
            "stage_pair_counts": dict(sorted(stage_pair_counts.items(), key=lambda item: (-item[1], item[0]))),
        },
        "operation_overlap": operation_overlap,
        "metadata": {
            "parameter_184": {
                "row_count": len(param184_rows),
                "parseable_xml_rows": parseable_xml_rows,
                "trip_id_rows": trip_id_rows,
                "compartment_rows": compartment_rows,
                "carrier_rows": carrier_rows,
            },
            "parameter_220": {
                "row_count": len(param220_rows),
                "distinct_guid_count": len(distinct_param220_guids),
                "guid_contact_match_count": len(guid_contact_matches),
                "guid_unmatched_count": len(unmatched_guids),
                "guid_transport_carrier_match_count": len(guid_transport_carrier_matches),
                "guid_ext_transporter_match_count": len(guid_ext_transporter_matches),
                "top_contact_hits": top_contact_hits,
                "unmatched_guid_examples": sorted(unmatched_guids)[:max_examples],
            },
        },
    }

    if component_scope_data:
        summary["component_scope"] = {
            "component_key": component_scope_data["component_key"],
            "component_id": component_scope_data["component_id"],
            "population_count": len(component_population_ids),
            "row_touch_count": component_row_touch_count,
            "sales_operation_touch_count": len(component_sales_touch_ops),
            "input_operation_touch_count": len(component_input_touch_ops),
        }

    markdown = build_markdown(summary)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Wrote report to {output_path}")

    if args.summary_json:
        summary_path = Path(args.summary_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Wrote summary JSON to {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
