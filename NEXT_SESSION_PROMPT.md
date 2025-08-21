# AquaMind Data Generation - Session 1 Completion Prompt

## Context
You are continuing work on the AquaMind aquaculture management system's data generation module. The previous session completed Phase 0 (orchestration framework) and achieved ~40% completion of Session 1 (Years 1-3 historical data). Your task is to fix the identified issues and complete Session 1.

## Current State
- **Branch**: `feature/data-generation-phase0-session1`
- **Progress**: Session 1 is ~40% complete (420 days of 1095 days processed)
- **Infrastructure**: 548 containers, 140 sensors, 8 batches created
- **Checkpoint**: Available at `scripts/data_generation/checkpoints/session_1_checkpoint.json`

## Critical Issues to Fix

### 1. Missing Sea Cage Infrastructure (CRITICAL UNDER-CAPACITY)
**Problem**: Infrastructure is creating ~20-30 containers when it needs **HUNDREDS**
**Location**: `scripts/data_generation/generators/infrastructure.py`
**Solution**: Scale up infrastructure creation to match Bakkafrost model
```python
# CORRECT SCALE PER GEOGRAPHY:
# - 10-15 sea areas, EACH with 15-25 large sea cages = 150-375 total sea cages
# - 10 freshwater stations, EACH with 5 halls (one per stage)
# - Each hall has stage-specific containers (50 trays, 40 fry tanks, etc.)
# Total containers needed: 1000+ freshwater containers, 200+ sea cages
```

### 2. Container Capacity Bottlenecks (ROOT CAUSE: INFRASTRUCTURE SCALE)
**Problem**: Massive under-capacity - creating 548 containers when need **2000+**
**Symptoms**: Warnings "No free containers..." for all container types
**Solution**: 
- Scale infrastructure to Bakkafrost levels (see corrected requirements above)
- With 25 active batches, need sufficient containers for parallel operations
- Implement proper hall-based organization in freshwater stations
- Each freshwater station needs 5 halls with stage-specific containers

### 3. Environmental Readings Not Created
**Problem**: 0 environmental readings being generated despite 140 sensors
**Location**: `scripts/data_generation/generators/environmental.py`
**Debug Steps**:
1. Check if `_flush_buffer()` is being called
2. Verify `batch_buffer` is accumulating readings
3. Ensure `bulk_create` is executing
4. Check for silent exceptions in reading generation

### 4. Batch Transfer Logic
**Problem**: Batches can't progress due to no available containers
**Location**: `scripts/data_generation/generators/batch.py` line ~380-410
**Solution**: Implement container availability checking before transfers

## Production Parameters (Bakkafrost Model)
- **Annual Production**: 100,000 tons filleted salmon
- **Whole Fish**: ~143,000 tons/year
- **Fish Count**: 28.6 million fish/year
- **Survival Rate**: 80% from egg to harvest
- **Eggs Needed**: 35.7 million eggs/year
- **Batches per Year**: ~10 reaching harvest
- **Active Batches**: ~25 (10 × 2.5 year cycle)
- **Batch Size**: 3-3.5 million eggs

## Infrastructure Requirements (CORRECTED - Bakkafrost Scale)

**PER GEOGRAPHY** (assuming 1-2 geographies total):
- **10-15 Sea Areas**: Each with 15-25 large sea cages = **150-375 sea cages per geography**
- **10 Freshwater Stations**: Each with 5 halls (one per lifecycle stage)

**PER FRESHWATER STATION** (10 stations × quantities below = total per geography):
```
Stage/Hall         Containers per Station    Total per Geography
-----------------------------------------------------------------
Egg/Alevin Hall    ~50 trays                 500 trays
Fry Hall           ~40 fry tanks             400 fry tanks
Parr Hall          ~30 parr tanks            300 parr tanks
Smolt Hall         ~15 smolt tanks           150 smolt tanks
Post-Smolt Hall    ~12 post-smolt tanks      120 post-smolt tanks
                   + Pre-Transfer Tanks      ~20-30 pre-transfer
```

