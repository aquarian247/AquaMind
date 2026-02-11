# FWSEA Endpoint Pairing Gate Integration (2026-02-11)

## Scope
Implemented the next deterministic step after FWSEA tooling integration:

1. Added endpoint uniqueness/stability acceptance gate tooling.
2. Wired endpoint gates into pilot regression runner as an optional phase.
3. Executed local gate runs against current extract/report artifacts.

No runtime API/UI code changes were made.

## Code changes
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/fwsea_endpoint_pairing_gate.py`
  - New tooling script for component-scoped endpoint acceptance gates.
  - Uses only extract/report artifacts (`internal_delivery`, `internal_delivery_actions`, `populations`, `grouped_organisation`, `population_members.csv`).
  - Computes deterministic endpoint metrics and gate outcomes:
    - evidence (`candidate_rows >= min`),
    - uniqueness (`ambiguous_rows <= max`),
    - coverage (`deterministic/candidate >= min`),
    - stability (`max_targets_per_source <= max`),
    - optional marine-target gate,
    - optional incomplete-linkage fallback gate via semantic summary JSON.
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_pilot_regression_check.py`
  - Added optional FWSEA endpoint-gate execution (`--run-fwsea-endpoint-gates`).
  - Added threshold flags and optional enforcement mode (`--fwsea-endpoint-enforce`).
  - Added endpoint gate results section to cohort markdown output.
  - Integration hardening: endpoint gates still run even when semantic validation output is missing (e.g., missing `ExternalIdMap`).
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/README.md`
  - Added `fwsea_endpoint_pairing_gate.py` to active tooling list.

## Exact commands run

### Tooling health checks
```bash
cd /Users/aquarian247/Projects/AquaMind
python -m py_compile \
  scripts/migration/tools/fwsea_endpoint_pairing_gate.py \
  scripts/migration/tools/migration_pilot_regression_check.py
python scripts/migration/tools/fwsea_endpoint_pairing_gate.py --help
python scripts/migration/tools/migration_pilot_regression_check.py --help
```

### Component-scoped endpoint gate (Stofnfiskur Juni 24)
```bash
cd /Users/aquarian247/Projects/AquaMind
python scripts/migration/tools/fwsea_endpoint_pairing_gate.py \
  --csv-dir scripts/migration/data/extract \
  --report-dir scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --expected-direction sales_to_input \
  --max-source-candidates 2 \
  --max-target-candidates 1 \
  --min-deterministic-coverage 0.90 \
  --max-ambiguous-rows 0 \
  --max-targets-per-source 1 \
  --min-candidate-rows 10 \
  --require-evidence \
  --require-marine-target \
  --min-marine-target-ratio 1.0 \
  --output aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_endpoint_pairing_gate_stofnfiskur_juni24_2026-02-11.md \
  --summary-json aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_endpoint_pairing_gate_stofnfiskur_juni24_2026-02-11.summary.json
```

Observed outcome:
- Overall endpoint gate: `PASS`
- Candidate rows: `15`
- Deterministic rows: `15`
- Deterministic coverage: `1.000`
- Ambiguous rows: `0`
- Dominant stage pair: `fw->marine` (`15` rows)

### Pilot regression runner smoke test with endpoint gates
```bash
cd /Users/aquarian247/Projects/AquaMind
python scripts/migration/tools/migration_pilot_regression_check.py \
  --analysis-dir aquamind/docs/progress/migration/analysis_reports/2026-02-11 \
  --component-key B884F78F-1E92-49C0-AE28-39DFC2E18C01 \
  --run-fwsea-endpoint-gates \
  --fwsea-endpoint-expected-direction sales_to_input \
  --fwsea-endpoint-max-source-candidates 2 \
  --fwsea-endpoint-max-target-candidates 1 \
  --fwsea-endpoint-min-deterministic-coverage 0.90 \
  --fwsea-endpoint-max-ambiguous-rows 0 \
  --fwsea-endpoint-max-targets-per-source 1 \
  --fwsea-endpoint-min-candidate-rows 10 \
  --fwsea-endpoint-require-evidence \
  --fwsea-endpoint-require-marine-target \
  --fwsea-endpoint-min-marine-target-ratio 1.0
```

Observed outcome:
- Semantic phase failed in current migration DB due missing `ExternalIdMap` for the component.
- Endpoint gate still executed and produced outputs:
  - `fwsea_endpoint_gate_Stofnfiskur_S_21_nov23_5_2023_2026-02-11.md`
  - `fwsea_endpoint_gate_Stofnfiskur_S_21_nov23_5_2023_2026-02-11.summary.json`
- Endpoint gate result for this component: `FAIL` (uniqueness only: `ambiguous_rows=1`, max allowed `0`; coverage `0.917` passed).

## Generated artifacts
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_endpoint_pairing_gate_stofnfiskur_juni24_2026-02-11.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_endpoint_pairing_gate_stofnfiskur_juni24_2026-02-11.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_endpoint_gate_Stofnfiskur_S_21_nov23_5_2023_2026-02-11.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_endpoint_gate_Stofnfiskur_S_21_nov23_5_2023_2026-02-11.summary.json`

## Compact findings table
| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
| --- | --- | --- | --- | --- |
| Endpoint gate (Stofnfiskur Juni 24, strict fw->marine config) | Y | 15/15 deterministic candidate rows, 0 ambiguous | High | Candidate for policy-readiness evidence set; keep tooling-only for now |
| Endpoint gate (Stofnfiskur S-21 nov23, same strict config) | Partial | 11/12 deterministic candidate rows, 1 ambiguous | Medium | Keep NO-GO for policy auto-link; investigate ambiguous row semantics |
| Pilot regression integration path | Y | endpoint gate runs even when semantic summary missing | High | Keep this decoupled behavior so deterministic gate evidence is always collectible |

## Go / No-Go
1. **GO**: endpoint-pairing acceptance gate tooling integration (implemented).
2. **NO-GO**: migration-policy/runtime FW/Sea auto-link promotion remains blocked until endpoint gates pass broadly across target cohorts with no incomplete-linkage fallback regression.
