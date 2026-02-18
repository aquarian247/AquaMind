# HANDOFF 2026-02-11 — PopulationLink / ActionMetaData Investigation (Revised)

## Origin
Independent read-only review (Opus 4.6) conducted under `READONLY_REVIEW_CHARTER_2026-02-11.md`. A full-schema search of all 614 FishTalk tables (3,888 columns from `FT_columns.xlsx`) identified three previously unexplored tables that are strong candidates for resolving **two** open problems:

- **Problem 1 (immediate):** External mixing boundary collapse — the `--external-mixing-status-multiplier` threshold problem in Stofnfiskur Juni 24 (and potentially other batches).
- **Problem 2 (strategic):** FW→Sea linkage — deterministic cross-environment batch identity for active (2023+) cohorts.

The same tables — particularly `PopulationLink` and `ActionMetaData` — are candidates for both. This plan executes external mixing investigation first because it is immediately actionable, validates the approach, and may change the FW→Sea strategy.

This revised version incorporates deterministic evidence generated later on 2026-02-11 (canary + bounded FW20 sweep), so next-agent decisions can start from verified outcomes rather than hypotheses.

## Status Update (Executed Evidence, 2026-02-11 plus 2026-02-12 follow-up)

| Evidence | Result | Migration Decision |
|----------|--------|--------------------|
| Stofnfiskur Juni 24 threshold canary (`10.0 -> 9.5`) | Fry stage-entry changed `196,889 -> 1,708,576`; other stages unchanged; gates stayed green | Keep as cohort-specific signal, not a global default change |
| FW20 bounded sensitivity sweep (4 additional high-drop cohorts, `10.0` vs `9.5`) | No differences in stage-entry, gates, or transition basis; all stayed PASS | Keep global default at `10.0`; use targeted override only with row-level evidence |
| FW20 endpoint gate matrix strict+tuned diagnostics (`min-candidate-rows=10,4,1`) | strict `1/20` PASS; tuned(4) `2/20` PASS; tuned(1) `2/20` PASS; only `Stofnfiskur sept 24` flipped on evidence-threshold boundary | Keep FW/Sea policy unlinked by default; use tuned profiles as diagnostics only |
| FW20 endpoint blocker provenance (`5` cohorts, `6` rows) | Blockers split cleanly into `direction_mismatch` (`3`) and `source_candidate_count_out_of_bounds` (`3`); SQL + CSV provenance aligned | Keep strict release gate and NO-GO policy; use blocker-family diagnostics to target next evidence step |
| FW20 endpoint source3 diagnostic (`max-source-candidates=3`) | strict `1/20` PASS -> source3 `2/20` PASS; added `Benchmark Gen. Septembur 2024` while evidence-relaxed profiles added a different cohort (`Stofnfiskur sept 24`) | Keep strict release gate and NO-GO policy; profile relaxations are non-generalizing diagnostics |
| FW20 endpoint combined diagnostic (`max-source-candidates=3`, `min-candidate-rows=4`) | strict `1/20` PASS -> combined `3/20` PASS; adds both previously profile-specific cohorts but leaves broad fail signal (`coverage` and `marine_target` each `16/20` fails) | Keep strict release gate and NO-GO policy; combined profile is diagnostic overlap mapping, not policy evidence |
| FW20 Part B high-signal FAIL follow-up (`source3 + min4` non-zero cohorts) | Non-zero candidate cohorts classified `7`: true FW->Sea candidates `4` (`3` full + `1` sparse), reverse-flow FW-only `3`; persistent high-signal FAIL set is exactly the reverse-flow family (`direction_mismatch`, `input_to_sales`, `fw->fw`) | GO for tooling-only blocker-family classification in acceptance reporting; NO-GO for global FW/Sea policy promotion and runtime changes |
| FW20 blocker-family classification integrated in matrix tooling (`strict` + `source3,min4`) | Tool now emits per-cohort deterministic blocker-family labels in JSON/TSV/MD (`reverse_flow_fw_only`, `true_fw_to_sea_candidate`, `true_fw_to_sea_sparse_evidence`, `unclassified_nonzero_candidate`) with strict `1/20` PASS and combined `3/20` PASS preserved | GO for tooling-only reporting enhancement; NO-GO for runtime changes and NO-GO for global FW/Sea policy promotion |
| FW20 reverse-flow trace-target prepack (`reverse_flow_fw_only`) | Built deterministic pre-trace pack for all persistent reverse-flow blockers (`3` rows, `6` operation IDs) with operation context signature: sales-side `OperationType=7` + Param220 presence vs component-side `OperationType=5` + Param184-only, all stage class `fw` | Keep reverse-flow family excluded from FW->Sea policy evidence; use published operation ID pack as direct input for local XE/Profiler capture |
| FW20 reverse-flow targeted SQL extract confirmation (`6` operation IDs) | Read-only source extract confirms stable pair signature across all blockers: Type7 + broad metadata palette (includes `220`) on sales side vs Type5 + no `220` on component side; all FW stage class | Keep reverse-flow blockers excluded from FW->Sea policy evidence; proceed to local XE/Profiler capture using published operation ID set |
| FW20 reverse-flow XE capture readiness (tooling + self-test) | Added XE lifecycle/analyze helper (`fwsea_xe_trace_capture.py`), validated local capture pipeline with ring-buffer self-test (`total_events=62`) and operation-id hit detection for all `6` target IDs; session can be armed for GUI trace runs | GO for local Activity Explorer trace capture against published operation ID set; no runtime or policy change |
| Runtime/UI behavior | Lifecycle chart behavior depends on migrated assignment materialization; no runtime FishTalk coupling introduced | Continue fixing in migration tooling/reporting only |