**FEED INFRASTRUCTURE**:
- **1-2 feed silos per hall** = 50-100 feed silos per geography
- **2-3 feed barges per sea area** = 20-45 feed barges per geography

⚠️ **THIS IS THE ROOT CAUSE**: Current implementation creates maybe 20-30 containers of each type when it should create **HUNDREDS**!

**IMPORTANT BUG TO FIX**: The batch.py generator is hardcoding stage durations instead of using the correct values from `generation_params.py`. Fix line 324-330 in `batch.py` to use `GP.STAGE_DURATIONS` instead of hardcoded values.

**CRITICAL CORRECTION - POST-SMOLT IS FRESHWATER**: There's a fundamental error throughout the codebase treating post-smolt as a sea phase. POST-SMOLT IS ACTUALLY A FRESHWATER STAGE that occurs in freshwater stations (in halls with large tanks). This affects:
- Container types: Post-smolt uses large freshwater tanks, NOT sea cages
- Environmental parameters: Should be freshwater conditions (salinity=0), not seawater
- Infrastructure: Post-smolt facilities are in freshwater stations, not sea sites
- The transition to sea happens AFTER post-smolt, when moving to grow-out phase
- Pre-Transfer Tanks are used at the END of post-smolt, preparing for sea transfer

Check and fix:
- `generation_params.py` - Container progression for post-smolt
- `infrastructure.py` - Ensure post-smolt containers are in freshwater stations
- `environmental.py` - Post-smolt should have freshwater parameters
- `batch.py` - Transfer logic for post-smolt to grow-out transition

## Commands to Use

```bash
# Check current state
py manage.py shell -c "from apps.infrastructure.models import Container, ContainerType; [(ct.name, Container.objects.filter(container_type=ct).count()) for ct in ContainerType.objects.all()]"

# Clear and restart
py scripts/data_generation/clear_data.py --quick
py scripts/data_generation/run_generation.py --session=1

# Resume from checkpoint
py scripts/data_generation/run_generation.py --resume

# Monitor progress
Get-Content scripts/data_generation/logs/*.log -Tail 50 | Select-String "Processed|ERROR|WARNING"
```

## Success Criteria
1. ✅ Complete 1095 days (3 years) of data generation
2. ✅ No container capacity warnings after day 500
3. ✅ Environmental readings > 3 million records
4. ✅ All 8 initial batches progress through lifecycle stages
5. ✅ Feed events match expected feeding rates
6. ✅ Memory usage stays under 500MB
7. ✅ Checkpoint saves allow resume on interruption

## Testing Approach
1. Fix sea cage infrastructure first
2. Run for 100 days to verify containers
3. Fix environmental readings
4. Run for 500 days to verify batch transfers
5. Complete full 1095 days
6. Validate data quality

## Important Files
- `scripts/data_generation/generators/infrastructure.py` - Add sea cages
- `scripts/data_generation/generators/environmental.py` - Fix readings
- `scripts/data_generation/generators/batch.py` - Fix transfers
- `scripts/data_generation/config/generation_params.py` - Adjust parameters
- `aquamind/docs/database/data_model.md` - Database schema reference

## Notes
- The Django models use different field names than expected (e.g., `active` not `is_active`)
- Always check actual model definitions in `apps/*/models/`
- Use `bulk_create` for performance with large datasets
- Environmental readings must be stored in TimescaleDB hypertables
- Container assignments have a unique constraint on active batch-container pairs

## Final Deliverable
Once Session 1 completes successfully:
1. Update `scripts/data_generation/IMPLEMENTATION_PLAN.md` 
2. Commit changes with clear message
3. Update PR with completion status
4. Close Session 1 GitHub issue
5. Prepare for Session 2 (Years 4-6)

Good luck! The foundation is solid - you just need to fix these specific issues to complete Session 1.
