#!/usr/bin/env python3
"""Generate non-canonical FW→Sea heuristic candidates (post-smolt hall overlay).

This script is a review tool only. It does NOT alter migration data and should not
be used as deterministic linkage without validation.
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]

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

POST_SMOLT_HALLS = {
    "S03 NORÐTOFTIR": {"18 HØLL A", "18 HØLL B"},
    "S08 GJÓGV": {"T-HØLL"},
    "S16 GLYVRADALUR": {"E1 HØLL", "E2 HØLL"},
    "S21 VIÐAREIÐI": {"E", "F"},
    "S24 STROND": {"G HØLL", "H HØLL", "I HØLL", "J HØLL"},
}


def normalize_label(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split()).strip()


def normalize_key(value: str | None) -> str:
    return normalize_label(value).upper()


def parse_sea_name(name: str) -> dict | None:
    match = SEA_NAME_RE.search(name.upper())
    if not match:
        return None
    data = match.groupdict()
    sea_month = MONTH_MAP.get(data["seamonth"][:3])
    fw_month = MONTH_MAP.get(data["fwmonth"][:3])
    sea_year = 2000 + int(data["seayear"])
    fw_year = 2000 + int(data["fwyer"])
    sea_date = pd.Timestamp(year=sea_year, month=sea_month, day=1) if sea_month else pd.NaT
    fw_date = pd.Timestamp(year=fw_year, month=fw_month, day=1) if fw_month else pd.NaT
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


def station_code(site: str | None) -> str | None:
    if not site:
        return None
    match = STATION_RE.search(site)
    return match.group(1) if match else None


def is_post_smolt_hall(site: str | None, hall_label: str | None) -> bool:
    site_key = normalize_key(site)
    hall_key = normalize_key(hall_label)
    return hall_key in POST_SMOLT_HALLS.get(site_key, set())


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate heuristic FW→Sea candidate links (post-smolt overlay)")
    parser.add_argument(
        "--csv-dir",
        default=str(PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"),
        help="CSV directory (bulk_extract_fishtalk.py output)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "aquamind" / "docs" / "progress" / "migration" / "analysis_reports" / "2026-02-03"),
        help="Output directory for the report",
    )
    parser.add_argument("--min-start", default="2023-01-01", help="Earliest sea StartTime (YYYY-MM-DD)")
    parser.add_argument("--window-days", type=int, default=60, help="FW EndTime window around sea StartTime")
    parser.add_argument("--top-per-sea", type=int, default=5, help="Top candidates per sea population")
    args = parser.parse_args()

    csv_dir = Path(args.csv_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ext_pop = pd.read_csv(
        csv_dir / "ext_populations.csv",
        usecols=["PopulationID", "ContainerID", "PopulationName", "StartTime", "EndTime"],
    )
    ext_pop["StartTime"] = pd.to_datetime(ext_pop["StartTime"], errors="coerce")
    ext_pop["EndTime"] = pd.to_datetime(ext_pop["EndTime"], errors="coerce")

    grouping = pd.read_csv(
        csv_dir / "grouped_organisation.csv",
        usecols=["ContainerID", "Site", "ProdStage", "ContainerGroup"],
    )
    merged = ext_pop.merge(grouping, on="ContainerID", how="left")
    merged["StationCode"] = merged["Site"].astype(str).str.extract(STATION_RE, expand=False)

    # Sea populations with naming pattern
    sea = merged[
        (merged["ProdStage"] == "MarineSite")
        & (merged["StartTime"] >= pd.Timestamp(args.min_start))
        & merged["PopulationName"].notna()
    ].copy()
    parsed = sea["PopulationName"].apply(parse_sea_name)
    sea = sea[parsed.notna()].copy()
    sea = sea.join(pd.DataFrame(list(parsed.dropna().values), index=parsed.dropna().index))

    # FW populations limited to post-smolt halls
    fw = merged[merged["ProdStage"].isin(["FreshWater", "SmoltProduction", "Hatchery"])].copy()
    fw = fw[fw["ContainerGroup"].notna()]
    fw = fw[fw.apply(lambda r: is_post_smolt_hall(r.get("Site"), r.get("ContainerGroup")), axis=1)]
    fw = fw[fw["EndTime"].notna()]

    fw_groups = {code: df for code, df in fw.groupby("StationCode") if isinstance(code, str)}

    records = []
    for _, sea_row in sea.iterrows():
        station = sea_row["FWStationCode"]
        sea_start = sea_row["StartTime"]
        if station not in fw_groups or pd.isna(sea_start):
            continue
        fw_candidates = fw_groups[station].copy()
        fw_candidates["DiffDays"] = (fw_candidates["EndTime"] - sea_start).dt.days
        fw_candidates = fw_candidates[fw_candidates["DiffDays"].abs() <= args.window_days]
        if fw_candidates.empty:
            continue

        for _, fw_row in fw_candidates.iterrows():
            diff_days = fw_row["DiffDays"]
            score = 40
            if abs(diff_days) <= 7:
                score += 20
            elif abs(diff_days) <= 21:
                score += 10
            elif abs(diff_days) <= args.window_days:
                score += 5

            if pd.notna(sea_row.get("SeaDate")):
                if sea_start.month == sea_row["SeaDate"].month and sea_start.year == sea_row["SeaDate"].year:
                    score += 5
            if pd.notna(sea_row.get("FWBatchDate")) and pd.notna(fw_row["StartTime"]):
                if (
                    fw_row["StartTime"].month == sea_row["FWBatchDate"].month
                    and fw_row["StartTime"].year == sea_row["FWBatchDate"].year
                ):
                    score += 5

            records.append(
                {
                    "SeaPopulationID": sea_row["PopulationID"],
                    "SeaPopulationName": sea_row["PopulationName"],
                    "SeaSite": sea_row["Site"],
                    "SeaStartTime": sea_start,
                    "SeaUnit": sea_row["Unit"],
                    "SeaFWStationCode": sea_row["FWStationCode"],
                    "SeaSupplierCode": sea_row["SupplierCode"],
                    "SeaName_SeaDate": sea_row["SeaDate"],
                    "SeaName_FWBatchDate": sea_row["FWBatchDate"],
                    "FWPopulationID": fw_row["PopulationID"],
                    "FWPopulationName": fw_row["PopulationName"],
                    "FWSite": fw_row["Site"],
                    "FWContainerGroup": fw_row["ContainerGroup"],
                    "FWStartTime": fw_row["StartTime"],
                    "FWEndTime": fw_row["EndTime"],
                    "DiffDays_FWEnd_to_SeaStart": diff_days,
                    "Score_Base": score,
                }
            )

    pairs = pd.DataFrame(records)
    if pairs.empty:
        out_csv = output_dir / "fw_to_sea_heuristic_candidates_postsmolt_2026-02-03.csv"
        pairs.to_csv(out_csv, index=False)
        out_md = output_dir / "fw_to_sea_heuristic_candidates_postsmolt_2026-02-03.md"
        out_md.write_text("No candidate pairs found for the selected window.\n")
        return 0

    sea_ids = set(pairs["SeaPopulationID"])
    fw_ids = set(pairs["FWPopulationID"])

    # Count alignment from status_values.csv
    status_path = csv_dir / "status_values.csv"
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
    sea_best_time = {}
    sea_best_count = {}
    fw_best_time = {}
    fw_best_count = {}

    if status_path.exists():
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

    def ratio(row):
        if pd.notna(row["SeaFirstCount"]) and pd.notna(row["FWLastCount"]) and row["FWLastCount"]:
            return row["SeaFirstCount"] / row["FWLastCount"]
        return pd.NA

    pairs["CountRatio"] = pairs.apply(ratio, axis=1)
    pairs["Score"] = pairs["Score_Base"]
    for idx, row in pairs.iterrows():
        ratio_val = row["CountRatio"]
        if pd.isna(ratio_val):
            continue
        if 0.7 <= ratio_val <= 1.3:
            pairs.at[idx, "Score"] += 20
        elif 0.5 <= ratio_val <= 1.5:
            pairs.at[idx, "Score"] += 10

    pairs_sorted = pairs.sort_values(
        ["SeaPopulationID", "Score", "DiffDays_FWEnd_to_SeaStart"],
        ascending=[True, False, True],
    )
    final = pairs_sorted.groupby("SeaPopulationID").head(args.top_per_sea).copy()

    out_csv = output_dir / "fw_to_sea_heuristic_candidates_postsmolt_2026-02-03.csv"
    final.to_csv(out_csv, index=False)

    summary = {
        "sea_populations_pattern_2023plus": len(sea),
        "fw_populations_postsmolt": len(fw),
        "candidate_pairs_within_window": len(pairs),
        "final_pairs_top_per_sea": len(final),
        "pairs_with_count_alignment": int(final["CountRatio"].notna().sum()),
    }

    out_md = output_dir / "fw_to_sea_heuristic_candidates_postsmolt_2026-02-03.md"
    with out_md.open("w", encoding="utf-8") as handle:
        handle.write("# FW→Sea Heuristic Candidates (Post‑Smolt overlay)\n\n")
        handle.write("**Method (heuristic):**\n")
        handle.write(
            "- Sea populations: `Ext_Populations_v2` names matching pattern like "
            "`S07 S21 SF NOV 25 (JUN 24)`, `ProdStage = MarineSite`, `StartTime >= 2023-01-01`.\n"
        )
        handle.write(
            "- FW candidates: `ProdStage in {FreshWater, SmoltProduction, Hatchery}` AND hall "
            "mapped to **Post‑Smolt** (Faroe hall mapping).\n"
        )
        handle.write(f"- Time window: FW `EndTime` within ±{args.window_days} days of sea `StartTime`.\n")
        handle.write("- Scoring: date alignment + optional count alignment from `status_values.csv`.\n\n")
        handle.write("**Summary:**\n")
        for key, value in summary.items():
            handle.write(f"- {key}: {value}\n")
        handle.write("\n**Output CSV:** `fw_to_sea_heuristic_candidates_postsmolt_2026-02-03.csv`\n")
        handle.write("\n**Important:** Non‑canonical review aid only. Do not use as deterministic linkage.\n")

    print(f"Wrote {out_csv}")
    print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
