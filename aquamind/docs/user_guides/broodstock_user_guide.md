# AquaMind Broodstock Module – User Guide

_Last updated: 2025-06-12_

---

## 1. Introduction
The Broodstock module manages breeding fish, their movements, egg production, and full lineage traceability.  This guide explains how farm staff, breeders, and administrators can use the system via the **Django Admin** and the **REST API**.

> **Audience** – Hatchery managers, breeders, genetics team, and system integrators.

---

## 2. Prerequisites
1. **User account** with one of the following roles:
   • _Admin_ – full access.  
   • _Breeder_ – create/edit broodstock records.  
   • _Viewer_ – read-only.
2. Access to the AquaMind web interface (`/admin/`) or API token for programmatic access.
3. Containers, freshwater stations, and species already configured in **Infrastructure** and **Batch** modules.

---

## 3. Core Concepts & Models
| Model | Purpose |
|-------|---------|
| **Broodstock Fish** | Individual brood fish linked to a container. |
| **Fish Movement** | Transfer history between containers (auto-updates fish location). |
| **Breeding Plan** | Time-boxed plan with trait priorities and notes. |
| **Breeding Pair** | Male × female assignment inside a plan. |
| **Egg Production** | Internal (from pairs) or external (supplier) egg batches. |
| **Egg Supplier / External Egg Batch** | Tracks third-party egg acquisitions. |
| **Batch Parentage** | Links eggs to grow-out batches for traceability. |
| **Maintenance Task** | Scheduled container maintenance.

All critical models have full history tracking (django-simple-history) for audit purposes.

---

## 4. Using Django Admin
### 4.1. Broodstock Fish
1. Navigate to **Broodstock Fish → Add**.  
2. Select the _container_, set **health status**, and optionally JSON **traits**.  
3. Save – history starts tracking automatically.

### 4.2. Moving Fish
1. Open a fish record and click **"Move fish"** in actions (or record a movement directly under **Fish Movements → Add**).  
2. Choose _from_ and _to_ containers.  The system validates:
   • Destination is a Broodstock container.  
   • Biomass capacity is not exceeded.  
3. Save – fish location updates, movement logged.

### 4.3. Breeding Workflow
1. **Create Breeding Plan** – define start/end dates, objectives, notes.  
2. Under the plan, **add Trait Priorities** (e.g. _growth_rate 0.7_).  
3. **Create Breeding Pairs** – only healthy fish allowed; duplicates prevented.  
4. Track progeny counts automatically when eggs are produced.

### 4.4. Egg Production
*Internal*  
1. View a **Breeding Pair** → action **"Produce Eggs"** (or Egg Productions → Add).  
2. Enter egg count and optional destination freshwater station.  
3. Unique batch ID is generated (`EB-INT-YYYYMMDDHHMMSS-ms`).

*External*  
1. **Egg Supplier** → Add supplier once.  
2. **External Egg Batch** → Add with supplier and batch number – validation prevents duplicates.

### 4.5. Assigning Eggs to Batches
1. Create or select a juvenile **Batch** (lifecycle stage _Egg/Alevin/Fry_).  
2. **Batch Parentage → Add** – choose Egg Production and Batch.  
3. Validation ensures lifecycle stage and station compatibility.

### 4.6. Traceability
Under a **Batch** record click **Parentage** or use the **Lineage** admin action – full egg-to-fish trace displayed.

---

## 5. Typical Workflows (Step-by-Step)
### 5.1. Register New Fish
```
Admin → Broodstock Fish → Add
Select container (Broodstock Tank 1)
Set health status = Healthy
Save
```

### 5.2. Transfer Fish Between Tanks
```
Admin → Fish Movements → Add
Fish = #123
From = Broodstock Tank 1
To   = Broodstock Tank 2
Notes = "Weight sample taken before move."
Save (auto validates capacity)
```

### 5.3. Internal Egg Production
```
Admin → Egg Productions → Add
Source Type = Internal
Pair = Winter Plan – Male #45 × Female #67
Egg Count = 12 000
Destination Station = Station A
Save (progeny count auto-updates)
```

### 5.4. External Egg Acquisition
```
Admin → External Egg Batches → Add
Supplier = "Nordic Eggs AS"
Batch No. = N-2025-04
Egg Count = 80 000 (set in linked Egg Production form)
Save
```

### 5.5. Assign Eggs to Grow-out Batch
```
Admin → Batch Parentages → Add
Egg Production = EB-EXT-20250420-123
Batch = TEST-001
Save
```

---

## 6. REST API Usage (v1)
Authentication: `Bearer <JWT>` or session cookie.

### 6.1. List Fish
```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/broodstock/fish/
```

### 6.2. Move Fish (custom action)
```bash
curl -X POST -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"to_container": 5, "notes": "health check"}' \
     http://localhost:8000/api/v1/broodstock/fish/123/move/
```

### 6.3. Produce Eggs Internally
```bash
curl -X POST -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"pair": 12, "egg_count": 15000}' \
     http://localhost:8000/api/v1/broodstock/egg-productions/
```

Full endpoint list is available at `/swagger/` or `/redoc/`.

---

## 7. Best Practices & Tips
* Keep container capacities updated – prevents invalid transfers.
* Close **Breeding Plans** (set end-date) to prevent new pairs.
* Use **Maintenance Tasks** to schedule tank cleaning ahead of breeding.
* Regularly review **history** tabs for audit requirements.

---

## 8. Troubleshooting
| Issue | Resolution |
|-------|------------|
| "Destination container is not a broodstock container" | Ensure the container type name contains "Broodstock". |
| Capacity exceeded | Check `max_biomass_kg` on the container or split the population. |
| Duplicate external batch number | Each supplier+batch number must be unique. |
| Egg assignment error | Verify batch lifecycle stage is Egg/Alevin/Fry and station matches. |

---

## 9. Appendix – Service-Layer Helpers (Dev-Only)
Developers can import services:
```python
from apps.broodstock.services import BroodstockService, EggManagementService
```
Key methods:
* `move_fish(fish, to_container, user)`
* `bulk_move_fish(fish_ids, from_container, to_container, user)`
* `create_breeding_pair(male_fish, female_fish, plan)`
* `produce_internal_eggs(breeding_pair, egg_count)`
* `acquire_external_eggs(supplier, batch_number, egg_count)`
* `assign_eggs_to_batch(egg_production, batch)`

All methods raise `ValidationError` on failure and are wrapped in DB transactions.

---

**Enjoy managing your broodstock with AquaMind!** 