Evidence references:
- `aquamind/docs/progress/migration/analysis_reports/2026-02-11/stofnfiskur_juni24_external_mixing_threshold_canary_2026-02-11.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_external_mixing_sensitivity_sweep_2026-02-11.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_execution_2026-02-11.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_tuned_sparse_comparison_2026-02-11.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_tuned_sparse_min1_comparison_2026-02-11.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_blocker_operation_provenance_report_2026-02-11.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_comparison_2026-02-11.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw20_endpoint_gate_matrix_diag_source3_min4_comparison_2026-02-11.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_partb_high_signal_fail_cohort_followup_2026-02-12.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_nonzero_candidate_classification_2026-02-12.summary.json`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_blocker_family_tooling_integration_2026-02-12.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_fwsea_endpoint_gate_matrix_with_blocker_family_2026-02-12.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_fwsea_endpoint_gate_matrix_diag_source3_min4_with_blocker_family_2026-02-12.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_with_blocker_family_2026-02-12/fw20_endpoint_gate_matrix.summary.json`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_diag_source3_min4_with_blocker_family_2026-02-12/fw20_endpoint_gate_matrix.summary.json`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_trace_target_pack_2026-02-12.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_trace_target_pack_2026-02-12.tsv`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_trace_target_pack_2026-02-12.summary.json`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_targeted_sql_extract_signature_2026-02-12.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_xe_capture_readiness_2026-02-12.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_xe_capture_selftest_2026-02-12.summary.json`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_xe_session_status_2026-02-12.summary.json`
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-12_FWSEA_PARTB_HIGH_SIGNAL_FAIL_CLASSIFICATION.md`
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-11_FW20_EXTERNAL_MIXING_SENSITIVITY.md`

## Phase 0: Programmable Object Recon (Run Before Part A/B)

### Why this is now mandatory
Prior work has been table/view heavy. We have not yet systematically inspected SQL Server programmable objects (`stored procedures`, `functions`, `triggers`) in the FishTalk backup. For legacy fat-client systems, these objects often encode the business joins and parameter semantics we are currently inferring indirectly.

This phase is read-only and should be executed first against the local FT DB.

### What this phase can and cannot prove
- Can reveal deterministic join paths and parameter vocabularies if module definitions are readable.
- Can reveal that logic exists but is encrypted/unavailable (still valuable).
- Cannot prove application-layer behavior that never touches SQL module text.
- Does not justify runtime coupling; findings stay in migration tooling and reports.

### P0 Query Pack (Read-Only)

#### P0a. Inventory programmable object counts
```sql
SELECT type_desc, COUNT(*) AS cnt
FROM sys.objects
WHERE type IN ('P','FN','IF','TF','TR','V','FS','FT')
GROUP BY type_desc
ORDER BY cnt DESC
```

#### P0b. Module readability and size
```sql
SELECT o.type_desc,
       o.name,
       o.create_date,
       o.modify_date,
       CASE WHEN m.definition IS NULL THEN 'ENCRYPTED_OR_UNAVAILABLE' ELSE 'READABLE' END AS definition_status,
       LEN(m.definition) AS definition_length
FROM sys.objects o
LEFT JOIN sys.sql_modules m ON m.object_id = o.object_id
WHERE o.type IN ('P','FN','IF','TF','TR','V','FS','FT')
ORDER BY o.type_desc, o.name
```

#### P0c. Keyword sweep across readable modules
Run once per term:
- `TransportCarrier`
- `InternalDelivery`
- `PopulationLink`
- `ActionMetaData`
- `ParameterID`
- `LinkType`
- `ProductionStage`
- `Ext_Transfers`
- `PublicTransfers`

```sql
DECLARE @term nvarchar(100) = N'TransportCarrier';

SELECT o.type_desc,
       o.name,
       LEFT(REPLACE(REPLACE(
            SUBSTRING(
                m.definition,
                CASE WHEN CHARINDEX(@term, m.definition) > 80 THEN CHARINDEX(@term, m.definition) - 80 ELSE 1 END,
                240
            ),
            CHAR(10), ' '
       ), CHAR(13), ' '), 240) AS context_snippet
FROM sys.objects o
JOIN sys.sql_modules m ON m.object_id = o.object_id
WHERE o.type IN ('P','FN','IF','TF','TR','V','FS','FT')
  AND m.definition LIKE '%' + @term + '%'
ORDER BY o.type_desc, o.name
```

#### P0d. View encryption/readability audit
```sql
SELECT v.name,
       OBJECTPROPERTY(v.object_id, 'IsEncrypted') AS is_encrypted,
       CASE WHEN m.definition IS NULL THEN 'NO_DEFINITION_TEXT'
            ELSE CAST(LEN(m.definition) AS varchar(32)) + ' chars'
       END AS definition_status
FROM sys.views v
LEFT JOIN sys.sql_modules m ON m.object_id = v.object_id
ORDER BY v.name
```

