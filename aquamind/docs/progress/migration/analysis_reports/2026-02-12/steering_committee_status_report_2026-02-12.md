# Steering Committee Status Report - FishTalk -> AquaMind Migration
Date: 2026-02-12
Audience: Steering Committee (non-technical and technical stakeholders)
Prepared by: Migration workstream

## 1) Executive summary (plain language)
We are moving data from an old system (FishTalk) into AquaMind. The migration is working very well for most operational records (feed, mortality, transfers, etc.), but one specific area is still too fragile for broad policy automation: reliably linking some freshwater (FW) records to sea-stage records in a fully deterministic way across all cohorts.

In simple terms:
- The **core data transfer is strong** in tested cohorts.
- The **hard part is identity/linking logic** in a subset of lifecycle scenarios.
- We have strong diagnostics, strong guardrails, and no runtime architecture compromise.
- We are **not recommending a global FW/Sea auto-link policy change yet**.

Current recommendation:
1. **GO** for continuing migration-tooling integration and staged validation.
2. **NO-GO** for global FW/Sea auto-link policy promotion at this time.

## 2) What this project is doing (layman’s explanation)
Think of this migration as moving records from one filing system to another:
- Most folders map cleanly.
- A few folders contain documents that were historically cross-referenced in implicit/opaque ways.
- We can move the documents accurately, but some cross-references still need stronger proof before we automate them globally.

The team has intentionally kept this complexity inside migration tooling and validation reports. We have **not polluted AquaMind runtime/API/UI logic with FishTalk-specific behavior**.

## 3) Status by workstream
### A. Data movement quality (tested scope)
Status: **Green**

What is going well:
- Operational migration outputs are stable in tested FW cohorts.
- Count/semantic validation gates are largely strong for core operational entities.

Meaning for the business:
- Day-to-day records are being transferred with high reliability in validated scenarios.

### B. Lifecycle linkage semantics (FW -> Sea)
Status: **Amber/Red**

What is hard:
- Deterministic linking between some FW and Sea endpoints does not generalize across the full FW20 cohort set under strict acceptance criteria.

Key result:
- Strict FW20 endpoint gate profile: **1/20 cohorts PASS**.

Meaning for the business:
- We should avoid broad automation assumptions for FW/Sea linking until broader deterministic evidence exists.

### C. Architecture and product integrity
Status: **Green**

Guardrails held:
- AquaMind runtime remains FishTalk-agnostic.
- Migration-specific logic stays in extraction/validation/reporting tooling.
- No runtime API/UI coupling to FishTalk semantics was introduced.

## 4) Evidence highlights (non-technical summary with concrete numbers)
## 4.1 External-mixing sensitivity (important but bounded)
- One cohort (`Stofnfiskur Juni 24`) is sensitive to a threshold boundary at fry stage entry.
- Wider FW20 checks did **not** show broad generalization.
- Decision remains: keep global external-mixing default at **10.0** unless stronger broad evidence appears.

## 4.2 FW20 strict endpoint gate matrix
- Cohorts evaluated: **20**
- Strict profile result: **PASS 1 / FAIL 19**
- Main fail patterns:
  - `coverage` failures: **18**
  - `evidence` failures: **18**
  - `marine_target` failures: **16**
  - `uniqueness` failures: **5**

Interpretation:
- Signal exists in pockets but not at a level that supports global policy promotion.

## 4.3 Diagnostic profiles (to understand failure families)
We tested controlled diagnostic relaxations to understand failure types:

- Evidence-floor relax (`min-candidate-rows=4`): **PASS 2/20**
- Evidence-floor relax (`min-candidate-rows=1`): **PASS 2/20**
- Source-candidate relax (`max-source-candidates=3`): **PASS 2/20**
- Combined diagnostic (`max-source-candidates=3` + `min-candidate-rows=4`): **PASS 3/20**

Important:
- Different relaxations unlock different cohorts.
- This is useful diagnostically, but it is **not** enough to justify global policy changes.

## 4.4 Blocker-family provenance (deterministic)
For strict-profile failing cohorts with non-zero evidence, blockers fell into two clean families:
1. `direction_mismatch` (3 rows across 3 cohorts)
2. `source_candidate_count_out_of_bounds` (3 rows across 2 cohorts)

We cross-checked these with local SQL and CSV extracts; results aligned.

Business interpretation:
- The issue is not random quality noise; it is structured and diagnosable.

## 5) Decisions currently in force
These are the active program decisions:
1. Keep AquaMind runtime FishTalk-agnostic.
2. Keep migration fixes in tooling/reporting only.
3. Keep external-mixing default at **10.0**.
4. Keep strict endpoint profile as release guardrail.
5. **No global FW/Sea auto-link policy change yet**.

## 6) Risk view (business framing)
### Risk 1: Premature policy automation
- If we auto-link globally now, some cohorts may be linked incorrectly.
- Mitigation: strict gates + diagnostics + evidence-based promotion only.

### Risk 2: Overfitting to one cohort
- One cohort can look convincing but fail to generalize.
- Mitigation: matrix-wide cohort evidence, not single-case decisions.

### Risk 3: Hidden legacy semantics
- Some FishTalk semantics are application-layer/opaque.
- Mitigation: read-only SQL recon + deterministic provenance + optional tracing only when needed.

## 7) Program readiness assessment
### Ready now
- Continue migration-tooling hardening.
- Continue cohort-by-cohort deterministic validation.
- Continue reporting and governance checkpoints.

### Not ready yet
- Global, automatic FW/Sea policy promotion across the full portfolio.

Overall readiness:
- **Operational migration quality:** strong in tested scope.
- **Global FW/Sea policy readiness:** not yet.

## 8) Recommended next phase (pragmatic)
1. Focus Part B follow-up on high-signal FAIL cohorts with non-zero candidates and persistent marine/coverage failures.
2. Keep strict profile as release gate; keep relaxed profiles diagnostic-only.
3. Promote policy only after broader deterministic PASS coverage is demonstrated under guardrail criteria.

## 9) Steering committee ask
1. Endorse the current **GO/NO-GO split**:
   - GO for tooling integration and phased progress.
   - NO-GO for global policy promotion today.
2. Endorse evidence-first governance:
   - no runtime shortcutting,
   - no broad policy change without cross-cohort deterministic proof.

## 10) Bottom line
This migration is complex, but it is under control:
- We have high confidence in core migration mechanics.
- We have identified the specific hard edge (FW/Sea global linking).
- We have deterministic evidence, clear guardrails, and a safe forward path.
- The correct executive stance today is **controlled progress, not forced policy acceleration**.
