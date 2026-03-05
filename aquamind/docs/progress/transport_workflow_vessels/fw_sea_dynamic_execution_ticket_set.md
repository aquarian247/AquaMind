# FW->Sea Dynamic Execution - Implementation Ticket Set

**Status:** Implemented (Current Branch)  
**Date:** March 4, 2026  
**Source Spec:** `fw_sea_dynamic_execution_page_spec.md`  
**Primary Goal:** Replace modal-based dynamic handoff planning with page-based live execution and mandatory start-of-transfer environmental compliance snapshots.

---

## Implementation Outcome (March 4, 2026)

Completed in this branch:

- Epic A: FWSEA-001, FWSEA-002, FWSEA-003
- Epic B: FWSEA-010, FWSEA-011, FWSEA-012, FWSEA-013
- Epic C: FWSEA-020, FWSEA-021, FWSEA-022 (policy/config path), FWSEA-023 (mapped through existing historian link model + settings)
- Epic D: FWSEA-030, FWSEA-031, FWSEA-032, FWSEA-033
- Epic E: FWSEA-040, FWSEA-041, FWSEA-042, FWSEA-044

Verification note:

- Backend automated tests for dynamic start/complete, completion semantics, concurrency guard, strict/override policy, and legacy cleanup are included.
- Frontend type-check is included.
- Prior Playwright E2E scenarios in this area are currently outdated and intentionally not treated as release-gating in this pass.

---

## 1. Delivery Strategy

Implementation is split into 5 epics:

1. Data model + workflow state semantics
2. Dynamic handoff API (start/complete)
3. AVEVA compliance snapshots (mandatory at transfer start)
4. Frontend execution page and modal deprecation
5. Cleanup, migration safety, rollout, and verification

---

## 2. Dependency and Risk Notes

### Hard Dependencies

- AVEVA endpoint addresses and sensor tag mapping for O2/temp/CO2 are not finalized.
- Policy decision needed for missing mapping behavior:
  - strict block,
  - privileged override with mandatory compliance note.

### Risk Mitigation

- Build integration behind adapter interface so endpoint details can be plugged in later.
- Implement strict/override policy as config, not hard-coded logic.
- Gate production enablement behind feature flags and contract tests.

---

## 3. Ticket Backlog

## Epic A - Data Model and State Machine

### FWSEA-001: Add dynamic route metadata to workflow

- **Type:** Backend migration/model
- **Estimate:** 4 hours
- **Depends on:** None
- **Changes:**
  - Add `dynamic_route_mode` to `batch_batchtransferworkflow`
  - Add optional estimate fields (`estimated_total_count`, `estimated_total_biomass_kg`)
  - Add explicit dynamic completion metadata (`dynamic_completed_by`, `dynamic_completed_at`)
- **Acceptance Criteria:**
  - Migration applies cleanly.
  - Existing workflows remain valid.
  - Non-dynamic workflows unaffected.

### FWSEA-002: Extend transfer action for dynamic handoff semantics

- **Type:** Backend migration/model
- **Estimate:** 6 hours
- **Depends on:** FWSEA-001
- **Changes:**
  - Add `leg_type` enum (`STATION_TO_VESSEL`, `STATION_TO_TRUCK`, `TRUCK_TO_VESSEL`, `VESSEL_TO_RING`)
  - Add high-resolution `executed_at` datetime
  - Add `created_via` enum (`PLANNED`, `DYNAMIC_LIVE`)
- **Acceptance Criteria:**
  - Actions can be tagged by leg and creation mode.
  - Existing APIs serialize new fields safely.

### FWSEA-003: Dynamic workflow completion rule update

- **Type:** Backend logic
- **Estimate:** 4 hours
- **Depends on:** FWSEA-001
- **Changes:**
  - Disable action-count auto-complete for dynamic workflows.
  - Require explicit completion call.
- **Acceptance Criteria:**
  - Dynamic workflows do not auto-complete when actions count matches.
  - Non-dynamic workflows keep existing behavior.

---

## Epic B - Handoff Execution API

### FWSEA-010: Start Transfer endpoint

- **Type:** Backend API/service
- **Estimate:** 8 hours
- **Depends on:** FWSEA-002
- **Endpoint:** `POST /api/v1/batch/transfer-workflows/{id}/handoffs/start/`
- **Behavior:**
  - Validates leg compatibility and source availability.
  - Creates `TransferAction` in `IN_PROGRESS`.
  - Triggers mandatory start snapshot path.
- **Acceptance Criteria:**
  - Action created with `status=IN_PROGRESS` and `created_via=DYNAMIC_LIVE`.
  - Endpoint returns action + snapshot summary payload.

### FWSEA-011: Complete Transfer endpoint

