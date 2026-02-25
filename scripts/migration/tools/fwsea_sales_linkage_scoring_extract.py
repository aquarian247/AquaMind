#!/usr/bin/env python3
# flake8: noqa: E501,C901,E402
"""Deterministic FW->Sea sales linkage scoring extract from FishTalk SQL.

This tooling query emits one scored row per sales action (ActionType=7 on
InternalDelivery.SalesOperationID) with:
- customer (ActionMetaData ParameterID=220 -> Contact)
- ring text (ParameterID=96)
- trip/transport tags (ParameterID=184 TransportXML)
- exact-time status sales snapshot (PublicStatusValues at operation StartTime)

Deterministic status tie-break for same (PopulationID, StatusTime):
1) non-zero SalesCount/SalesBiomassKg over zero
2) higher SalesCount
3) higher SalesBiomassKg
4) higher CurrentCount
5) higher CurrentBiomassKg
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migration.extractors.base import BaseExtractor, ExtractionContext


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "scripts" / "migration" / "output"
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)


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


def is_uuid_like(value: str | None) -> int:
    return 1 if UUID_RE.match(normalize(value)) else 0


def compute_score(
    *,
    has_customer: int,
    has_ring: int,
    has_trip: int,
    has_status_sales_count: int,
    has_status_sales_biomass: int,
) -> int:
    # Deterministic evidence-completeness score (0..100).
    return (
        25 * has_customer
        + 20 * has_ring
        + 20 * has_trip
        + 25 * has_status_sales_count
        + 10 * has_status_sales_biomass
    )


def score_band(score: int) -> str:
    if score >= 80:
        return "strong"
    if score >= 60:
        return "medium"
    if score >= 40:
        return "weak"
    return "sparse"


def build_query(
    *,
    since: str | None,
    until: str | None,
    customer_like: str | None,
    site_like: str | None,
    only_fw_sources: bool,
    limit: int | None,
) -> str:
    filters: list[str] = ["o.OperationType = 7"]
    if since:
        filters.append(f"o.StartTime >= '{sql_quote(since)}'")
    if until:
        filters.append(f"o.StartTime < '{sql_quote(until)}'")
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
    top_sql = f"TOP {int(limit)} " if limit and limit > 0 else ""

    return f"""
