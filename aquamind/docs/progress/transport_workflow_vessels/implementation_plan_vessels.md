**Vessel Transport Integration Implementation Plan**  
**Ready for Cursor IDE**  
**Target Branch:** `feature/vessel-transport-integration`  
**Estimated Effort:** 2–3 days (backend 1.5d + frontend 1d + testing 0.5d)  
**Goal:** Full traceability for FW-container → vessel-tank → sea-ring transfers using **existing** `TransferWorkflow`/`TransferAction` flow. AVEVA remains the real-time SCADA/alarm UI; AquaMind becomes the operational system of record.

### Reading List for Cursor Agent (copy-paste these into Cursor first)

**Must-read (in this order – ~15 min total):**
1. `TRANSFER_WORKFLOW_FINANCE_GUIDE.md` – entire doc (defines the exact execution flow crew will use)
2. `planning_and_workflows_primer.md` – sections “The Symbiotic Loop” and “Transfer Workflow Integration”
3. `data_model.md` – sections 4.1 (Infrastructure), 4.2 (Batch), 4.11 (Historian), 4.12 (Operational Planning)
4. `live_forward_projection_guide.md` – “How It Works” + “Data Models” (shows why per-container env readings matter)
5. `RBAC_FRONTEND_IMPLEMENTATION.md` – entire doc (we need a new `SHIP_CREW` role + guards)
6. `architecture.md` – “Historian Integration” and “External System Integrations”
7. `CONTRIBUTING.md` – “Always Use Generated ApiService”, “Backend-first API Strategy”
8. `prd.md` – 3.1.2.1 Transfer Workflow Architecture + 3.1.3 Feed/Inventory (for compliance context)

**Reference only (skim):**
- `personas.md` – “Captain of Logistics Ship” and “Ship Personnel (Fish Handling Specialist)”
- `multi-entity-filtering-guide.md` – for vessel filter UI if needed

### 1. Executive Summary

- Add `Vessel` model + `vessel` FK on `infrastructure_container` (VesselTank = Container with vessel FK).
- Extend existing `BatchTransferWorkflow`/`TransferAction` to support vessel tanks as source or destination.
- Crew executes actions in AquaMind mobile UI (same dialog as today) → creates exact `BatchContainerAssignment` + triggers historian snapshot for enter/exit env readings.
- AVEVA only provides passive sensor feed + alarms; no operational data entry there.
- Full compliance: timestamped enter/exit readings stored against the exact assignment.
- RBAC: only `SHIP_CREW` (or `OPR` + `subsidiary=LG`) can execute vessel actions.

### 2. Backend Changes

#### 2.1 Data Model (infrastructure app)

```python
# models.py
class Vessel(models.Model):
    name = models.CharField(max_length=100, unique=True)  # "Martin"
    imo_number = models.CharField(max_length=20, blank=True, null=True)
    geography = models.ForeignKey('infrastructure.Geography', on_delete=models.PROTECT)
    capacity_m3 = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# Update existing Container
class Container(models.Model):
    ...
    vessel = models.ForeignKey('Vessel', on_delete=models.SET_NULL, null=True, blank=True, related_name='tanks')
```

- Migration: `python manage.py makemigrations infrastructure --name add_vessel`
- Run migration + create 2–3 test vessels via admin or data migration.

#### 2.2 Extend TransferAction & Workflow

- Add validation in `TransferAction.clean()` / serializer: source or dest can be vessel tank.
- In `TransferAction.execute()`:
  - On **loading** (FW → VesselTank): snapshot historian tags linked to **source** and **dest** containers at exact execution timestamp → create `EnvironmentalReading` records with `reading_time = now()`.
  - On **unloading** (VesselTank → SeaRing): same, snapshot enter/exit.
- Use existing `historian_tag_link` (already built) to map AVEVA tags → AquaMind sensors.
- Add `is_vessel_transfer` computed property on Workflow for finance / reporting.

#### 2.3 RBAC

