#!/usr/bin/env python3
# flake8: noqa: E501,C901,E402
"""Directional FW->Sea sales parity extract (container-out vs ring-in).

Deterministic intent:
- Anchor rows on InternalDelivery operation pairs (SalesOperationID + InputOperationID).
- Compute fish-out from sales-side actions (OperationType=7, ActionType=7, ParameterID=10).
- Compute fish-in from paired input-side actions (OperationType=5, ActionType=4, ParameterID=10).
- Classify parity as exact / within_tolerance / outside_tolerance / missing-side.

This is tooling-only diagnostics and does not change migration policy.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migration.extractors.base import BaseExtractor, ExtractionContext


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "scripts" / "migration" / "output"


def normalize(value: str | None) -> str:
    return (value or "").strip()


def sql_quote(value: str) -> str:
    return value.replace("'", "''")


def to_float(raw: str | None) -> float:
    text = normalize(raw)
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def classify_prod_stage(value: str) -> str:
    upper = normalize(value).upper()
    if "MARINE" in upper:
        return "marine"
    if "HATCHERY" in upper or "FRESH" in upper or "FW" in upper:
        return "fw"
    return "unknown"


def extract_xml_tag(xml_text: str, tag: str) -> str:
    if not xml_text:
        return ""
    match = re.search(rf"<{tag}>\s*([^<]+?)\s*</{tag}>", xml_text, flags=re.IGNORECASE)
    return normalize(match.group(1)) if match else ""


def parse_transport_xml(xml_text: str) -> dict[str, str]:
    xml_clean = normalize(xml_text)
    return {
        "trip_id": extract_xml_tag(xml_clean, "TripID"),
        "compartment_id": extract_xml_tag(xml_clean, "CompartmentID"),
        "compartment_nr": extract_xml_tag(xml_clean, "CompartmentNr"),
        "carrier_id": extract_xml_tag(xml_clean, "CarrierID"),
        "transporter_id": extract_xml_tag(xml_clean, "TransporterID"),
    }


def join_values(values: set[str], *, max_items: int = 6) -> str:
    cleaned = sorted(v for v in values if normalize(v))
    if len(cleaned) <= max_items:
        return "; ".join(cleaned)
    kept = cleaned[:max_items]
    return "; ".join(kept) + f"; ... (+{len(cleaned) - max_items} more)"


def build_sales_query(
    *,
    since: str | None,
    until: str | None,
    customer_like: str | None,
    site_like: str | None,
    only_fw_sources: bool,
) -> str:
    filters: list[str] = ["so.OperationType = 7"]
    if since:
        filters.append(f"so.StartTime >= '{sql_quote(since)}'")
    if until:
        filters.append(f"so.StartTime < '{sql_quote(until)}'")
    if customer_like:
        pattern = f"%{sql_quote(customer_like)}%"
        filters.append(f"ISNULL(cn220.Name, '') LIKE '{pattern}'")
    if site_like:
        pattern = f"%{sql_quote(site_like)}%"
        filters.append(f"ISNULL(go.Site, '') LIKE '{pattern}'")
    if only_fw_sources:
        filters.append(
            "("
            "UPPER(ISNULL(go.ProdStage, '')) LIKE '%HATCHERY%' "
            "OR UPPER(ISNULL(go.ProdStage, '')) LIKE '%FRESH%' "
            "OR UPPER(ISNULL(go.ProdStage, '')) LIKE '%FW%'"
            ")"
        )
    where_sql = " AND ".join(filters) if filters else "1=1"

    return f"""