#### P0e. Trigger inventory and readability
```sql
SELECT t.name,
       OBJECT_SCHEMA_NAME(t.parent_id) + '.' + OBJECT_NAME(t.parent_id) AS parent_table,
       t.is_disabled,
       CASE WHEN m.definition IS NULL THEN 'ENCRYPTED_OR_UNAVAILABLE' ELSE 'READABLE' END AS definition_status,
       LEN(m.definition) AS definition_length
FROM sys.triggers t
LEFT JOIN sys.sql_modules m ON m.object_id = t.object_id
ORDER BY parent_table, t.name
```

#### P0f. Optional dependency cross-check for transfer surfaces
```sql
SELECT DISTINCT
       referencing_schema_name = OBJECT_SCHEMA_NAME(d.referencing_id),
       referencing_object_name = OBJECT_NAME(d.referencing_id),
       referencing_type_desc = o.type_desc,
       referenced_schema_name = d.referenced_schema_name,
       referenced_entity_name = d.referenced_entity_name
FROM sys.sql_expression_dependencies d
JOIN sys.objects o ON o.object_id = d.referencing_id
WHERE d.referenced_entity_name IN ('PopulationLink', 'ActionMetaData', 'InternalDelivery', 'Ext_Transfers_v2', 'PublicTransfers')
ORDER BY referencing_type_desc, referencing_object_name
```

### Phase 0 Decision Gate
1. If readable modules contain deterministic parameter decoding or explicit FW->Sea/cross-boundary join paths, prioritize module-derived interpretation before additional heuristic table analysis.
2. If module hits exist but are partial/ambiguous, continue with Part A/B table queries and label confidence as medium.
3. If modules are encrypted/unavailable or no relevant hits, proceed with Part A/B as primary and keep profiler/decompilation escalation ready.

---

## Part A: External Mixing Boundary Investigation

### Background: The Head-Scratcher

The Stofnfiskur Juni 24 batch (component `EDF931F2-51CC-4A10-9002-128E7BF8067C`, station S03 Nordtoftir) has **131 outside-component SubTransfer edges** and shows this signature at the Fry stage:

| Metric | Value |
|--------|-------|
| Fry entry populations | 12 (all in hall `5 M Høll`) |
| Conserved count per population | ~14,765 |
| Status snapshot count per population | ~142,381 |
| Ratio (status / conserved) | ~9.64x |
| External mixing flag | all `True` |

With `--external-mixing-status-multiplier 10.0` (default), the 9.64x ratio doesn't trigger, so conserved counts are used → Fry entry = 196,889.
With `9.5`, the ratio triggers, status counts are used → Fry entry = 1,708,576.

Parr, Smolt, and Post-Smolt are unaffected. No other tested FW20 batch shows this sensitivity (4-batch sweep confirmed identical results at 10.0 vs 9.5).

### What the Numbers Tell Us

~90% of the fish in those 12 Fry containers came from **outside the component boundary**. The conserved count tracks only the ~10% flowing through the internal SubTransfer chain. The status snapshot captures the total container population from all sources.

This means:
- The component boundary (`InputName|InputNumber|YearClass = Stofnfiskur Juni 24|2|2024`) is **too narrow** to capture the full biological reality of those Fry containers.
- Other InputProjects contribute fish to the same physical containers.
- The multiplier threshold is a symptom treatment. The root cause is component boundary definition.

### Cross-Cutting Pattern Across Today's Handoffs

Component boundary behavior is a dominant issue, but not the only active class of migration risk. Keep these buckets separate:

| Bucket | Confirmed? | Typical Signature | Current Confidence |
|--------|------------|-------------------|--------------------|
| External boundary mixing | Yes (Stofnfiskur Juni 24) | near-threshold status/conserved ratio, large stage-entry divergence under multiplier change | High |
| Linkage closure gaps | Yes (multiple FW20 cohorts) | `incomplete_linkage`, `entry_population_external_source_count > 0` | High |
| Stage mapping coverage gaps | Yes (site-dependent) | hall fallback and site mapping dependence | Medium |
| FW→Sea identity linkage absence | Yes | `link_pending` for active cohorts, no deterministic transfer edge | High |

Do not collapse all findings into one root-cause statement. The above buckets interact, but they should be diagnosed and remediated independently.

### Discovery: Three Candidate Tables

#### Candidate 1: `PopulationLink` — 20,070 rows (TOP PRIORITY)

```
PopulationLink:
  FromPopulationID   uniqueidentifier
  ToPopulationID     uniqueidentifier
  OperationID        uniqueidentifier
  LinkType           int
```

- Explicitly links populations to each other with a typed relationship.
- If any `LinkType` represents "shared container" or "batch mixing" or "delivery", this IS the missing cross-boundary edge information.
- 20,070 rows is substantial — not a dead table.
- The `OperationID` ties each link to a traceable operation.
- **Never been extracted or analyzed** in any prior investigation.

#### Candidate 2: `ActionMetaData` — 5,883,811 rows (HIGH PRIORITY)