- **Type:** Backend API/service
- **Estimate:** 8 hours
- **Depends on:** FWSEA-010
- **Endpoint:** `POST /api/v1/batch/transfer-actions/{id}/complete-handoff/`
- **Behavior:**
  - Valid only from `IN_PROGRESS`.
  - Applies count/biomass/mortality and assignment mutations.
  - Marks action `COMPLETED`.
- **Acceptance Criteria:**
  - Source/destination populations are updated once.
  - Completion updates workflow totals and progress.
  - Rejects completion if action not `IN_PROGRESS`.

### FWSEA-012: Execution Context endpoint

- **Type:** Backend API
- **Estimate:** 5 hours
- **Depends on:** FWSEA-001
- **Endpoint:** `GET /api/v1/batch/transfer-workflows/{id}/execution-context/`
- **Behavior:**
  - Returns live source assignments and destination candidates by route mode.
  - Includes workflow estimate/progress context.
- **Acceptance Criteria:**
  - Returned sources reflect active assignments only.
  - Response supports rendering execution page without additional N+1 calls.

### FWSEA-013: Restrict deprecated dynamic create paths

- **Type:** Backend API policy
- **Estimate:** 4 hours
- **Depends on:** FWSEA-010, FWSEA-011
- **Changes:**
  - Deprecate direct dynamic operational creation via generic `POST /transfer-actions/`.
  - Enforce new flow for dynamic FW->Sea workflows.
- **Acceptance Criteria:**
  - Deprecated path is blocked for dynamic workflows in runtime API usage.

---

## Epic C - AVEVA Compliance Snapshots

### FWSEA-020: Implement AVEVA snapshot adapter contract

- **Type:** Backend integration architecture
- **Estimate:** 6 hours
- **Depends on:** None
- **Changes:**
  - Add provider interface for transfer snapshot fetch (`source`, `destination`, `timestamp`, `parameters`).
  - Support required parameter set: O2, temperature, CO2.
- **Acceptance Criteria:**
  - Adapter can run in mock mode for integration testing.
  - Start endpoint depends only on adapter contract, not hard-coded endpoint URLs.

### FWSEA-021: Wire start-of-transfer mandatory snapshot capture

- **Type:** Backend integration/service
- **Estimate:** 8 hours
- **Depends on:** FWSEA-010, FWSEA-020
- **Changes:**
  - On `handoffs/start`, fetch source+destination values via AVEVA adapter.
  - Persist readings linked to action/assignment with timestamp + compliance marker.
- **Acceptance Criteria:**
  - Every started handoff has attempt/result record for both source and destination.
  - O2/temp/CO2 are persisted when available.

### FWSEA-022: Missing-tag policy and override flow

- **Type:** Backend policy/config
- **Estimate:** 5 hours
- **Depends on:** FWSEA-021
- **Changes:**
  - Add strict mode (`block_start_if_missing_tags=true|false`).
  - Add privileged override path requiring compliance note.
- **Acceptance Criteria:**
  - In strict mode, start is blocked when mandatory mapping missing.
  - Override path is auditable and role-restricted.

### FWSEA-023: AVEVA endpoint/tag config plumbing

- **Type:** Backend ops/config
- **Estimate:** 6 hours (excluding external provisioning)
- **Depends on:** FWSEA-020
- **Changes:**
  - Introduce env/config keys or mapping storage for endpoint base URL and tag IDs.
  - Bind container->tag mapping to existing historian mapping structures where possible.
- **Acceptance Criteria:**
  - Endpoint and tag mapping can be configured without code changes.
  - Health check endpoint/command validates readiness.

---

## Epic D - Frontend Execution Page

### FWSEA-030: Add execution route and page scaffold

- **Type:** Frontend
- **Estimate:** 6 hours
- **Depends on:** FWSEA-012
- **Changes:**
  - Add route `/transfer-workflows/:id/execute`.
  - Add read-only vs operator role rendering.
- **Acceptance Criteria:**
  - Dynamic workflows open execution page from workflow detail.
  - Non-authorized roles see read-only mode.

### FWSEA-031: Build Start Transfer UX

- **Type:** Frontend
- **Estimate:** 8 hours
- **Depends on:** FWSEA-010, FWSEA-012
- **Changes:**
  - Handoff composer with leg constraints.
  - `Start Transfer` action and start snapshot feedback.
- **Acceptance Criteria:**
  - Operator can start station->truck, station->vessel, truck->vessel, vessel->ring.
  - Start response visibly shows compliance snapshot status.

### FWSEA-032: Build Complete Transfer UX

- **Type:** Frontend
- **Estimate:** 8 hours
- **Depends on:** FWSEA-011
- **Changes:**
  - Complete form for `IN_PROGRESS` actions with actual counts/mortality.
  - Update recent timeline and progress after completion.