SELECT
    CONVERT(varchar(19), so.StartTime, 120) AS SalesStartTime,
    CONVERT(varchar(36), id.SalesOperationID) AS SalesOperationID,
    CONVERT(varchar(36), id.InputOperationID) AS InputOperationID,
    CONVERT(varchar(36), a.ActionID) AS SaleActionID,
    CONVERT(varchar(10), a.ActionType) AS SaleActionType,
    CONVERT(varchar(10), a.ActionOrder) AS SaleActionOrder,
    CONVERT(varchar(36), a.PopulationID) AS SalePopulationID,
    ISNULL(CONVERT(varchar(64), m1.ParameterValue), '') AS SaleParam1Value,
    ISNULL(CONVERT(varchar(64), m10.ParameterValue), '') AS SaleParam10Value,
    ISNULL(CONVERT(varchar(64), m11.ParameterValue), '') AS SaleParam11Value,
    ISNULL(REPLACE(REPLACE(REPLACE(m96.ParameterString, '|', '/'), CHAR(13), ' '), CHAR(10), ' '), '') AS RingText,
    ISNULL(REPLACE(REPLACE(REPLACE(m184.ParameterString, '|', '/'), CHAR(13), ' '), CHAR(10), ' '), '') AS SaleTransportXml,
    ISNULL(CONVERT(varchar(36), m220.ParameterGuid), '') AS CustomerGuid,
    ISNULL(cn220.Name, '') AS CustomerContactName,
    ISNULL(c.ContainerName, '') AS SourceContainerName,
    ISNULL(c.OfficialID, '') AS SourceOfficialID,
    ISNULL(go.Site, '') AS SourceSite,
    ISNULL(go.ContainerGroup, '') AS SourceContainerGroup,
    ISNULL(go.ProdStage, '') AS SourceProdStage
FROM dbo.InternalDelivery id
JOIN dbo.Operations so
  ON so.OperationID = id.SalesOperationID
JOIN dbo.Action a
  ON a.OperationID = so.OperationID
 AND a.ActionType IN (7, 25)
LEFT JOIN dbo.Populations p
  ON p.PopulationID = a.PopulationID
LEFT JOIN dbo.Containers c
  ON c.ContainerID = p.ContainerID
LEFT JOIN dbo.Ext_GroupedOrganisation_v2 go
  ON go.ContainerID = c.ContainerID
OUTER APPLY (
    SELECT TOP 1 m.ParameterValue
    FROM dbo.ActionMetaData m
    WHERE m.ActionID = a.ActionID
      AND m.ParameterID = 1
    ORDER BY m.ParameterDate DESC, m.ActionID
) m1
OUTER APPLY (
    SELECT TOP 1 m.ParameterValue
    FROM dbo.ActionMetaData m
    WHERE m.ActionID = a.ActionID
      AND m.ParameterID = 10
    ORDER BY m.ParameterDate DESC, m.ActionID
) m10
OUTER APPLY (
    SELECT TOP 1 m.ParameterValue
    FROM dbo.ActionMetaData m
    WHERE m.ActionID = a.ActionID
      AND m.ParameterID = 11
    ORDER BY m.ParameterDate DESC, m.ActionID
) m11
OUTER APPLY (
    SELECT TOP 1 m.ParameterString
    FROM dbo.ActionMetaData m
    WHERE m.ActionID = a.ActionID
      AND m.ParameterID = 96
    ORDER BY m.ParameterDate DESC, m.ActionID
) m96
OUTER APPLY (
    SELECT TOP 1 m.ParameterString
    FROM dbo.ActionMetaData m
    WHERE m.ActionID = a.ActionID
      AND m.ParameterID = 184
    ORDER BY m.ParameterDate DESC, m.ActionID
) m184
OUTER APPLY (
    SELECT TOP 1 m.ParameterGuid
    FROM dbo.ActionMetaData m
    WHERE m.ActionID = a.ActionID
      AND m.ParameterID = 220
    ORDER BY m.ParameterDate DESC, m.ActionID
) m220
LEFT JOIN dbo.Contact cn220
  ON cn220.ID = m220.ParameterGuid
WHERE {where_sql}
ORDER BY so.StartTime DESC, id.SalesOperationID, a.ActionOrder, a.ActionID
"""


def build_input_query(
    *,
    since: str | None,
    until: str | None,
    customer_like: str | None,
    site_like: str | None,
    only_fw_sources: bool,
) -> str:
    filters: list[str] = ["so.OperationType = 7", "id.InputOperationID IS NOT NULL", "sa.ActionType = 7"]
    if since:
        filters.append(f"so.StartTime >= '{sql_quote(since)}'")
    if until:
        filters.append(f"so.StartTime < '{sql_quote(until)}'")
    if customer_like:
        pattern = f"%{sql_quote(customer_like)}%"
        filters.append(f"ISNULL(cn220.Name, '') LIKE '{pattern}'")
    if site_like:
        pattern = f"%{sql_quote(site_like)}%"
        filters.append(f"ISNULL(go_src.Site, '') LIKE '{pattern}'")
    if only_fw_sources:
        filters.append(
            "("
            "UPPER(ISNULL(go_src.ProdStage, '')) LIKE '%HATCHERY%' "
            "OR UPPER(ISNULL(go_src.ProdStage, '')) LIKE '%FRESH%' "
            "OR UPPER(ISNULL(go_src.ProdStage, '')) LIKE '%FW%'"
            ")"
        )
    where_sql = " AND ".join(filters) if filters else "1=1"

    return f"""