```
ActionMetaData:
  ActionID        uniqueidentifier   → FK to Action.ActionID
  ParameterID     int                → type of metadata
  ParameterValue  float
  ParameterString nvarchar
  ParameterDate   datetime
  ParameterGuid   uniqueidentifier   → could store TransportCarrierID, source batch refs, etc.
```

- Classic EAV (Entity-Attribute-Value) pattern — the application stores extensible metadata here.
- Join path: `InternalDelivery.SalesOperationID` → `Operations.OperationID` → `Action.OperationID` → `ActionMetaData.ActionID`.
- Also reachable from: `SubTransfers.OperationID` → `Action.OperationID` → `ActionMetaData.ActionID`.
- Could reveal the operational context of cross-boundary SubTransfer edges (planned redistribution? batch mixing? delivery?).
- Parallel table `PlanActionMetaData` (5.3M rows) has identical schema.

#### Candidate 3: `OperationProductionStageChange` — 25,015 rows (MEDIUM PRIORITY)

```
OperationProductionStageChange:
  OperationID     uniqueidentifier
  PPSPopID        uniqueidentifier
  PPSStageID      uniqueidentifier   → likely references ProductionStages.StageID
  PPSStartTime    datetime
```

- Records when operations cause production stage changes for populations.
- Cross-referencing with SubTransfer `OperationID` values could reveal whether cross-boundary edges involve stage transitions.

#### Supporting Context

- `FishGroupAttributes.CarryOverThroughInternalDelivery` (boolean column) confirms internal delivery is a first-class domain concept with attribute-carryover semantics in FishTalk.
- Full column-level search of all 614 tables confirmed: **zero columns** contain "Trip", "Voyage", or "Compartment" anywhere in the database. Transport metadata (if stored) uses the EAV pattern in `ActionMetaData`, not dedicated columns.
- `TransportCarrierID` FK appears only in Feed/Harvest tables — never in any transfer/delivery/operation table.

### Phase A1: External Mixing Enumeration Queries (30 min)

Run these against the FishTalk SQL Server backup. Each query is independent.

#### A1a. PopulationLink — Full Type Enumeration
```sql
-- What link types exist and their volumes?
SELECT LinkType, COUNT(*) AS cnt
FROM PopulationLink
GROUP BY LinkType
ORDER BY cnt DESC
```

```sql
-- Sample rows for each link type
SELECT *
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY LinkType ORDER BY OperationID) AS rn
    FROM PopulationLink
) x
WHERE rn <= 5
```

#### A1b. PopulationLink — Stofnfiskur Juni 24 Specific
Use the 12 known Fry population IDs from the component's `population_members.csv` (or query them from `ExternalIdMap`). Also use the 131 outside-component edge population IDs from SubTransfers.

```sql
-- Do PopulationLink rows connect Stofnfiskur Juni 24 populations to outside populations?
-- First, get component population IDs from Ext_Inputs_v2 or the migration's ExternalIdMap
-- Then:
SELECT pl.*
FROM PopulationLink pl
WHERE pl.FromPopulationID IN (<component_population_ids>)
   OR pl.ToPopulationID IN (<component_population_ids>)
ORDER BY pl.LinkType
```

```sql
-- Which InputProjects do the linked outside populations belong to?
WITH outside_links AS (
    SELECT pl.OperationID, pl.LinkType, outside_pop_id = pl.FromPopulationID
    FROM PopulationLink pl
    WHERE pl.ToPopulationID IN (<component_pop_ids>)
      AND pl.FromPopulationID NOT IN (<component_pop_ids>)
    UNION ALL
    SELECT pl.OperationID, pl.LinkType, outside_pop_id = pl.ToPopulationID
    FROM PopulationLink pl
    WHERE pl.FromPopulationID IN (<component_pop_ids>)
      AND pl.ToPopulationID NOT IN (<component_pop_ids>)
),
outside_links_dedup AS (
    SELECT DISTINCT OperationID, LinkType, outside_pop_id
    FROM outside_links
)
SELECT ip.ProjectName, ip.SiteID, ip.YearClass, ol.LinkType,
       COUNT(DISTINCT ol.outside_pop_id) AS linked_outside_pop_count
FROM outside_links_dedup ol
LEFT JOIN FishGroupHistory fgh ON fgh.PopulationID = ol.outside_pop_id
LEFT JOIN InputProjects ip ON ip.InputProjectID = fgh.InputProjectID
GROUP BY ip.ProjectName, ip.SiteID, ip.YearClass, ol.LinkType
ORDER BY linked_outside_pop_count DESC
```

Note: if `FishGroupHistory` has multiple rows per `PopulationID`, this join can fan out. In that case, switch to `OUTER APPLY (SELECT TOP 1 ...)` with a deterministic temporal sort column in your backup.