- **Acceptance Criteria:**
  - Completion only enabled for in-progress handoffs.
  - UI handles validation/conflict errors gracefully.

### FWSEA-033: Deprecate and remove modal dynamic flow from runtime

- **Type:** Frontend cleanup
- **Estimate:** 5 hours
- **Depends on:** FWSEA-030, FWSEA-031, FWSEA-032
- **Changes:**
  - Remove modal launch path for dynamic workflows from workflow detail.
  - Keep optional temporary fallback behind feature flag in phase 1 only.
- **Acceptance Criteria:**
  - Dynamic workflow actions are no longer created through modal path in production mode.

---

## Epic E - Cleanup, Safety, and Rollout

### FWSEA-040: Legacy dynamic data cleanup command

- **Type:** Backend maintenance
- **Estimate:** 7 hours
- **Depends on:** FWSEA-013
- **Command:** `cleanup_dynamic_transport_legacy`
- **Behavior:**
  - Identify stale pending modal-era actions.
  - Skip/archive legacy placeholders safely.
  - Report orphan inactive placeholder assignments.
- **Acceptance Criteria:**
  - `--dry-run` and apply modes implemented.
  - Command is idempotent and auditable.

### FWSEA-041: Remove dead/deprecated backend code

- **Type:** Backend cleanup
- **Estimate:** 4 hours
- **Depends on:** FWSEA-040
- **Changes:**
  - Remove placeholder assignment code branches no longer used.
  - Remove notes-based leg parsing once `leg_type` fully adopted.
- **Acceptance Criteria:**
  - No production path depends on deprecated behavior.

### FWSEA-042: Remove dead/deprecated frontend code

- **Type:** Frontend cleanup
- **Estimate:** 4 hours
- **Depends on:** FWSEA-033
- **Changes:**
  - Remove unused dialog components and helpers tied to dynamic modal flow.
  - Remove feature flags/fallback routes post-cutover.
- **Acceptance Criteria:**
  - Build has no references to removed dynamic modal components.

### FWSEA-043: E2E + contract tests for compliance-critical flow

- **Type:** QA/automation
- **Estimate:** 8 hours
- **Depends on:** FWSEA-031, FWSEA-032, FWSEA-021, FWSEA-022
- **Coverage:**
  - Start captures mandatory source+destination snapshots.
  - Complete applies population correctly.
  - Strict-mode block and privileged override behavior.
- **Acceptance Criteria:**
  - Test suite fails if mandatory start snapshot logic regresses.

### FWSEA-044: Rollout runbook + docs updates

- **Type:** Docs/ops
- **Estimate:** 4 hours
- **Depends on:** All prior epics
- **Changes:**
  - Update PRD/data model/user guides.
  - Add rollout checklist, monitoring KPIs, and rollback procedure.
- **Acceptance Criteria:**
  - Handover-ready docs for operations and support.

---

## 4. Critical Path and Sequence

Recommended order:

1. FWSEA-001, FWSEA-002, FWSEA-003
2. FWSEA-020, FWSEA-023
3. FWSEA-010, FWSEA-011, FWSEA-012
4. FWSEA-021, FWSEA-022
5. FWSEA-030, FWSEA-031, FWSEA-032
6. FWSEA-013, FWSEA-033
7. FWSEA-040, FWSEA-041, FWSEA-042
8. FWSEA-043, FWSEA-044

---

## 5. Estimate Summary

- **Backend core (Epics A + B):** ~35 hours
- **AVEVA compliance integration (Epic C):** ~25 hours (+ external tag/endpoint readiness)
- **Frontend execution page (Epic D):** ~27 hours
- **Cleanup/QA/docs (Epic E):** ~27 hours
- **Total engineering estimate:** ~114 hours (about 3 weeks for one full-time engineer, or ~1.5 weeks for two engineers in parallel)

Add 20-30% schedule buffer for external AVEVA endpoint/tag onboarding uncertainty.

---

## 6. Go/No-Go Gates

Cutover to execution page is blocked unless all are true:

1. Start transfer captures source+destination O2/temp/CO2 from AVEVA adapter path (or governed override mode).
2. Dynamic workflows no longer depend on speculative pending actions.
3. Explicit complete path works and finance integration still triggers correctly.
4. Legacy cleanup dry-run reviewed and approved.
5. E2E compliance tests pass in CI.

---

## 7. Immediate Next Actions

1. Confirm strict-mode policy vs override policy for missing AVEVA tags.
2. Assign owners for FWSEA-020 and FWSEA-023 first (integration unblockers).
3. Start Epic A migrations in parallel with frontend route scaffolding.