- New permission: `can_execute_vessel_transfer` (or reuse `operational` + `subsidiary=LG`).
- In `TransferActionViewSet.execute()`: `permission_classes = [IsShipCrewOrAdmin]`
- Create `IsShipCrew` permission class (check `user.userprofile.role in ('SHIP_CREW', 'OPR') and subsidiary == 'LG'`).

#### 2.4 API & Signals

- No new endpoints needed for execution (reuse existing `/transfer-actions/{id}/execute/`).
- Signal on `TransferAction.post_save` (status=COMPLETED) → trigger historian snapshot if vessel involved.
- Update `BatchContainerAssignment` creation logic to handle vessel tanks seamlessly.

#### 2.5 Historian Snapshot Helper (new utility)

```python
# apps/environmental/services/historian_snapshot.py
def snapshot_vessel_tank_readings(action: TransferAction, moment: str):  # "enter" or "exit"
    # Get linked tags for source + dest containers
    # Call AVEVA historian API (or use existing ingestion path)
    # Create EnvironmentalReading records with reading_time = timezone.now()
```

### 3. Frontend Changes

#### 3.1 Infrastructure UI

- Add Vessel list/detail page (reuse Container patterns).
- In Container detail: show “Vessel: Martin” if linked.
- Multi-entity filter support for vessels (reuse `MultiSelectFilter` from multi-entity-filtering-guide.md).

#### 3.2 Transfer Workflow UI (extend existing)

- In workflow creation / action list: show vessel tanks in source/dest dropdowns (filter by vessel).
- Execution dialog (mobile-optimized): same as today, but label “Loading to Vessel Tank T05” or “Unloading from Vessel Tank T08”.
- After execute: show confirmation “Enter readings captured at 12:34:56” (read-only snapshot).

#### 3.3 RBAC

- Use existing `UserContext` + `PermissionGuard`.
- New role check: `isShipCrew` in `UserContext.tsx`.
- Hide vessel execution buttons for non-crew.
- Sidebar: show “Vessel Transfers” only for `SHIP_CREW` / Logistics users.

#### 3.4 Env Reading Display

- On TransferAction detail: new “Enter Readings” and “Exit Readings” cards (timestamp + key params: pH, O₂, temp, CO₂, salinity).
- Reuse existing environmental reading components.

### 4. RBAC Configuration (quick)

- Add to `users_userprofile.role` choices: `'SHIP_CREW'`.
- In Django admin: assign `SHIP_CREW` + `subsidiary=LG` to ship personnel.
- Frontend: extend `UserContext` with `isShipCrew`.

### 5. Testing Plan (run these in Cursor)

**Backend:**
- Create vessel + tanks.
- Create workflow with FW → VesselTank action → execute as SHIP_CREW → verify `BatchContainerAssignment` + 2× `EnvironmentalReading` records created with correct timestamps.
- Verify non-crew cannot execute.
- Check Live Forward Projection still works after vessel segment.

**Frontend:**
- Login as SHIP_CREW → see vessel tanks in workflow UI.
- Execute action → see snapshot confirmation.
- Login as normal operator → cannot see/execute vessel actions.

**Compliance:**
- Export env readings for a transport → verify enter/exit timestamps match execution time.

### 6. Deployment / Migration Notes

- Run migration before deploy.
- Seed 3 test vessels + map 10 AVEVA tags to their tanks via admin.
- No data migration needed (existing containers stay unchanged).
- Update documentation: add section to `TRANSFER_WORKFLOW_FINANCE_GUIDE.md`.
- Update prd.md (section 3.1.2.1 or a new subsection?) and data_model.md using the style of the docs, respectively

### 7. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| AVEVA API latency during execute | Snapshot async via Celery task (fire-and-forget) |
| Duplicate readings | Unique constraint on `(container_id, reading_time, parameter_id)` |
| Crew forgets to execute in AquaMind | Mobile push notification reminder 2 min after planned time |
| Historian tags not mapped | Admin dashboard “Vessel Tank Mapping” page (reuse historian_tag_link) |

---