WITH filtered_internal AS (
    SELECT DISTINCT
        CONVERT(varchar(36), id.SalesOperationID) AS SalesOperationID,
        CONVERT(varchar(36), id.InputOperationID) AS InputOperationID
    FROM dbo.InternalDelivery id
    JOIN dbo.Operations so
      ON so.OperationID = id.SalesOperationID
    JOIN dbo.Action sa
      ON sa.OperationID = so.OperationID
    LEFT JOIN dbo.Populations sp
      ON sp.PopulationID = sa.PopulationID
    LEFT JOIN dbo.Containers sc
      ON sc.ContainerID = sp.ContainerID
    LEFT JOIN dbo.Ext_GroupedOrganisation_v2 go_src
      ON go_src.ContainerID = sc.ContainerID
    OUTER APPLY (
        SELECT TOP 1 m.ParameterGuid
        FROM dbo.ActionMetaData m
        WHERE m.ActionID = sa.ActionID
          AND m.ParameterID = 220
        ORDER BY m.ParameterDate DESC, m.ActionID
    ) sm220
    LEFT JOIN dbo.Contact cn220
      ON cn220.ID = sm220.ParameterGuid
    WHERE {where_sql}
)
SELECT
    fi.SalesOperationID,
    fi.InputOperationID,
    CONVERT(varchar(19), io.StartTime, 120) AS InputStartTime,
    CONVERT(varchar(36), ia.ActionID) AS InputActionID,
    CONVERT(varchar(10), ia.ActionType) AS InputActionType,
    CONVERT(varchar(10), ia.ActionOrder) AS InputActionOrder,
    CONVERT(varchar(36), ia.PopulationID) AS InputPopulationID,
    ISNULL(CONVERT(varchar(64), im10.ParameterValue), '') AS InputParam10Value,
    ISNULL(CONVERT(varchar(64), im11.ParameterValue), '') AS InputParam11Value,
    ISNULL(REPLACE(REPLACE(REPLACE(im184.ParameterString, '|', '/'), CHAR(13), ' '), CHAR(10), ' '), '') AS InputTransportXml,
    ISNULL(ic.ContainerName, '') AS TargetContainerName,
    ISNULL(ic.OfficialID, '') AS TargetOfficialID,
    ISNULL(go_in.Site, '') AS TargetSite,
    ISNULL(go_in.ContainerGroup, '') AS TargetContainerGroup,
    ISNULL(go_in.ProdStage, '') AS TargetProdStage
FROM filtered_internal fi
JOIN dbo.Operations io
  ON io.OperationID = fi.InputOperationID
 AND io.OperationType = 5
JOIN dbo.Action ia
  ON ia.OperationID = io.OperationID
 AND ia.ActionType = 4
LEFT JOIN dbo.Populations ip
  ON ip.PopulationID = ia.PopulationID
LEFT JOIN dbo.Containers ic
  ON ic.ContainerID = ip.ContainerID
LEFT JOIN dbo.Ext_GroupedOrganisation_v2 go_in
  ON go_in.ContainerID = ic.ContainerID
