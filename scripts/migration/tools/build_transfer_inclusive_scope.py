#!/usr/bin/env python3
"""Build a transfer-inclusive population scope from stitched members + SubTransfers.

The output keeps all original input members, then adds destination populations
for any SubTransfers edge whose source population is already in scope.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def pick_column(df: pd.DataFrame, candidates: list[str], *, label: str) -> str:
    for name in candidates:
        if name in df.columns:
            return name
    raise ValueError(f"Missing required {label} column; tried {candidates}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-members", required=True)
    parser.add_argument("--subtransfers", required=True)
    parser.add_argument(
        "--ext-inputs",
        default="scripts/migration/data/extract/ext_inputs.csv",
        help="Optional ext_inputs.csv path for mapping unresolved destinations to batch keys",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    members_path = Path(args.input_members)
    subtransfers_path = Path(args.subtransfers)
    ext_inputs_path = Path(args.ext_inputs)
    output_path = Path(args.output)

    members = pd.read_csv(members_path)
    sub = pd.read_csv(subtransfers_path)

    pop_col = pick_column(
        members,
        ["population_id", "PopulationID", "populationId"],
        label="members population id",
    )
    source_col = pick_column(
        sub,
        ["SourcePopID", "SourcePopBefore", "SourcePop", "source_population_id"],
        label="subtransfers source",
    )
    dest_col = pick_column(
        sub,
        ["DestPopID", "DestPopAfter", "DestPop", "dest_population_id"],
        label="subtransfers destination",
    )

    scope = members.copy()
    scope["scope_reason"] = "original_member"

    in_scope_pop_ids = set(scope[pop_col].dropna().astype(str))
    source_matches = sub[source_col].astype(str).isin(in_scope_pop_ids)
    dest_ids = (
        sub.loc[source_matches, dest_col]
        .dropna()
        .astype(str)
        .drop_duplicates()
    )
    dest_ids_set = set(dest_ids)

    # Pull full member rows for discovered destination populations.
    destination_rows = members[members[pop_col].astype(str).isin(dest_ids_set)].copy()
    destination_rows["scope_reason"] = "dest_from_source_in_scope"

    expanded = pd.concat([scope, destination_rows], ignore_index=True)
    expanded = expanded.drop_duplicates(subset=[pop_col], keep="first")

    # Include unresolved destinations for visibility in the artifact.
    unresolved_dest_ids = sorted(dest_ids_set - set(members[pop_col].astype(str)))
    if unresolved_dest_ids:
        unresolved = pd.DataFrame({pop_col: unresolved_dest_ids})
        unresolved["scope_reason"] = "dest_from_source_in_scope_unresolved"
        unresolved["batch_key"] = pd.NA

        # Best-effort batch-key mapping from ext_inputs PopulationID.
        if ext_inputs_path.exists():
            ext_inputs = pd.read_csv(ext_inputs_path)
            ext_pop_col = pick_column(
                ext_inputs,
                ["PopulationID", "population_id", "populationId"],
                label="ext_inputs population id",
            )
            input_name_col = pick_column(
                ext_inputs,
                ["InputName", "input_name"],
                label="ext_inputs input name",
            )
            input_number_col = pick_column(
                ext_inputs,
                ["InputNumber", "input_number"],
                label="ext_inputs input number",
            )
            year_class_col = pick_column(
                ext_inputs,
                ["YearClass", "year_class"],
                label="ext_inputs year class",
            )
            ext = ext_inputs.copy()
            ext["_pop"] = ext[ext_pop_col].astype(str)
            ext["_batch_key"] = (
                ext[input_name_col].astype(str).str.strip()
                + "|"
                + ext[input_number_col].astype(str).str.strip()
                + "|"
                + ext[year_class_col].astype(str).str.strip()
            )
            ext = ext[["_pop", "_batch_key"]].drop_duplicates(subset=["_pop"], keep="first")

            unresolved["_pop"] = unresolved[pop_col].astype(str)
            unresolved = unresolved.merge(ext, on="_pop", how="left")
            unresolved["batch_key"] = unresolved["_batch_key"]
            unresolved = unresolved.drop(columns=["_pop", "_batch_key"])

        expanded = pd.concat([expanded, unresolved], ignore_index=True)
        expanded = expanded.drop_duplicates(subset=[pop_col], keep="first")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    expanded.to_csv(output_path, index=False)

    original_count = len(scope)
    extra_count = len(expanded) - original_count
    batch_key_count = (
        expanded["batch_key"].dropna().astype(str).nunique()
        if "batch_key" in expanded.columns
        else 0
    )
    unresolved_count = len(unresolved_dest_ids)
    resolved_unmapped_count = 0
    if unresolved_dest_ids and "batch_key" in expanded.columns:
        unresolved_rows = expanded[expanded["scope_reason"] == "dest_from_source_in_scope_unresolved"]
        resolved_unmapped_count = int(unresolved_rows["batch_key"].notna().sum())

    print(
        f"Expanded scope: {len(expanded)} populations "
        f"({extra_count} extra destinations; unresolved={unresolved_count}; "
        f"unresolved_with_batch_key={resolved_unmapped_count}; batch_keys={batch_key_count})"
    )
    print(f"Wrote: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
