#!/usr/bin/env bash
set -euo pipefail

SQL_ROOT="/tmp/fwsea_phase0_partab_2026-02-11/sql"
OUT_ROOT="/tmp/fwsea_phase0_partab_2026-02-11/out"

run_reader() {
  local sql_file="$1"
  local out_file="$2"
  cat "$sql_file" | docker exec -i sqlserver /opt/mssql-tools18/bin/sqlcmd \
    -b -C -S localhost,1433 -U fishtalk_reader -P '<REDACTED>' -d FishTalk -W \
    > "$out_file"
}

run_sa() {
  local sql_file="$1"
  local out_file="$2"
  cat "$sql_file" | docker exec -i sqlserver /opt/mssql-tools18/bin/sqlcmd \
    -b -C -S localhost,1433 -U sa -P '<REDACTED>' -d FishTalk -W \
    > "$out_file"
}

# Core pack run (reader)
while IFS= read -r sql_path; do
  base_name="$(basename "$sql_path" .sql)"
  run_reader "$sql_path" "$OUT_ROOT/${base_name}.txt"
done < <(find "$SQL_ROOT" -maxdepth 1 -type f -name '*.sql' | sort)

# Elevated Phase 0 cross-checks (sa)
for name in P0a_inventory_counts.sql P0b_module_readability.sql P0c_keyword_ActionMetaData.sql P0c_keyword_Ext_Transfers.sql P0c_keyword_InternalDelivery.sql P0c_keyword_LinkType.sql P0c_keyword_ParameterID.sql P0c_keyword_PopulationLink.sql P0c_keyword_ProductionStage.sql P0c_keyword_PublicTransfers.sql P0c_keyword_TransportCarrier.sql P0d_view_readability.sql P0e_trigger_inventory.sql P0f_dependency_crosscheck.sql S13_key_view_definitions_full.sql S14_module_keyword_sweep_sa.sql; do
  src="$SQL_ROOT/$name"
  dst="$OUT_ROOT/${name%.sql}_sa.txt"
  run_sa "$src" "$dst"
done

# Explicit rerun with provided credential (2026-02-11)
run_sa "$SQL_ROOT/P0d_view_readability.sql" "$OUT_ROOT/P0d_view_readability_sa.txt"
run_sa "$SQL_ROOT/P0f_dependency_crosscheck.sql" "$OUT_ROOT/P0f_dependency_crosscheck_sa.txt"