#### A1c. Outside Population Identity — Who Are the Other Batches?
```sql
-- From SubTransfers, identify outside populations touching the 12 Fry populations
-- Then resolve their InputProject identity
SELECT DISTINCT
    outside_pop.pop_id AS outside_pop_id,
    ip.ProjectName AS outside_batch,
    ip.SiteID AS outside_site,
    ep.ContainerID,
    ep.StartTime, ep.EndTime,
    ep.Fishgroup
FROM SubTransfers st
CROSS APPLY (VALUES
    (st.SourcePopBefore),
    (st.SourcePopAfter),
    (st.DestPopBefore),
    (st.DestPopAfter)
) outside_pop(pop_id)
JOIN Ext_Populations_v2 ep ON ep.PopulationID = outside_pop.pop_id
LEFT JOIN FishGroupHistory fgh ON fgh.PopulationID = outside_pop.pop_id
LEFT JOIN InputProjects ip ON ip.InputProjectID = fgh.InputProjectID
WHERE (st.SourcePopBefore IN (<12_fry_pop_ids>) 
    OR st.SourcePopAfter IN (<12_fry_pop_ids>)
    OR st.DestPopBefore IN (<12_fry_pop_ids>)
    OR st.DestPopAfter IN (<12_fry_pop_ids>))
  AND outside_pop.pop_id IS NOT NULL
  AND outside_pop.pop_id NOT IN (<component_pop_ids>)
ORDER BY ip.ProjectName, ep.StartTime
```

#### A1d. ActionMetaData for Cross-Boundary Operations
```sql
-- What ActionMetaData exists for the 131 outside-component SubTransfer operations?
WITH cross_boundary_ops AS (
    SELECT DISTINCT st.OperationID
    FROM SubTransfers st
    WHERE (
            st.SourcePopBefore IN (<component_pop_ids>)
         OR st.SourcePopAfter IN (<component_pop_ids>)
         OR st.DestPopBefore IN (<component_pop_ids>)
         OR st.DestPopAfter IN (<component_pop_ids>)
    )
      AND (
            (st.SourcePopBefore IS NOT NULL AND st.SourcePopBefore NOT IN (<component_pop_ids>))
         OR (st.SourcePopAfter  IS NOT NULL AND st.SourcePopAfter  NOT IN (<component_pop_ids>))
         OR (st.DestPopBefore   IS NOT NULL AND st.DestPopBefore   NOT IN (<component_pop_ids>))
         OR (st.DestPopAfter    IS NOT NULL AND st.DestPopAfter    NOT IN (<component_pop_ids>))
    )
)
SELECT cbo.OperationID, o.OperationType, o.StartTime,
       a.ActionType, a.ActionID,
       amd.ParameterID, amd.ParameterValue, amd.ParameterString,
       amd.ParameterDate, amd.ParameterGuid
FROM cross_boundary_ops cbo
JOIN Operations o ON o.OperationID = cbo.OperationID
JOIN Action a ON a.OperationID = o.OperationID
LEFT JOIN ActionMetaData amd ON amd.ActionID = a.ActionID
ORDER BY o.StartTime, amd.ParameterID
```

#### A1e. OperationProductionStageChange for Cross-Boundary Ops
```sql
-- Do any cross-boundary operations trigger stage changes?
SELECT opsc.*, ps.StageName
FROM OperationProductionStageChange opsc
JOIN ProductionStages ps ON ps.StageID = opsc.PPSStageID
WHERE opsc.OperationID IN (
    SELECT DISTINCT st.OperationID 
    FROM SubTransfers st
    WHERE (st.SourcePopBefore IN (<12_fry_pop_ids>) 
        OR st.SourcePopAfter IN (<12_fry_pop_ids>)
        OR st.DestPopBefore IN (<12_fry_pop_ids>)
        OR st.DestPopAfter IN (<12_fry_pop_ids>))
      AND (
            (st.SourcePopBefore IS NOT NULL AND st.SourcePopBefore NOT IN (<component_pop_ids>))
         OR (st.SourcePopAfter  IS NOT NULL AND st.SourcePopAfter  NOT IN (<component_pop_ids>))
         OR (st.DestPopBefore   IS NOT NULL AND st.DestPopBefore   NOT IN (<component_pop_ids>))
         OR (st.DestPopAfter    IS NOT NULL AND st.DestPopAfter    NOT IN (<component_pop_ids>))
      )
)
```

### Phase A2: Follow-Up Based on Phase A1 Results (1-2 hours)

#### If PopulationLink connects Stofnfiskur Juni 24 to other batches:
1. Identify ALL InputProjects that contribute to the shared Fry containers.
2. Quantify the contribution from each (fish counts via status snapshots at shared container time).
3. Assess whether widening the component boundary to include contributing batches would make conservation work.
4. Alternatively, assess whether AquaMind's `BatchComposition` model (explicit mixed-batch parentage with percentage contributions) is the correct migration target.
5. Check if the same pattern applies to the `Fry→Parr` transition (which has `incomplete_linkage` / `entry_population_external_source_count = 2`).

#### If ActionMetaData reveals operational context:
1. Decode the `ParameterID` vocabulary for cross-boundary operations.
2. Determine if these are planned redistributions vs accidental mixing.
3. If there's a "source batch" parameter, that directly supports BatchComposition migration.

#### If the pattern generalizes beyond Stofnfiskur Juni 24:
1. Run the same PopulationLink query for the other batches that have `incomplete_linkage` warnings in the FW20 cohort.
2. Determine how many batches share this cross-InputProject mixing pattern.
3. This informs whether the fix should be batch-specific or architectural.

### Phase A3: Determine the Right Migration Strategy (Evidence-Gated)

