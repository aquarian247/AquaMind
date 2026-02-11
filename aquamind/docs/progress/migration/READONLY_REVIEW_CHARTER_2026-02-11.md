# Readonly Review Charter: FishTalk -> AquaMind Migration (2026-02-11)

## Purpose
Provide an independent, read-only technical review of the migration program with emphasis on:
- correctness,
- robustness across cohorts,
- hidden assumptions,
- possible FishTalk/AquaMind model incompatibilities,
- and whether observed behavior could depend on application logic not visible in the raw database.

This charter is intentionally open-ended. The reviewer should challenge current assumptions and propose alternatives when warranted by evidence.

## Reviewer Mode
- Read-only investigation.
- Do not edit code, data, scripts, or documents.
- Deliver analysis, risk assessment, and recommendation options.

## Context
Migration has progressed from single-batch validation to broader cohort checks, with tooling-only improvements for stage resolution and transition linkage. Some issues are resolved, but confidence still depends on broader replay evidence and deeper understanding of FishTalk semantics.

## Core Questions (open-ended)
1. Are we mapping source semantics correctly, or merely matching expected outputs for known batches?
2. Which migration rules are truly deterministic vs currently heuristic?
3. Could FishTalk application-layer logic (views, stored procedures, business services, UI transformations) be adding meaning not obvious in exported tables?
4. Are FishTalk and AquaMind data models fundamentally compatible for lifecycle/history semantics, or is partial mismatch unavoidable?
5. If incompatibility exists, what mitigation patterns are realistic (for example: explicit uncertainty states, manual linkage workflows, post-import reconciliation tools)?

## Required Review Angles

### 1) Data-Model Compatibility
Assess conceptual fit between FishTalk and AquaMind for:
- lifecycle stages,
- population identity continuity,
- transfer lineage,
- snapshot vs event semantics,
- historical reconstruction.

Focus on whether discrepancies are implementation bugs or structural model differences.

### 2) Source-of-Truth Boundaries
Evaluate where truth appears to come from in practice:
- raw base tables,
- derived views,
- export transformations,
- inferred hall/stage mappings,
- replay-time conservation logic.

Call out any places where “truth” may actually be a computed convention rather than an intrinsic field.

### 3) Transition Linkage Integrity
Independently judge whether bridge-aware vs entry-window fallback decisions are:
- deterministic,
- reproducible,
- and biologically/plausibly constrained.

Highlight cases where linkage quality cannot be proven with current evidence.

### 4) Population and Biomass Semantics
Investigate the risk that count/biomass reconstruction may be mathematically consistent but semantically misleading.
Examples:
- temporary bridge populations,
- superseded same-stage segments,
- missing biomass in source but derived biomass in target,
- stage progression inflation due aggregation method differences.

### 5) Operational Behavior Not Captured in DB
Probe whether significant business logic likely lives outside visible DB records:
- application services,
- scheduling jobs,
- internal calculations,
- or UI-level representations.

If likely, identify concrete evidence needed to confirm or refute.

### 6) Generalization Risk
Assess whether current migration behavior is likely to generalize across:
- Faroe FW batches < 30 months,
- Scotland FW,
- sea-based cohorts.

Differentiate “works on validated cases” from “expected to generalize safely.”

## Suggested Evidence Set (not exhaustive)
- Program docs:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/MIGRATION_CANONICAL.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/MIGRATION_BEST_PRACTICES.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/FISHTALK_SCHEMA_ANALYSIS.md`
- Latest handoffs:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-10_RUNTIME_SEPARATION.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-11_FW20_REMEDIATION.md`
- Current tooling:
  - `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component.py`
  - `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_input_batch.py`
  - `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py`
- Representative reports across dates and cohorts under:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/`
- Key AquaMind d:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/database/data_model.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/prd.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/architecture.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/user_guides/planning_and_workflows_primer.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/user_guides/live_forward_projection_guide.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/user_guides/production_planning_guide.md`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/user_guides/TRANSFER_WORKFLOW_FINANCE_GUIDE.md`

Reviewer may expand this evidence set as needed.

## Deliverable Format
Produce one report with these sections:
1. Executive assessment.
2. High-confidence findings (ordered by severity).
3. Medium/low-confidence hypotheses requiring further evidence.
4. Compatibility assessment:
   - compatible,
   - conditionally compatible,
   - or structurally mismatched areas.
5. Risks to scale-up (Faroe FW -> Scotland FW -> sea).
6. Decision options for leadership:
   - continue as-is,
   - continue with safeguards,
   - redesign parts of mapping/model.
7. Concrete verification experiments to reduce uncertainty.

## Tone and Method Guidance
- Prefer falsification mindset over confirmation mindset.
- Explicitly state confidence level for each claim.
- Separate observed evidence from interpretation.
- Avoid bias toward preserving current approach if evidence suggests a different direction.

## Desired Outcome
A clear, evidence-backed answer to this practical question:
- “Are we converging on a generally correct migration, or are we compensating for a deeper model/semantic mismatch that requires mitigation at product/process level?”
