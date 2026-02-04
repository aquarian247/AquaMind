# FishTalk -> AquaMind Model Audit Checklist

Purpose: resolve the FishTalk data-model meaning of Populations and lock the correct mapping to AquaMind Batch + Assignment + Workflow.

This is a focused data-model audit (not a migration run). Use CSV extracts under scripts/migration/data/extract/.

---

## Core hypothesis to test

1) **FishTalk Populations are not batches.** They are likely *instance segments* (container/time/stage slices) that roll up to a biological cohort.
2) **Batch identity is input-based.** `Ext_Inputs_v2` (InputName + InputNumber + YearClass) is the biological cohort.
3) **PublicStatusValues are snapshots.** They represent historical time-series states, not batch identity.

---

## Data sources (CSV extract)

Required:
- ext_inputs.csv
- populations.csv
- population_stages.csv
- production_stages.csv
- status_values.csv
- sub_transfers.csv
- population_links.csv

Optional (for validation):
- operation_stage_changes.csv
- feeding_actions.csv
- mortality_actions.csv

---

## Checklist (do in order)

### A) Global population context
- Count unique PopulationIDs in populations.csv.
- Count unique PopulationIDs in ext_inputs.csv.
- Calculate coverage: % of populations that have an Ext_Inputs_v2 record.
- Count unique input batches (InputName+InputNumber+YearClass) and average populations per input batch.

**Decision goal:** confirm Populations >> input batches, implying Populations are instances/segments.

**Status (2026-01-28):** Completed. See `model_audit_evidence_2026-01-28.md`.

### B) Single-batch deep dive (choose one input batch)
Use a known sea batch (e.g., InputName = V\u00e1r 2024, InputNumber=1, YearClass=2024).

For that batch:
- Populations per input batch (from ext_inputs.csv).
- Distinct containers (from populations.csv).
- Distinct project tuples (ProjectNumber/InputYear/RunningNumber) represented.
- Time span across population StartTime/EndTime.
- Stage entries per population (from population_stages.csv).
- Stage distribution (map StageID -> StageName using production_stages.csv).
- Status snapshots per population (from status_values.csv): min/max/avg counts.
- SubTransfers and PopulationLinks touching the population set.

**Decision goal:** show that many populations exist for one input batch, often each with a single stage and multiple containers/time windows; therefore population ~= segment, not batch.

**Status (2026-01-28):** Completed for **V\u00e1r 2024|1|2024** and **Heyst 2023|1|2023**. See evidence doc.

### B2) Second-batch repeatability check
- Repeat B) metrics for a different input batch to confirm the pattern is not batch-specific.

**Status (2026-01-28):** Completed for **Heyst 2023|1|2023**. See evidence doc.

### C) Lineage + workflow semantics
- Check whether SubTransfers link many populations within the batch set.
- Check whether OperationProductionStageChange provides stage transitions for the same population IDs.
- Decide whether lifecycle workflows should be derived from OperationProductionStageChange vs inferred from population_stages + assignments.

**Decision goal:** establish the authoritative lifecycle signals and limit inferred stage transitions.

**Status (2026-01-28):** SubTransfers/PopulationLinks confirmed per-batch. OperationProductionStageChange still needs a focused check if full lifecycle migration is planned.

### D) Mapping decision lock-in (document in DATA_MAPPING_DOCUMENT.md)
- Batch identity = Ext_Inputs_v2 (InputName + InputNumber + YearClass).
- BatchContainerAssignment = derived from populations + status snapshots (not from Populations alone).
- Transfers = SubTransfers (within environment) + OperationProductionStageChange for stage changes.
- Status snapshots = status_values.csv (time-series), do not treat as identity.

**Status (2026-01-28):** Locked in `DATA_MAPPING_DOCUMENT.md`.

### E) Migration readiness decision
- Sea-phase input batches can migrate using Ext_Inputs_v2 + Populations + Status snapshots + SubTransfers.
- Full lifecycle (FW\u2192Sea) requires explicit linking rules (PopulationLink + Ext_Populations_v2 parsing + heuristics) before migration.

### F) Domain invariants for projection readiness (do not violate)
- Mortality decreases population count over time; snapshots must reflect this (no upward jumps without transfers).
- Average weight and biomass increase over time (derived by TGC); avoid zero or missing weights where projections depend on them.
- Feed events require feed inventory to exist and be replenished (feed is dispersed, not batch-bound).
- Assignments must align with container history; projections require consistent container timelines.
- Lifecycle stages are 6 in AquaMind (Egg/Alevin, Fry, Parr, Smolt, Post-Smolt, Adult); newer Faroe data should roughly follow this progression, but older FishTalk data may be sparse.

### G) Context hygiene (avoid agent overreach)
- Use only CSV extracts under `scripts/migration/data/extract/` for evidence.
- Do not assume full lifecycle linkage unless explicitly proven for the batch.
- Keep decisions grounded in evidence + `DATA_MAPPING_DOCUMENT.md`.

---

## Output artifacts

1) Evidence summary for the chosen batch.
2) Short statement of what Population represents (entity vs instance).
3) Mapping decisions written into DATA_MAPPING_DOCUMENT.md.

---

## Acceptance criteria

- We can explain why Populations >> Batches using actual counts.
- A single input batch shows many populations across containers/time, with sparse stage entries and many status snapshots.
- Mapping rules are revised (if needed) and documented in DATA_MAPPING_DOCUMENT.md.