Hard guardrails from executed 2026-02-11 evidence:
- Keep global default `--external-mixing-status-multiplier` at `10.0` unless a broader cohort set shows deterministic net benefit.
- Do not auto-prefer status count solely because cross-boundary mixing exists; that can overcount shared-container populations.
- Do not widen component boundaries globally without quantified blast-radius analysis.

Decision gates before approving any policy change:
1. Semantic gates remain PASS across canary cohort set.
2. `non_bridge_zero_assignments` stays `0`.
3. Transition basis/reason moves toward deterministic evidence (not more `incomplete_linkage` or opaque fallbacks).
4. Operational count fidelity (feeding, mortality, culling, escapes, growth) remains unchanged.
5. Every comparative run includes DB wipe and published before/after deltas.

Based on Phase A1/A2 results, one of these approaches should emerge:

**Option A: Targeted boundary widening pilot.** Include contributing InputProjects for one or two representative cohorts only, then re-run gates and count deltas. Treat as experiment, not default.

**Option B: Use BatchComposition.** Keep current component boundaries but explicitly record external contributions using AquaMind's `batch_batchcomposition` model (source batches, percentages, counts). This is semantically richer and aligns with native mixed-batch representation.

**Option C: Evidence-scoped status preference.** Consider status preference only when all are true: (a) deterministic cross-batch linkage evidence exists, (b) ratio/coverage checks indicate conserved-count underrepresentation, and (c) cohort-level gates remain stable.

**Option D: Negative result.** If `PopulationLink`/`ActionMetaData` do not provide deterministic linkage context, keep current threshold policy (`10.0` default + targeted override only where row-level evidence supports it), document uncertainty, and continue.

---

## Part B: FW→Sea Linkage Investigation

### Background: Why FW→Sea Linkage Is Missing

The migration has no deterministic way to link freshwater batches to their sea-phase successors for any cohort active since 2023. The current backup (2026-01-22) contains only 283 FW→Marine `SubTransfer` edges, all from 2010–2014. All active batches are replayed as independent FW or Sea components with `link_pending` metadata.

### What We Already Know Doesn't Work
- `SubTransfers`: No FW→Sea edges for 2023+ cohorts.
- `PublicTransfers`: Broken since Jan 2023.
- `InternalDelivery` (2,822 rows): Has `SalesOperationID`, `InputSiteID`, `InputOperationID`, `PlannedActivityID`. Investigated Jan 30 — does **not** directly link FW→Sea for S16/S24/S21. `InputOperationID` is consistently NULL. No FK to `TransportCarrier`.
- `Ext_Inputs_v2.Transporter`: All NULL in the 2026-01-22 extract.
- `TransportCarrier` (41 rows, e.g. "Tangi 3"): Exists, but FK references appear **only** in Feed/Harvest tables — not in any transfer/delivery/operation table.
- `Ext_Transfers_v2`: View definition unreadable (encrypted or permission-blocked via `sp_helptext` and `sys.sql_modules`).
- Name-based FW→Sea candidate matching: Heuristic only (non-canonical, review-only flag).

### Key Schema Discovery: No Trip/Voyage/Compartment Tables Exist
A full column-level search of all 614 tables confirmed: **zero columns** in the entire database contain "Trip", "Voyage", or "Compartment". The transport metadata the Activity Explorer GUI displays is not stored in dedicated transport-detail tables.

### Why ActionMetaData Is the Prime Suspect for Transport Data

The reasoning chain:
1. The Activity Explorer GUI **does** display carrier/trip/compartment for FW→Sea operations.
2. No dedicated Trip/Voyage/Compartment table or column exists anywhere in 614 tables.
3. `TransportCarrier` exists (41 rows) but has no FK from any transfer/delivery table.
4. `ActionMetaData` is a 5.8M-row EAV table with a `ParameterGuid` column — the natural place to store a `TransportCarrierID` reference without a formal FK.
5. The join path `InternalDelivery → Operations → Action → ActionMetaData` is structurally valid.
6. `FishGroupAttributes.CarryOverThroughInternalDelivery` confirms internal delivery has rich application-layer semantics.

Important uncertainty label:
- `ActionMetaData` is currently a best hypothesis, not established fact for FW→Sea linkage.
- If B1a/B1b fail to produce deterministic carrier/trip/compartment mapping, do not force heuristic joins into migration runtime.
- In that case, escalate to profiler/decompilation evidence and keep FW/Sea unlinked unless explicit deterministic linkage is proven.

### Phase B1: FW→Sea Enumeration Queries (30 min)

Run these after Phase 0. Once Phase 0 is complete, B1 can run in parallel with A1. Several checks overlap with Phase 0 outputs (module keyword hits, view readability).

#### B1a. ActionMetaData — "Smoking Gun" Test
```sql
-- Does ActionMetaData store TransportCarrierID references?
SELECT amd.ParameterID, COUNT(*) AS match_count
FROM ActionMetaData amd
WHERE amd.ParameterGuid IN (SELECT ID FROM TransportCarrier)
GROUP BY amd.ParameterID
ORDER BY match_count DESC
```

If this returns results, `ParameterID` tells you which parameter code means "TransportCarrier". Then:

```sql
-- What other ParameterIDs appear alongside the carrier parameter on the same ActionID?
SELECT amd2.ParameterID, 
       COUNT(*) AS co_occurrence,
       MAX(amd2.ParameterString) AS sample_string,
       MAX(amd2.ParameterValue) AS sample_value
FROM ActionMetaData amd
JOIN ActionMetaData amd2 ON amd.ActionID = amd2.ActionID
WHERE amd.ParameterGuid IN (SELECT ID FROM TransportCarrier)
  AND amd2.ParameterID != amd.ParameterID
GROUP BY amd2.ParameterID
ORDER BY co_occurrence DESC
```

#### B1b. ActionMetaData — InternalDelivery Join Path
```sql
-- What ActionMetaData exists for InternalDelivery-linked operations?
SELECT TOP 100
       id.SalesOperationID,
       id.InputSiteID,
       id.InputOperationID,
       o.OperationType,
       o.StartTime,
       a.ActionID,
       a.ActionType,
       amd.ParameterID,
       amd.ParameterValue,
       amd.ParameterString,
       amd.ParameterDate,
       amd.ParameterGuid
FROM InternalDelivery id
JOIN Operations o ON o.OperationID = id.SalesOperationID
JOIN Action a ON a.OperationID = o.OperationID
LEFT JOIN ActionMetaData amd ON amd.ActionID = a.ActionID
ORDER BY o.StartTime DESC
```

#### B1c. PopulationLink — Cross-Environment Check
```sql
-- Do any PopulationLink rows cross ProdStage boundaries (FW → Marine)?
-- This requires joining through Populations → Containers → Ext_GroupedOrganisation_v2
-- Adjust the join path based on available columns:
SELECT pl.LinkType,
       src_org.ProdStage AS from_prod_stage,
       dst_org.ProdStage AS to_prod_stage,
       COUNT(*) AS cnt
FROM PopulationLink pl
JOIN Ext_Populations_v2 src ON src.PopulationID = pl.FromPopulationID
JOIN Ext_GroupedOrganisation_v2 src_org ON src_org.ContainerID = src.ContainerID
JOIN Ext_Populations_v2 dst ON dst.PopulationID = pl.ToPopulationID
JOIN Ext_GroupedOrganisation_v2 dst_org ON dst_org.ContainerID = dst.ContainerID
GROUP BY pl.LinkType, src_org.ProdStage, dst_org.ProdStage
ORDER BY pl.LinkType
```

Note: The exact join path may need adjustment depending on how `Ext_GroupedOrganisation_v2` keys its rows (ContainerID vs OrgUnitID). Try both if the first fails.

#### B1d. OperationProductionStageChange — Stage Mapping
```sql
-- What stages exist in ProductionStages?
SELECT * FROM ProductionStages ORDER BY StageOrder

-- Do any stage changes co-occur with InternalDelivery operations?
SELECT opsc.*, ps.StageName, id.InputSiteID
FROM OperationProductionStageChange opsc
JOIN ProductionStages ps ON ps.StageID = opsc.PPSStageID
JOIN InternalDelivery id ON id.SalesOperationID = opsc.OperationID
```

#### B1e. Ext_Transfers_v2 View Encryption Check (skip if P0d already captured)
```sql
-- Is the view encrypted? (targeted reconfirmation)
SELECT name, 
       OBJECTPROPERTY(object_id, 'IsEncrypted') AS is_encrypted,
       type_desc
FROM sys.views 
WHERE name = 'Ext_Transfers_v2'

-- Alternative view definition methods
SELECT VIEW_DEFINITION 
FROM INFORMATION_SCHEMA.VIEWS 
WHERE TABLE_NAME = 'Ext_Transfers_v2'

-- Check for synonyms
SELECT name, base_object_name 
FROM sys.synonyms 
WHERE name LIKE '%Transfer%'

-- Check all objects with Transfer in name
SELECT name, type_desc 
FROM sys.objects 
WHERE name LIKE '%Transfer%' 
ORDER BY name
```

#### B1f. Second Database Check
```sql
-- Are there other databases on this SQL Server instance?
SELECT name FROM sys.databases 
WHERE name NOT IN ('master','tempdb','model','msdb')
```

### Phase B2: Follow-Up Based on Phase B1 Results (1-2 hours)

#### If ActionMetaData contains TransportCarrierID matches:
1. Identify the full ParameterID vocabulary:
   ```sql
   SELECT ParameterID, COUNT(*) AS cnt,
          MAX(ParameterString) AS sample_string,
          MAX(CAST(ParameterGuid AS varchar(36))) AS sample_guid
   FROM ActionMetaData
   GROUP BY ParameterID
   ORDER BY cnt DESC
   ```
2. Extract all ActionMetaData rows for InternalDelivery-linked operations.
3. Cross-reference `ParameterGuid` values against `TransportCarrier.ID` to identify carrier assignments per delivery.
4. Look for ParameterID codes that store trip/compartment strings alongside carrier GUIDs.
5. Determine which InternalDelivery rows have complete transport metadata vs. incomplete.

#### If PopulationLink contains cross-environment links:
1. Extract all PopulationLink rows with the relevant LinkType.
2. For each link, resolve both populations to their InputProject/batch context via `FishGroupHistory` → `InputProjects`.
3. Determine if this provides FW→Sea batch-level linkage.
4. Assess coverage: how many active (2023+) batches have PopulationLink-based cross-environment edges?
5. Compare against InternalDelivery rows for consistency.