WITH base AS (
    SELECT
        o.StartTime AS SalesStartTimeRaw,
        CONVERT(varchar(36), id.SalesOperationID) AS SalesOperationID,
        CONVERT(varchar(36), id.InputOperationID) AS InputOperationID,
        CONVERT(varchar(36), id.InputSiteID) AS InputSiteID,
        CONVERT(varchar(36), id.PlannedActivityID) AS PlannedActivityID,
        CONVERT(varchar(10), o.OperationType) AS SalesOperationType,
        CONVERT(varchar(36), a.ActionID) AS SaleActionID,
        CONVERT(varchar(10), a.ActionOrder) AS SaleActionOrder,
        CONVERT(varchar(36), a.PopulationID) AS PopulationID,
        ISNULL(c.ContainerName, '') AS SourceContainerName,
        ISNULL(c.OfficialID, '') AS SourceOfficialID,
        ISNULL(go.Site, '') AS SourceSite,
        ISNULL(go.ContainerGroup, '') AS SourceContainerGroup,
        ISNULL(go.ProdStage, '') AS SourceProdStage,
        ISNULL(CONVERT(varchar(36), m220.ParameterGuid), '') AS CustomerGuid,
        ISNULL(cn220.Name, '') AS CustomerContactName,
        ISNULL(REPLACE(REPLACE(REPLACE(m96.ParameterString, '|', '/'), CHAR(13), ' '), CHAR(10), ' '), '') AS RingText,
        ISNULL(REPLACE(REPLACE(REPLACE(m184.ParameterString, '|', '/'), CHAR(13), ' '), CHAR(10), ' '), '') AS TransportXml
    FROM dbo.InternalDelivery id
    JOIN dbo.Operations o
      ON o.OperationID = id.SalesOperationID
    JOIN dbo.Action a
      ON a.OperationID = o.OperationID
     AND a.ActionType = 7
    LEFT JOIN dbo.Populations p
      ON p.PopulationID = a.PopulationID
    LEFT JOIN dbo.Containers c
      ON c.ContainerID = p.ContainerID
    LEFT JOIN dbo.Ext_GroupedOrganisation_v2 go
      ON go.ContainerID = c.ContainerID
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
),
status_ranked AS (
    SELECT
        b.*,
        ISNULL(CONVERT(varchar(32), sv.SalesCount), '') AS StatusSalesCount,
        ISNULL(CONVERT(varchar(32), sv.SalesBiomassKg), '') AS StatusSalesBiomassKg,
        ISNULL(CONVERT(varchar(32), sv.CurrentCount), '') AS StatusCurrentCount,
        ISNULL(CONVERT(varchar(32), sv.CurrentBiomassKg), '') AS StatusCurrentBiomassKg,
        ROW_NUMBER() OVER (
            PARTITION BY b.SaleActionID
            ORDER BY
                CASE WHEN ISNULL(sv.SalesCount, 0) <> 0 OR ISNULL(sv.SalesBiomassKg, 0) <> 0 THEN 1 ELSE 0 END DESC,
                ISNULL(sv.SalesCount, 0) DESC,
                ISNULL(sv.SalesBiomassKg, 0) DESC,
                ISNULL(sv.CurrentCount, 0) DESC,
                ISNULL(sv.CurrentBiomassKg, 0) DESC
        ) AS rn
    FROM base b
    LEFT JOIN dbo.PublicStatusValues sv
      ON sv.PopulationID = b.PopulationID
     AND sv.StatusTime = b.SalesStartTimeRaw
)
SELECT {top_sql}
    CONVERT(varchar(19), SalesStartTimeRaw, 120) AS SalesStartTime,
    SalesOperationID,
    InputOperationID,
    InputSiteID,
    PlannedActivityID,
    SalesOperationType,
    SaleActionID,
    SaleActionOrder,
    PopulationID,
    SourceContainerName,
    SourceOfficialID,
    SourceSite,
    SourceContainerGroup,
    SourceProdStage,
    CustomerGuid,
    CustomerContactName,
    RingText,
    TransportXml,
    StatusSalesCount,
    StatusSalesBiomassKg,
    StatusCurrentCount,
    StatusCurrentBiomassKg
