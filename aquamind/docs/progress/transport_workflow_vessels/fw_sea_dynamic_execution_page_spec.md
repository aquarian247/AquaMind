# FW->Sea Dynamic Execution Page Spec

**Status:** Implemented (Current Branch)  
**Date:** March 4, 2026  
**Owner:** Batch + Frontend + Logistics  
**Related:** `prd.md` (3.1.2, 3.1.2.1), `data_model.md` (4.1), `implementation_plan_vessels.md`

---

## Implementation Notes (March 4, 2026)

- Delivered backend endpoints:
  - `POST /api/v1/batch/transfer-workflows/{id}/handoffs/start/`
  - `POST /api/v1/batch/transfer-actions/{id}/complete-handoff/`
  - `GET /api/v1/batch/transfer-workflows/{id}/execution-context/`
  - `POST /api/v1/batch/transfer-workflows/{id}/complete-dynamic/`
- Dynamic planning is intent-only; runtime modal creation paths are blocked/deprecated.
- Compliance start snapshot policy is config-driven via `TRANSFER_START_MISSING_MAPPING_POLICY` (`STRICT` or `OVERRIDE`).
- Legacy cleanup command implemented: `cleanup_dynamic_transport_legacy` with dry-run + apply modes and idempotent behavior.

---

## 1. Problem Statement

Current dynamic FW->Sea flow still behaves partly like pre-planned workflows:

- Handoffs are created in bulk as `PENDING` actions.
- Destination assignments are created as inactive placeholders (`population=0`, `is_active=false`).
- Next-leg sources (e.g., truck->vessel) depend on executed previous legs, so planning many legs up front creates empty-source dead-ends.
- Modal UX is fragile for long, real-world transport work (accidental dismiss, poor continuity, low situational awareness).

Operationally, FW->Sea transfer is high-variance and on-the-fly. Planning exact tank-pair actions in advance creates stale/hanging actions and extra cleanup burden.

---

## 2. Decision Summary

For FW->Sea dynamic workflows:

1. Plan intent only (no container-level actions in DRAFT/PLANNED).
2. Offer only two route modes:
   - `DIRECT_STATION_TO_VESSEL`
   - `VIA_TRUCK_TO_VESSEL`
3. Replace modal handoff creation with a dedicated execution page.
4. Execute each handoff in two explicit steps:
   - `Start Transfer` (creates action in-progress + mandatory start snapshot)
   - `Complete Transfer` (applies final counts/mortality + completes action)
5. Complete dynamic workflow explicitly by operator signoff (not by action-count equality).

---

## 3. Scope

### In Scope

- FW->Sea dynamic transfer workflows only.
- New execution page and start/complete handoff endpoints.
- Workflow/model/API adjustments required for intent-only planning and explicit completion.
- Cleanup of deprecated modal-based dynamic flow and stale data patterns.

### Out of Scope

- Internal station redistribution workflows (remain pre-planned actions).
- Sea-side redistribution/harvest workflows (remain existing model unless separately specified).
- Offline-first mobile support.

---

## 4. Functional Requirements

### 4.1 Planning Phase (Intent Only)

Dynamic FW->Sea workflow creation captures:

- Batch
- Source lifecycle stage
- Destination lifecycle stage
- Route mode (`DIRECT_STATION_TO_VESSEL` or `VIA_TRUCK_TO_VESSEL`)
- Planned start date
- Optional estimate fields (`estimated_total_count`, `estimated_total_biomass_kg`, notes)

No source/destination container pairings are created during planning.

### 4.2 Execution Phase (Live, On-the-Fly)

Execution happens from dedicated page: `/transfer-workflows/:id/execute`.

Each handoff lifecycle must:

- Validate route-leg compatibility.
- Validate source assignment availability from live active assignments.
- On `Start Transfer`:
  - create `TransferAction` in `IN_PROGRESS`,
  - capture mandatory AVEVA snapshot for source and destination containers,
  - include O2, temperature, CO2 values (if mapped/available).
- On `Complete Transfer`:
  - resolve/create destination assignment,
  - apply population/biomass/mortality updates,
  - set action `COMPLETED` with execution metadata.

No speculative `PENDING` actions are created for future legs.

### 4.3 Completion

Dynamic workflow completion is explicit:

- Operator presses `Complete Workflow`.
- System validates:
  - no active in-progress submission,
  - transfer has at least one executed action,
  - optional warning if estimate variance exceeds threshold.
- Workflow becomes `COMPLETED`; finance detection/creation runs as today.

### 4.4 Environmental Compliance Requirement (Mandatory)

For every physical transfer start event (station->truck, station->vessel, truck->vessel, vessel->ring):

- Operator must press `Start Transfer`.
- Backend must call AVEVA integration path for source + destination tank context at that timestamp.
- Required parameters to persist (when available from sensors):
  - O2
  - Temperature
  - CO2