#### If OperationProductionStageChange links to InternalDelivery:
1. Map operations that trigger FW→Marine stage changes.
2. Trace the populations to their batch identity.

### Phase B3: CSV Extraction and Migration Integration (if evidence found)

If Phase B1/B2 confirms linkage data exists:

1. **Extract CSVs:**
   - `PopulationLink` — all 20,070 rows.
   - `ActionMetaData` — filtered to only InternalDelivery-linked ActionIDs (not the full 5.8M).
   - `OperationProductionStageChange` — all 25,015 rows.
   - `ProductionStages` — all rows (small reference table).
   
2. **Add to `bulk_extract_fishtalk.py`.**

3. **Update `DATA_MAPPING_DOCUMENT.md`** with discovered join paths and entity mappings.

4. **Assess migration impact** and propose integration approach.

---

## Additional Context from Independent Review

### Review Charter Findings (Summary)

The full review (conducted under `READONLY_REVIEW_CHARTER_2026-02-11.md`) assessed the migration across six angles:

1. **Operational data migration is excellent:** Perfect count fidelity across all 20 tested FW batches. Zero-diff on feeding, mortality, culling, escapes, harvest, treatments, growth samples, lice. Gate pass rate: 100% (24/24 Faroe FW <30m).

2. **FW→Sea linkage is the single largest remaining gap.** Source-data availability issue, not a tooling bug.

3. **The migration relies on opaque FishTalk application-layer views** (`Ext_*`, `Public*`). The `ActionMetaData` EAV pattern is consistent with this — FishTalk stores extensible data in generic tables only the application interprets.

4. **Stage resolution depends on hardcoded hall mappings** for ~71% of populations. Scotland sites (FW13, FW21, FW23) have no mappings. Separate risk from linkage but compounds generalization.

5. **Sea-phase batches are essentially untested.** Only 2 sea batches attempted; both initially failed gates. Dedicated sea-phase pilot recommended.

6. **The core question** ("converging on correct migration vs compensating for deeper mismatch?") — answer: converging on correctness for single-phase FW, but compensating for structural gaps at boundaries. This investigation directly attacks those boundary gaps.

### Post-Draft Calibration (Verified Same Day)

1. Stofnfiskur Juni 24 is confirmed as a threshold-sensitive outlier at `9.64x` status/conserved ratio for Fry entry populations.
2. A bounded 4-batch FW20 sweep showed zero impact from `10.0 -> 9.5`; therefore, no evidence supports lowering global default.
3. Next-agent default stance: keep multiplier at `10.0`, apply targeted overrides only with row-level evidence and published before/after deltas.
4. Continue treating lifecycle discrepancies as migration-materialization evidence first; runtime code remains FishTalk-agnostic.

## SQL Server Profiler Recommendation

If Phase 0 + Phase A/B do not fully resolve linkage questions on the local FT DB instance, the highest-value next step is SQL tracing (**Extended Events** preferred; Profiler acceptable if that is what is available):

1. Open SSMS (or equivalent SQL tooling) against the same local SQL Server instance hosting the FT backup.
2. Start a trace/session filtering for `SQL:BatchCompleted` and `RPC:Completed` (or their XE equivalents).
3. In the FishTalk GUI, navigate to the Activity Explorer and open a known FW→Sea transfer or a known cross-batch mixing operation.
4. Capture all SQL statements — this reveals exactly which tables and joins the application uses.

Also worth checking on the file system:
- FishTalk installation directory (`C:\Program Files\FishTalk\` or similar) for `.config`, `.xml`, `.dll` files.
- If .NET DLLs are found, they can be decompiled with ILSpy/dnSpy to inspect query logic.

## Success Criteria

### Phase 0 (Programmable Objects)
- **Full success:** Readable module code yields deterministic mapping clues (e.g., `ParameterID`/`LinkType` interpretation or explicit FW→Sea join path).
- **Partial success:** Relevant modules found but semantics remain ambiguous.
- **Negative result (still valuable):** Objects are encrypted/unavailable or no relevant references found; proceed with table-level evidence path and uncertainty label.

### Part A (External Mixing)
- **Full success:** Discover deterministic cross-batch population linkage for Stofnfiskur Juni 24 Fry containers, enabling principled count resolution (replacing arbitrary multiplier).
- **Partial success:** Identify the contributing batches but without sufficient link metadata for automatic resolution.
- **Negative result (still valuable):** Confirm PopulationLink doesn't cover this case, validating that the multiplier approach is the best available option.

### Part B (FW→Sea)
- **Full success:** Discover deterministic FW→Sea population linkage with sufficient coverage for active (2023+) cohorts.
- **Partial success:** Discover the mechanism but with incomplete coverage.
- **Negative result (still valuable):** Confirm none of these tables contain FW→Sea linkage, narrowing to application-code-only logic or newer backup requirement.

## Safety Notes

- All queries are **read-only** against the FishTalk backup.
- Do not modify any AquaMind runtime code based on these findings — follow the runtime separation principle.
- Document all findings in `analysis_reports/` with date prefix.
- If linkage evidence is found, propose integration as a new migration tooling module, not as changes to existing scripts.