FROM status_ranked
WHERE rn = 1
ORDER BY SalesStartTimeRaw DESC, SalesOperationID, SaleActionID
"""


def build_markdown(
    *,
    csv_path: Path,
    summary: dict[str, Any],
    sample_rows: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# FWSEA Sales Linkage Scoring Extract")
    lines.append("")
    lines.append("## Run Summary")
    lines.append(f"- Output CSV: `{csv_path}`")
    lines.append(f"- Row count: `{summary['row_count']}`")
    lines.append(f"- Distinct sales operations: `{summary['distinct_sales_operations']}`")
    lines.append(f"- Distinct sale actions: `{summary['distinct_sale_actions']}`")
    lines.append(f"- Distinct populations: `{summary['distinct_populations']}`")
    lines.append(f"- FW source rows: `{summary['fw_source_rows']}`")
    lines.append(f"- Rows with customer: `{summary['rows_with_customer']}`")
    lines.append(f"- Rows with ring: `{summary['rows_with_ring']}`")
    lines.append(f"- Rows with trip: `{summary['rows_with_trip']}`")
    lines.append(f"- Rows with status sales count > 0: `{summary['rows_with_status_sales_count']}`")
    lines.append("")
    lines.append("## Score Bands")
    lines.append("| band | rows |")
    lines.append("| --- | ---: |")
    for band, count in summary["score_band_counts"].items():
        lines.append(f"| {band} | {count} |")
    lines.append("")
    lines.append("## Evidence Slices")
    lines.append("| slice (C/R/T/S) | rows |")
    lines.append("| --- | ---: |")
    for key, count in summary.get("evidence_slice_counts", {}).items():
        lines.append(f"| {key} | {count} |")
    lines.append("")
    lines.append("## Top Customers")
    lines.append("| customer | rows |")
    lines.append("| --- | ---: |")
    for customer, count in summary["top_customers"]:
        label = customer or "(blank)"
        lines.append(f"| {label} | {count} |")
    lines.append("")
    lines.append("## Transport Field Quality")
    transport = summary.get("transport_field_quality", {})
    lines.append("| metric | rows |")
    lines.append("| --- | ---: |")
    for key in [
        "rows_with_transport_xml",
        "rows_with_any_transport_field",
        "rows_with_trip_id",
        "rows_with_compartment_id",
        "rows_with_compartment_nr",
        "rows_with_carrier_id",
        "rows_with_transporter_id",
        "rows_with_trip_uuid_like",
        "rows_with_carrier_uuid_like",
        "rows_with_transporter_uuid_like",
    ]:
        lines.append(f"| {key} | {transport.get(key, 0)} |")
    lines.append("")
    lines.append("## Sample Rows")
    lines.append("| start | source site | container | customer | ring | trip | sales count | score | band |")
    lines.append("| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |")
    for row in sample_rows:
        lines.append(
            "| "
            f"{row.get('SalesStartTime', '')} | "
            f"{row.get('SourceSite', '')} | "
            f"{row.get('SourceContainerName', '')} | "
            f"{row.get('CustomerContactName', '')} | "
            f"{row.get('RingText', '')} | "
            f"{row.get('TripID', '')} | "
            f"{row.get('StatusSalesCount', '')} | "
            f"{row.get('LinkageScore', '')} | "
            f"{row.get('ScoreBand', '')} |"
        )
    lines.append("")
    lines.append("## Scoring Formula")
    lines.append("- +25: customer present (`ParameterID=220`)")  # noqa: RUF001
    lines.append("- +20: ring text present (`ParameterID=96`)")
    lines.append("- +20: trip id present (`ParameterID=184` TransportXML)")
    lines.append("- +25: status sales count > 0 at exact operation time")
    lines.append("- +10: status sales biomass > 0 at exact operation time")
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deterministic FW->Sea sales linkage scoring extract"
    )
    parser.add_argument("--sql-profile", default="fishtalk_readonly")
    parser.add_argument("--since", help="Include operations with StartTime >= this timestamp")
    parser.add_argument("--until", help="Include operations with StartTime < this timestamp")
    parser.add_argument("--customer-like", help="Optional LIKE filter on customer contact name")
    parser.add_argument("--site-like", help="Optional LIKE filter on source site name")
    parser.add_argument(
        "--only-fw-sources",
        action="store_true",
        help="Restrict to source rows with FW/Hatchery-like prod stage",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional TOP N limit after deterministic ranking",
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
        else DEFAULT_OUTPUT_DIR / f"fwsea_sales_linkage_scoring_{stamp}.csv"
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
    query = build_query(
        since=args.since,
        until=args.until,
        customer_like=args.customer_like,
        site_like=args.site_like,
        only_fw_sources=bool(args.only_fw_sources),
        limit=args.limit,
    )

    headers = [
        "SalesStartTime",
        "SalesOperationID",
        "InputOperationID",
        "InputSiteID",
        "PlannedActivityID",
        "SalesOperationType",
        "SaleActionID",
        "SaleActionOrder",
        "PopulationID",
        "SourceContainerName",
        "SourceOfficialID",
        "SourceSite",
        "SourceContainerGroup",
        "SourceProdStage",
        "CustomerGuid",
        "CustomerContactName",
        "RingText",
        "TransportXml",
        "StatusSalesCount",
        "StatusSalesBiomassKg",
        "StatusCurrentCount",
        "StatusCurrentBiomassKg",
    ]
    rows = extractor._run_sqlcmd(query=query, headers=headers)

    enriched_rows: list[dict[str, Any]] = []
    for row in rows:
        transport_xml = normalize(row.get("TransportXml"))
        parsed = parse_transport_xml(normalize(row.get("TransportXml")))
        has_customer = 1 if normalize(row.get("CustomerContactName")) else 0
        has_ring = 1 if normalize(row.get("RingText")) else 0
        has_trip = 1 if parsed["trip_id"] else 0
        sales_count = to_float(row.get("StatusSalesCount"))
        sales_biomass = to_float(row.get("StatusSalesBiomassKg"))
        has_status_sales_count = 1 if sales_count > 0 else 0
        has_status_sales_biomass = 1 if sales_biomass > 0 else 0
        score = compute_score(
            has_customer=has_customer,
            has_ring=has_ring,
            has_trip=has_trip,
            has_status_sales_count=has_status_sales_count,
            has_status_sales_biomass=has_status_sales_biomass,
        )
        stage_class = classify_prod_stage(normalize(row.get("SourceProdStage")))

        out_row: dict[str, Any] = {
            "SalesStartTime": normalize(row.get("SalesStartTime")),
            "SalesOperationID": normalize(row.get("SalesOperationID")),
            "InputOperationID": normalize(row.get("InputOperationID")),
            "InputSiteID": normalize(row.get("InputSiteID")),
            "PlannedActivityID": normalize(row.get("PlannedActivityID")),
            "SalesOperationType": normalize(row.get("SalesOperationType")),
            "SaleActionID": normalize(row.get("SaleActionID")),
            "SaleActionOrder": normalize(row.get("SaleActionOrder")),
            "PopulationID": normalize(row.get("PopulationID")),
            "SourceSite": normalize(row.get("SourceSite")),
            "SourceProdStage": normalize(row.get("SourceProdStage")),
            "SourceStageClass": stage_class,
            "SourceContainerGroup": normalize(row.get("SourceContainerGroup")),
            "SourceContainerName": normalize(row.get("SourceContainerName")),
            "SourceOfficialID": normalize(row.get("SourceOfficialID")),
            "CustomerGuid": normalize(row.get("CustomerGuid")),
            "CustomerContactName": normalize(row.get("CustomerContactName")),
            "RingText": normalize(row.get("RingText")),
            "TripID": parsed["trip_id"],
            "CompartmentID": parsed["compartment_id"],
            "CompartmentNr": parsed["compartment_nr"],
            "CarrierID": parsed["carrier_id"],
            "TransporterID": parsed["transporter_id"],
            "HasTransportXml": 1 if transport_xml else 0,
            "StatusSalesCount": normalize(row.get("StatusSalesCount")),
            "StatusSalesBiomassKg": normalize(row.get("StatusSalesBiomassKg")),
            "StatusCurrentCount": normalize(row.get("StatusCurrentCount")),
            "StatusCurrentBiomassKg": normalize(row.get("StatusCurrentBiomassKg")),
            "HasCustomer": has_customer,
            "HasRing": has_ring,
            "HasTrip": has_trip,
            "HasStatusSalesCount": has_status_sales_count,
            "HasStatusSalesBiomassKg": has_status_sales_biomass,
            "LinkageScore": score,
            "ScoreBand": score_band(score),
        }
        enriched_rows.append(out_row)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "SalesStartTime",
        "SalesOperationID",
        "InputOperationID",
        "InputSiteID",
        "PlannedActivityID",
        "SalesOperationType",
        "SaleActionID",
        "SaleActionOrder",
        "PopulationID",
        "SourceSite",
        "SourceProdStage",
        "SourceStageClass",
        "SourceContainerGroup",
        "SourceContainerName",
        "SourceOfficialID",
        "CustomerGuid",
        "CustomerContactName",
        "RingText",
        "TripID",
        "CompartmentID",
        "CompartmentNr",
        "CarrierID",
        "TransporterID",
        "HasTransportXml",
        "StatusSalesCount",
        "StatusSalesBiomassKg",
        "StatusCurrentCount",
        "StatusCurrentBiomassKg",
        "HasCustomer",
        "HasRing",
        "HasTrip",
        "HasStatusSalesCount",
        "HasStatusSalesBiomassKg",
        "LinkageScore",
        "ScoreBand",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in enriched_rows:
            writer.writerow(row)

    score_band_counts = Counter(row["ScoreBand"] for row in enriched_rows)
    evidence_slice_counts = Counter(
        f"C{row['HasCustomer']}_R{row['HasRing']}_T{row['HasTrip']}_S{row['HasStatusSalesCount']}"
        for row in enriched_rows
    )
    top_customers = Counter(
        normalize(row["CustomerContactName"]) for row in enriched_rows if normalize(row["CustomerContactName"])
    ).most_common(10)
    transport_field_quality = {
        "rows_with_transport_xml": sum(1 for row in enriched_rows if row["HasTransportXml"] == 1),
        "rows_with_any_transport_field": sum(
            1
            for row in enriched_rows
            if row["TripID"] or row["CompartmentID"] or row["CompartmentNr"] or row["CarrierID"] or row["TransporterID"]
        ),
        "rows_with_trip_id": sum(1 for row in enriched_rows if row["TripID"]),
        "rows_with_compartment_id": sum(1 for row in enriched_rows if row["CompartmentID"]),
        "rows_with_compartment_nr": sum(1 for row in enriched_rows if row["CompartmentNr"]),
        "rows_with_carrier_id": sum(1 for row in enriched_rows if row["CarrierID"]),
        "rows_with_transporter_id": sum(1 for row in enriched_rows if row["TransporterID"]),
        "rows_with_trip_uuid_like": sum(is_uuid_like(row["TripID"]) for row in enriched_rows),
        "rows_with_carrier_uuid_like": sum(is_uuid_like(row["CarrierID"]) for row in enriched_rows),
        "rows_with_transporter_uuid_like": sum(is_uuid_like(row["TransporterID"]) for row in enriched_rows),
    }
    summary: dict[str, Any] = {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "sql_profile": args.sql_profile,
        "filters": {
            "since": args.since or "",
            "until": args.until or "",
            "customer_like": args.customer_like or "",
            "site_like": args.site_like or "",
            "only_fw_sources": bool(args.only_fw_sources),
            "limit": args.limit or 0,
        },
        "output_csv": str(output_csv),
        "row_count": len(enriched_rows),
        "distinct_sales_operations": len({row["SalesOperationID"] for row in enriched_rows if row["SalesOperationID"]}),
        "distinct_sale_actions": len({row["SaleActionID"] for row in enriched_rows if row["SaleActionID"]}),
        "distinct_populations": len({row["PopulationID"] for row in enriched_rows if row["PopulationID"]}),
        "fw_source_rows": sum(1 for row in enriched_rows if row["SourceStageClass"] == "fw"),
        "rows_with_customer": sum(1 for row in enriched_rows if row["HasCustomer"] == 1),
        "rows_with_ring": sum(1 for row in enriched_rows if row["HasRing"] == 1),
        "rows_with_trip": sum(1 for row in enriched_rows if row["HasTrip"] == 1),
        "rows_with_status_sales_count": sum(1 for row in enriched_rows if row["HasStatusSalesCount"] == 1),
        "rows_with_status_sales_biomass": sum(1 for row in enriched_rows if row["HasStatusSalesBiomassKg"] == 1),
        "evidence_slice_counts": dict(sorted(evidence_slice_counts.items())),
        "transport_field_quality": transport_field_quality,
        "score_band_counts": {
            "strong": score_band_counts.get("strong", 0),
            "medium": score_band_counts.get("medium", 0),
            "weak": score_band_counts.get("weak", 0),
            "sparse": score_band_counts.get("sparse", 0),
        },
        "top_customers": top_customers,
    }

    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    sample_rows = enriched_rows[:15]
    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_md.write_text(
        build_markdown(csv_path=output_csv, summary=summary, sample_rows=sample_rows),
        encoding="utf-8",
    )

    print(f"Wrote scoring CSV: {output_csv}")
    print(f"Wrote summary JSON: {summary_json}")
    print(f"Wrote summary markdown: {summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