- Manual fields (if needed) remain separate and do not replace mandatory start snapshot.
- If AVEVA endpoint/tag mapping is missing for either side:
  - start action is blocked by default in strict mode,
  - or requires privileged override with explicit compliance note (policy-controlled).

---

## 5. UX Specification (Execution Page)

### 5.1 Page Structure

Top-level sections:

1. **Workflow Header**
   - Workflow number/status, route mode, batch, elapsed time.
2. **Live Availability Panel**
   - Source pool by container class (station/truck/vessel) with active counts/biomass.
3. **Handoff Composer**
   - Single robust form for one handoff at a time with `Start Transfer` and `Complete Transfer` controls.
   - Leg type constrained by route mode.
4. **Recent Handoffs Timeline/Table**
   - Latest executed actions with source->dest, fish, biomass, mortality, operator, timestamp.
5. **Progress & Variance**
   - Executed totals vs estimates.
6. **Footer Controls**
   - `Complete Workflow`, `Cancel Workflow`.

### 5.2 UX Guardrails

- No dismiss-on-outside-click risk (full page).
- Unsaved-change route guard when editing handoff form.
- Optimistic lock messaging if same source is used concurrently.
- “Repeat last handoff” shortcut for high-throughput operations.
- Clear operator feedback on start snapshot capture and completion.

### 5.3 Role Behavior

- SHIP_CREW / Logistics operator: full execution controls.
- Others: read-only execution page with live timeline and progress.

---

## 6. Backend/API Contract

### 6.1 New Endpoint (Start Transfer)

`POST /api/v1/batch/transfer-workflows/{id}/handoffs/start/`

Behavior:

- Creates one `TransferAction` in `IN_PROGRESS`.
- Captures mandatory start snapshot for source + destination container assignments.
- Returns action detail + captured snapshot summary + workflow deltas.

Request (example):

```json
{
  "leg_type": "STATION_TO_TRUCK",
  "source_assignment_id": 2536,
  "dest_container_id": 4412,
  "planned_transferred_count": 10000,
  "planned_transferred_biomass_kg": "500.00",
  "transfer_method": "PUMP",
  "allow_mixed": false,
  "notes": "Truck alpha fill pass 1 at pump start"
}
```

### 6.2 New Endpoint (Complete Transfer)

`POST /api/v1/batch/transfer-actions/{id}/complete-handoff/`

Behavior:

- Valid only for actions in `IN_PROGRESS`.
- Applies transferred count, biomass, mortality, assignment updates, and marks action `COMPLETED`.
- Triggers completion-side environmental snapshot behavior where configured.

### 6.3 Existing Endpoint (In-Transit Snapshot)

Reuse existing:

`POST /api/v1/batch/transfer-actions/{id}/snapshot/`

with `moment=in_transit` for optional periodic readings while in transit.

### 6.4 New Endpoint (Execution Context)

`GET /api/v1/batch/transfer-workflows/{id}/execution-context/`

Returns:

- Allowed legs for route mode.
- Live source assignments by container class.
- Candidate destination containers by container class.
- Current workflow progress and estimates.

### 6.5 Completion Endpoint

Use existing `complete` action with dynamic validation extension or add:

`POST /api/v1/batch/transfer-workflows/{id}/complete-dynamic/`

Rule: dynamic workflow completion must be explicit operator action.

### 6.6 Existing Endpoint Policy Change

For `is_dynamic_execution=true`:

- Direct generic action creation (`POST /transfer-actions/`) is blocked for dynamic workflows in runtime usage.
- Single-step dynamic execution (`/transfer-actions/{id}/execute/`) is blocked for dynamic workflows.
- Required runtime path is `handoffs/start` + `complete-handoff` + explicit workflow completion.

---

## 7. Data Model Changes

### 7.1 Required (Recommended)

### `batch_batchtransferworkflow`

- Add `dynamic_route_mode` (`DIRECT_STATION_TO_VESSEL`, `VIA_TRUCK_TO_VESSEL`) nullable for non-dynamic workflows.
- Add optional estimate fields:
  - `estimated_total_count` nullable
  - `estimated_total_biomass_kg` nullable
- Add explicit completion metadata:
  - `dynamic_completed_by` FK nullable
  - `dynamic_completed_at` datetime nullable

### `batch_transferaction`

- Add `leg_type` enum:
  - `STATION_TO_VESSEL`
  - `STATION_TO_TRUCK`
  - `TRUCK_TO_VESSEL`
- Add `executed_at` datetime (high-resolution operational ordering); keep existing `actual_execution_date` for compatibility.
- Add `created_via` enum (`PLANNED`, `DYNAMIC_LIVE`) for analytics and cleanup logic.

### 7.2 Optional (Deferred)

Introduce dedicated `batch_transporthandoffevent` table if event stream must diverge from `TransferAction` semantics later. Not required for v1.

---

## 8. State Machine Adjustments

Current dynamic workflows can auto-complete when `actions_completed >= total_actions_planned`. This is unsafe when actions are generated during execution.

New rule:

- Dynamic workflows never auto-complete by action count.
- Completion requires explicit operator action.
- Progress percentage for dynamic workflows derives from executed totals vs estimates (if estimates provided); otherwise show executed totals without forcing percent-to-100 semantics.
- Transfer action lifecycle for dynamic flows must be explicitly used:
  - `IN_PROGRESS` at start
  - `COMPLETED` at finish

---

## 9. Deprecation and Cleanup Workstream (Mandatory)

### 9.1 Frontend Cleanup

- Remove deprecated modal-first dynamic execution path:
  - Retire `DynamicTransportActionsDialog` from runtime routing.
  - Remove modal trigger path from `WorkflowDetailPage` for dynamic workflows.
- Introduce dedicated execution page components and route.
- Remove dead modal-specific code branches and stale helper utilities.

### 9.2 Backend Cleanup

- Remove/disable placeholder-assignment creation pattern for dynamic handoffs.
- Centralize dynamic handoff logic in start/complete service endpoints.
- Remove dependence on notes-based leg encoding (`notes: [LEG_TYPE]`) once `leg_type` field is in place.

### 9.3 Data Cleanup / Migration Safety

Provide management command:

`python manage.py cleanup_dynamic_transport_legacy --workflow-id=<id|all> --dry-run`

Actions:

1. Detect stale `PENDING` dynamic actions older than threshold with no operational relevance.
2. Mark stale actions as `SKIPPED` with structured reason (`deprecated_dynamic_modal_flow`).
3. Detect orphan/placeholder destination assignments (`is_active=false`, zero population/biomass, created by placeholder note) with no completed action linkage.
4. Soft-clean by archiving note tag first; hard-delete only with explicit `--apply-hard-delete`.

All cleanup operations must be idempotent and auditable.

---

## 10. Migration and Rollout Plan

### Phase 0: Schema + Feature Flag

- Add schema changes.
- Add feature flag: `FW_SEA_EXECUTION_PAGE_ENABLED`.
- Keep old modal path available.

### Phase 1: Dual Path (Internal)

- Enable execution page for test roles.
- Keep modal path read-only warning for dynamic workflows.
- Run cleanup command in dry-run and review.

### Phase 2: Cutover

- Enable execution page for all dynamic FW->Sea workflows.
- Disable modal dynamic action creation.
- Run approved cleanup command in apply mode.

### Phase 3: Remove Deprecated Code

- Delete dead UI components and stale endpoint logic.
- Remove feature flag and fallback branches.
- Update docs and training material.

---

## 11. Testing Plan

### Backend

- Start/complete handoff execution:
  - station->truck, truck->vessel, direct station->vessel, vessel->ring
- Mandatory start snapshots:
  - source+destination readings captured for O2/temp/CO2 when mapped
  - policy behavior when mapping is missing (block vs privileged override)
- Concurrency:
  - two users attempting same source assignment simultaneously
- Snapshot capture integrity per handoff
- Dynamic explicit completion behavior
- Cleanup command idempotency and safety

### Frontend

- Execution page routing and runtime handoff flow validation
- Read-only role behavior validation
- Progress/variance rendering with and without estimates
- Frontend type-check coverage for new route/page/API usage

### UAT Scenarios

1. Planned 10 trucks, used 9 trucks.
2. Planned direct route, actual route remains direct.
3. Partial day execution with continuation next day.
4. Explicit complete with variance note.

---

## 12. Acceptance Criteria

1. Dynamic FW->Sea workflows can be planned without container-level actions.
2. Operators can execute full transport via dedicated page without modal UX.
3. Next-leg sources always reflect real executed state (no chicken-egg gaps).
4. No hanging speculative `PENDING` actions are required for normal operation.
5. Dynamic completion is explicit and auditable.
6. Deprecated dynamic modal flow is removed from runtime and codebase.
7. Legacy stale data cleanup command exists, is safe, and documented.
8. Each transfer start records mandatory source+destination AVEVA readings for O2/temp/CO2 (or approved override policy).

---

## 13. Implementation Task Breakdown

1. Backend schema migration (`dynamic_route_mode`, `leg_type`, execution metadata).
2. Backend service for `handoffs/start` (action creation + mandatory start snapshot).
3. Backend service for `complete-handoff` (population/biomass mutation + action completion).
4. Backend execution-context endpoint.
5. Dynamic completion rule update.
6. Frontend execution page route + components.
7. Remove modal dynamic creation path from workflow detail.
8. Management command for legacy cleanup.
9. Documentation updates (`prd.md`, `data_model.md`, user guide).
10. E2E and regression test suite updates.
11. Final dead code removal pass post-cutover.

---

## 14. Open Questions

1. Should vessel->ring be modeled as a separate workflow type or included in this same dynamic route family?
2. Should estimate variance thresholds block completion or only warn?
3. Do we need a mandatory completion note when variance exceeds threshold?
4. Should direct `POST /transfer-actions/` for dynamic workflows be hard-blocked immediately or after one release cycle?