OUTER APPLY (
    SELECT TOP 1 m.ParameterValue
    FROM dbo.ActionMetaData m
    WHERE m.ActionID = ia.ActionID
      AND m.ParameterID = 10
    ORDER BY m.ParameterDate DESC, m.ActionID
) im10
OUTER APPLY (
    SELECT TOP 1 m.ParameterValue
    FROM dbo.ActionMetaData m
    WHERE m.ActionID = ia.ActionID
      AND m.ParameterID = 11
    ORDER BY m.ParameterDate DESC, m.ActionID
) im11
OUTER APPLY (
    SELECT TOP 1 m.ParameterString
    FROM dbo.ActionMetaData m
    WHERE m.ActionID = ia.ActionID
      AND m.ParameterID = 184
    ORDER BY m.ParameterDate DESC, m.ActionID
) im184
ORDER BY io.StartTime DESC, fi.SalesOperationID, ia.ActionOrder, ia.ActionID
"""


def parity_band(
    *,
    sales_out_count: float,
    input_in_count: float,
    tolerance_abs: float,
    tolerance_ratio: float,
) -> str:
    if sales_out_count <= 0 and input_in_count <= 0:
        return "missing_both_counts"
    if sales_out_count <= 0:
        return "missing_sales_out"
    if input_in_count <= 0:
        return "missing_input_in"
    abs_diff = abs(input_in_count - sales_out_count)
    tolerance = max(tolerance_abs, sales_out_count * tolerance_ratio)
    if abs_diff < 0.5:
        return "exact"
    if abs_diff <= tolerance:
        return "within_tolerance"
    return "outside_tolerance"


def build_markdown(
    *,
    csv_path: Path,
    summary: dict[str, Any],
    examples: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# FWSEA Directional Sales Parity Extract")
    lines.append("")
    lines.append("## Run Summary")
    lines.append(f"- Output CSV: `{csv_path}`")
    lines.append(f"- Operation pairs: `{summary['operation_pair_count']}`")
    lines.append(f"- Pairs with sales out count > 0: `{summary['pairs_with_sales_out_count']}`")
    lines.append(f"- Pairs with input in count > 0: `{summary['pairs_with_input_in_count']}`")
    lines.append(
        f"- Tolerance: abs <= `{summary['tolerance']['count_abs']}` "
        f"or ratio <= `{summary['tolerance']['count_ratio']}`"
    )
    lines.append("")
    lines.append("## Parity Bands (Count)")
    lines.append("| band | pairs |")
    lines.append("| --- | ---: |")
    for key, value in summary["count_parity_band_counts"].items():
        lines.append(f"| {key} | {value} |")
    lines.append("")
    lines.append("## Key Metrics")
    lines.append("| metric | value |")
    lines.append("| --- | ---: |")
    lines.append(f"| exact_pairs | {summary['exact_pairs']} |")
    lines.append(f"| within_tolerance_pairs | {summary['within_tolerance_pairs']} |")
    lines.append(f"| outside_tolerance_pairs | {summary['outside_tolerance_pairs']} |")
    lines.append(f"| missing_input_in_pairs | {summary['missing_input_in_pairs']} |")
    lines.append(f"| missing_sales_out_pairs | {summary['missing_sales_out_pairs']} |")
    lines.append(f"| missing_both_count_pairs | {summary['missing_both_count_pairs']} |")
    lines.append(
        f"| directional_match_rate (exact+within over comparable) | "
        f"{summary['directional_match_rate']:.4f} |"
    )
    lines.append("")
    lines.append("## Worst Mismatches (Sample)")
    lines.append("| sales start | source site | source containers | ring text | sales out | input in | abs diff | ratio | band |")
    lines.append("| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |")
    for row in examples:
        lines.append(
            "| "
            f"{row.get('SalesStartTime', '')} | "
            f"{row.get('SourceSites', '')} | "
            f"{row.get('SourceContainers', '')} | "
            f"{row.get('RingTexts', '')} | "
            f"{row.get('SalesOutCountParam10', '')} | "
            f"{row.get('InputInCountParam10', '')} | "
            f"{row.get('CountAbsDiff', '')} | "
            f"{row.get('CountRatioInputToSales', '')} | "
            f"{row.get('CountParityBand', '')} |"
        )
    lines.append("")
    lines.append("## Deterministic Notes")
    lines.append("- Sales out count uses sales-side `ActionType=7`, `ParameterID=10` (absolute delta).")
    lines.append("- Input in count uses input-side `ActionType=4`, `ParameterID=10` (absolute delta).")
    lines.append("- Pairing anchor is `InternalDelivery(SalesOperationID, InputOperationID)`.")
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Directional FW->Sea parity extract for sales out vs ring in counts"
    )
    parser.add_argument("--sql-profile", default="fishtalk_readonly")
    parser.add_argument("--since", help="Include sales operations with StartTime >= this timestamp")
    parser.add_argument("--until", help="Include sales operations with StartTime < this timestamp")
    parser.add_argument("--customer-like", help="Optional LIKE filter on customer contact name")
    parser.add_argument("--site-like", help="Optional LIKE filter on source site name")
    parser.add_argument(
        "--only-fw-sources",
        action="store_true",
        help="Restrict to source rows with FW/Hatchery-like prod stage",
    )
    parser.add_argument(
        "--count-tolerance-abs",
        type=float,
        default=500.0,
        help="Absolute fish-count tolerance for directional parity (default: 500)",
    )
    parser.add_argument(
        "--count-tolerance-ratio",
        type=float,
        default=0.02,
        help="Relative fish-count tolerance ratio for directional parity (default: 0.02 = 2%)",
    )
    parser.add_argument("--output-csv", help="Output CSV path")
    parser.add_argument("--summary-json", help="Optional JSON summary path")
    parser.add_argument("--summary-md", help="Optional markdown summary path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_csv = (
        Path(args.output_csv)
        if args.output_csv
        else DEFAULT_OUTPUT_DIR / f"fwsea_sales_directional_parity_{stamp}.csv"
    )
    summary_json = (
        Path(args.summary_json)
        if args.summary_json
        else output_csv.with_suffix(".json")
    )
    summary_md = (
        Path(args.summary_md)
        if args.summary_md
        else output_csv.with_suffix(".md")
    )

    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))
    sales_rows = extractor._run_sqlcmd(
        query=build_sales_query(
            since=args.since,
            until=args.until,
            customer_like=args.customer_like,
            site_like=args.site_like,
            only_fw_sources=bool(args.only_fw_sources),
        ),
        headers=[
            "SalesStartTime",
            "SalesOperationID",
            "InputOperationID",
            "SaleActionID",
            "SaleActionType",
            "SaleActionOrder",
            "SalePopulationID",
            "SaleParam1Value",
            "SaleParam10Value",
            "SaleParam11Value",
            "RingText",
            "SaleTransportXml",
            "CustomerGuid",
            "CustomerContactName",
            "SourceContainerName",
            "SourceOfficialID",
            "SourceSite",
            "SourceContainerGroup",
            "SourceProdStage",
        ],
    )
    input_rows = extractor._run_sqlcmd(
        query=build_input_query(
            since=args.since,
            until=args.until,
            customer_like=args.customer_like,
            site_like=args.site_like,
            only_fw_sources=bool(args.only_fw_sources),
        ),
        headers=[
            "SalesOperationID",
            "InputOperationID",
            "InputStartTime",
            "InputActionID",
            "InputActionType",
            "InputActionOrder",
            "InputPopulationID",
            "InputParam10Value",
            "InputParam11Value",
            "InputTransportXml",
            "TargetContainerName",
            "TargetOfficialID",
            "TargetSite",
            "TargetContainerGroup",
            "TargetProdStage",
        ],
    )

    per_pair: dict[tuple[str, str], dict[str, Any]] = {}

    def ensure_pair(pair_key: tuple[str, str]) -> dict[str, Any]:
        entry = per_pair.get(pair_key)
        if entry is not None:
            return entry
        entry = {
            "SalesStartTime": "",
            "InputStartTime": "",
            "SalesOperationID": pair_key[0],
            "InputOperationID": pair_key[1],
            "SourceSites": set(),
            "SourceContainers": set(),
            "SourceStageClasses": Counter(),
            "TargetSites": set(),
            "TargetContainers": set(),
            "TargetStageClasses": Counter(),
            "RingTexts": set(),
            "CustomerNames": set(),
            "TripIDs": set(),
            "SalesActionCount": 0,
            "InputActionCount": 0,
            "SalesOutCountParam10": 0.0,
            "SalesOutBiomassParam11": 0.0,
            "SalesInCountParam1Action25": 0.0,
            "InputInCountParam10": 0.0,
            "InputInBiomassParam11": 0.0,
        }
        per_pair[pair_key] = entry
        return entry

    for row in sales_rows:
        sales_op = normalize(row.get("SalesOperationID"))
        input_op = normalize(row.get("InputOperationID"))
        pair_key = (sales_op, input_op)
        entry = ensure_pair(pair_key)
        if not entry["SalesStartTime"]:
            entry["SalesStartTime"] = normalize(row.get("SalesStartTime"))
        entry["SalesActionCount"] += 1

        source_site = normalize(row.get("SourceSite"))
        source_container = normalize(row.get("SourceContainerName"))
        source_stage_class = classify_prod_stage(normalize(row.get("SourceProdStage")))
        if source_site:
            entry["SourceSites"].add(source_site)
        if source_container:
            entry["SourceContainers"].add(source_container)
        entry["SourceStageClasses"][source_stage_class] += 1

        ring_text = normalize(row.get("RingText"))
        if ring_text:
            entry["RingTexts"].add(ring_text)
        customer_name = normalize(row.get("CustomerContactName"))
        if customer_name:
            entry["CustomerNames"].add(customer_name)
        trip_id = parse_transport_xml(normalize(row.get("SaleTransportXml"))).get("trip_id", "")
        if trip_id:
            entry["TripIDs"].add(trip_id)

        action_type = normalize(row.get("SaleActionType"))
        param1 = to_float(row.get("SaleParam1Value"))
        param10 = to_float(row.get("SaleParam10Value"))
        param11 = to_float(row.get("SaleParam11Value"))

        if action_type == "7":
            entry["SalesOutCountParam10"] += abs(param10)
            entry["SalesOutBiomassParam11"] += abs(param11)
        elif action_type == "25":
            if param1 > 0:
                entry["SalesInCountParam1Action25"] += param1

    for row in input_rows:
        sales_op = normalize(row.get("SalesOperationID"))
        input_op = normalize(row.get("InputOperationID"))
        pair_key = (sales_op, input_op)
        entry = ensure_pair(pair_key)
        if not entry["InputStartTime"]:
            entry["InputStartTime"] = normalize(row.get("InputStartTime"))
        entry["InputActionCount"] += 1

        target_site = normalize(row.get("TargetSite"))
        target_container = normalize(row.get("TargetContainerName"))
        target_stage_class = classify_prod_stage(normalize(row.get("TargetProdStage")))
        if target_site:
            entry["TargetSites"].add(target_site)
        if target_container:
            entry["TargetContainers"].add(target_container)
        entry["TargetStageClasses"][target_stage_class] += 1

        param10 = to_float(row.get("InputParam10Value"))
        param11 = to_float(row.get("InputParam11Value"))
        entry["InputInCountParam10"] += abs(param10)
        entry["InputInBiomassParam11"] += abs(param11)

    output_rows: list[dict[str, Any]] = []
    parity_counter: Counter[str] = Counter()
    exact_pairs = 0
    within_tolerance_pairs = 0
    outside_tolerance_pairs = 0
    missing_input_in_pairs = 0
    missing_sales_out_pairs = 0
    missing_both_count_pairs = 0

    for _, entry in sorted(
        per_pair.items(),
        key=lambda item: (
            normalize(item[1].get("SalesStartTime")),
            normalize(item[1].get("SalesOperationID")),
        ),
        reverse=True,
    ):
        sales_out_count = float(entry["SalesOutCountParam10"])
        input_in_count = float(entry["InputInCountParam10"])
        abs_diff = abs(input_in_count - sales_out_count)
        ratio = (input_in_count / sales_out_count) if sales_out_count > 0 else 0.0
        tolerance = max(float(args.count_tolerance_abs), sales_out_count * float(args.count_tolerance_ratio))
        band = parity_band(
            sales_out_count=sales_out_count,
            input_in_count=input_in_count,
            tolerance_abs=float(args.count_tolerance_abs),
            tolerance_ratio=float(args.count_tolerance_ratio),
        )
        parity_counter[band] += 1
        if band == "exact":
            exact_pairs += 1
        elif band == "within_tolerance":
            within_tolerance_pairs += 1
        elif band == "outside_tolerance":
            outside_tolerance_pairs += 1
        elif band == "missing_input_in":
            missing_input_in_pairs += 1
        elif band == "missing_sales_out":
            missing_sales_out_pairs += 1
        elif band == "missing_both_counts":
            missing_both_count_pairs += 1

        stage_source = (
            entry["SourceStageClasses"].most_common(1)[0][0]
            if entry["SourceStageClasses"]
            else "unknown"
        )
        stage_target = (
            entry["TargetStageClasses"].most_common(1)[0][0]
            if entry["TargetStageClasses"]
            else "unknown"
        )

        output_rows.append(
            {
                "SalesStartTime": normalize(entry["SalesStartTime"]),
                "InputStartTime": normalize(entry["InputStartTime"]),
                "SalesOperationID": normalize(entry["SalesOperationID"]),
                "InputOperationID": normalize(entry["InputOperationID"]),
                "DominantSourceStageClass": stage_source,
                "DominantTargetStageClass": stage_target,
                "SourceSites": join_values(entry["SourceSites"]),
                "SourceContainers": join_values(entry["SourceContainers"]),
                "TargetSites": join_values(entry["TargetSites"]),
                "TargetContainers": join_values(entry["TargetContainers"]),
                "CustomerNames": join_values(entry["CustomerNames"]),
                "RingTexts": join_values(entry["RingTexts"]),
                "TripIDs": join_values(entry["TripIDs"]),
                "SalesActionCount": int(entry["SalesActionCount"]),
                "InputActionCount": int(entry["InputActionCount"]),
                "SalesOutCountParam10": int(round(sales_out_count)),
                "InputInCountParam10": int(round(input_in_count)),
                "CountAbsDiff": int(round(abs_diff)),
                "CountTolerance": int(round(tolerance)),
                "CountRatioInputToSales": round(ratio, 6),
                "CountParityBand": band,
                "SalesOutBiomassParam11": round(float(entry["SalesOutBiomassParam11"]), 3),
                "InputInBiomassParam11": round(float(entry["InputInBiomassParam11"]), 3),
                "SalesInCountParam1Action25": int(round(float(entry["SalesInCountParam1Action25"]))),
            }
        )

    operation_pair_count = len(output_rows)
    pairs_with_sales_out_count = sum(1 for row in output_rows if row["SalesOutCountParam10"] > 0)
    pairs_with_input_in_count = sum(1 for row in output_rows if row["InputInCountParam10"] > 0)
    comparable_pairs = sum(
        1
        for row in output_rows
        if row["SalesOutCountParam10"] > 0 and row["InputInCountParam10"] > 0
    )
    directional_match_rate = (
        (exact_pairs + within_tolerance_pairs) / comparable_pairs
        if comparable_pairs > 0
        else 0.0
    )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "SalesStartTime",
        "InputStartTime",
        "SalesOperationID",
        "InputOperationID",
        "DominantSourceStageClass",
        "DominantTargetStageClass",
        "SourceSites",
        "SourceContainers",
        "TargetSites",
        "TargetContainers",
        "CustomerNames",
        "RingTexts",
        "TripIDs",
        "SalesActionCount",
        "InputActionCount",
        "SalesOutCountParam10",
        "InputInCountParam10",
        "CountAbsDiff",
        "CountTolerance",
        "CountRatioInputToSales",
        "CountParityBand",
        "SalesOutBiomassParam11",
        "InputInBiomassParam11",
        "SalesInCountParam1Action25",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in output_rows:
            writer.writerow(row)

    worst_examples = [
        row
        for row in output_rows
        if row["CountParityBand"] == "outside_tolerance"
    ]
    worst_examples.sort(key=lambda row: row["CountAbsDiff"], reverse=True)
    sample_examples = worst_examples[:15]

    summary: dict[str, Any] = {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "sql_profile": args.sql_profile,
        "filters": {
            "since": args.since or "",
            "until": args.until or "",
            "customer_like": args.customer_like or "",
            "site_like": args.site_like or "",
            "only_fw_sources": bool(args.only_fw_sources),
        },
        "output_csv": str(output_csv),
        "tolerance": {
            "count_abs": float(args.count_tolerance_abs),
            "count_ratio": float(args.count_tolerance_ratio),
        },
        "operation_pair_count": operation_pair_count,
        "sales_action_row_count": len(sales_rows),
        "input_action_row_count": len(input_rows),
        "pairs_with_sales_out_count": pairs_with_sales_out_count,
        "pairs_with_input_in_count": pairs_with_input_in_count,
        "comparable_pairs": comparable_pairs,
        "exact_pairs": exact_pairs,
        "within_tolerance_pairs": within_tolerance_pairs,
        "outside_tolerance_pairs": outside_tolerance_pairs,
        "missing_input_in_pairs": missing_input_in_pairs,
        "missing_sales_out_pairs": missing_sales_out_pairs,
        "missing_both_count_pairs": missing_both_count_pairs,
        "directional_match_rate": directional_match_rate,
        "count_parity_band_counts": {
            "exact": parity_counter.get("exact", 0),
            "within_tolerance": parity_counter.get("within_tolerance", 0),
            "outside_tolerance": parity_counter.get("outside_tolerance", 0),
            "missing_input_in": parity_counter.get("missing_input_in", 0),
            "missing_sales_out": parity_counter.get("missing_sales_out", 0),
            "missing_both_counts": parity_counter.get("missing_both_counts", 0),
        },
    }

    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_md.write_text(
        build_markdown(csv_path=output_csv, summary=summary, examples=sample_examples),
        encoding="utf-8",
    )

    print(f"Wrote directional parity CSV: {output_csv}")
    print(f"Wrote summary JSON: {summary_json}")
    print(f"Wrote summary markdown: {summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
