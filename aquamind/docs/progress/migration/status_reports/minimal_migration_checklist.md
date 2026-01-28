# Minimal Migration Checklist (Crawl Phase)

**Goal:** Migrate one batch end‑to‑end by honoring chronology and using the smallest authoritative dataset.

---

## 0) Ground Rules
- **Chronology is king.** No pre‑emptive feed inventory or retroactive events.
- **Use raw events as truth.** Recompute derived daily states in AquaMind.
- **Master data is not time‑bounded** (load fully unless clearly obsolete).

---

## 1) Master Data (Load First)
### Infrastructure & Org
- `Containers` (ContainerID, ContainerName, ContainerType, ContainerSystemType)
- `ContainerWaterTypeHistory` (ContainerID, WaterTypeID, Start/End)
- `ContainerPhysicsHistory` (ContainerID, ShapeID, Start/End)
- `grouped_organisation` / org units (from extract)

### Species & Stages
- `ProductionStages` (StageID, names)
- `PopulationProductionStages` (PopulationID, StageID, StartTime) *(used later for lifecycle validation)*

### Health Lookups
- `MortalityCauses`, `MortalityCategories`, `MortalityCauseGroup`
- `TreatmentCategory`, `TreatmentReasons`
- `LiceStages`, `LiceStageGroups`, `LiceStageGroupMembership` *(if lice is included)*

### Feed & Inventory Lookups
- `FeedTypes`/`Feed`
- `FeedBatch`
- `FeedReceptions`, `FeedReceptionBatches`
- `FeedStoreUnitAssignment`
- `FeedTransferCauses`

---

## 2) Batch Identity (Choose One Batch)
- **Primary key**: `Ext_Inputs_v2` (InputName + InputNumber + YearClass)
- Link through: `Ext_Inputs_v2.PopulationID` → `Populations` → `Action`/`Operations`

---

## 3) Core Event Tables (Chronological Order)
1. **Creation / Input events**
   - `Ext_Inputs_v2` (egg inputs, StartTime)
   - `Populations`
2. **Transfers / Assignments**
   - `PopulationLink`, `SubTransfers`, `OperationProductionStageChange` *(workflow)*
3. **Feeding**
   - `Feeding` (ActionID)
   - Resolve time via `Operations.StartTime` or `Feeding.OperationStartTime`
4. **Mortality**
   - `Mortality`, plus `Culling`, `Escapes` if losses included
5. **Treatments / Health**
   - `Treatment`

---

## 4) Exclude/Defer (Derived Snapshots)
- `PublicPlanStatusValues`, `PublicMortalityStatus`, `PublicStatusValues`
- `StatusCalculation`, `PlanStatusFeedUse`, `PopDistCost`
- Use for validation only, not migration

---

## 5) Validation Gates (Before Next Phase)
- **Single geography** per batch (no mixed FW/Sea without explicit linkage)
- **Lifecycle ordering**: no Egg/Fry after Adult on same batch timeline
- **Chronology**: event times monotonic within workflows
- **Feed chain**: purchase → storage → feeding order is coherent

---

## 6) If It Breaks
- Re‑validate cohort selection (FW/Sea split, year‑class parsing)
- Check rerun accumulation (clear batch assignments before rerun)
- Re‑run with tighter creation window or cohort filters

---

## Open Questions
- Confirm FishTalk “Project” tables used only for FW→Sea linkage (not finance)
- Decide whether to include lice/treatments in crawl phase or defer

---

**Status:** Drafted 2026‑01‑26. Adjust after first crawl‑phase migration run.
