# Scenario Planning Data Model Fixes

## 🔴 Critical Issue Discovered

**Temperature Profile Reusability Flaw**

During PRD Section 3.3.1 compliance review, a fundamental data model issue was identified:

**Problem**: `TemperatureReading.reading_date` uses calendar dates instead of relative day numbers, preventing profile reusability across scenarios with different start dates.

**Impact**: Users cannot create reusable temperature patterns (e.g., "Faroe Islands Standard Year") and apply them to multiple scenarios starting on different dates.

**Status**: Implementation plan created, ready for execution in next session

---

## 📋 Files in This Directory

### TEMPERATURE_PROFILE_DAY_NUMBER_FIX.md

**Comprehensive implementation plan** for fixing the temperature profile data model.

**Contains**:
- Problem statement with examples
- Sanity check of all scenario models (TGC, FCR, Mortality) → ✅ All correct
- Complete implementation plan (4 phases, 2-3 hours)
- Step-by-step migration strategy
- Code changes with before/after examples
- Testing plan (backend + frontend)
- Expected outcomes demonstration
- Files to modify checklist
- Quick start guide for next session

**Key Finding**: Only TemperatureReading needs fixing. TGC, FCR, and Mortality models have correct designs.

---

## 🎯 Quick Summary for Next Agent

**What to do**:
1. Read `TEMPERATURE_PROFILE_DAY_NUMBER_FIX.md` completely
2. Understand: `reading_date` (DateField) → `day_number` (IntegerField)  
3. Why: Enables profile reusability across scenarios with different start dates
4. Follow Phase 1-4 implementation steps
5. Test reusability: Two scenarios, different start dates, same Day 1 temperature

**Expected time**: 2-3 hours for complete fix + testing

**Critical**: Must complete before production launch or any real temperature data creation

---

## ✅ Other Models - Status

**Verified against PRD Section 3.3.1**:

- ✅ **TGCModel**: Correct (constants + profile reference, not date-dependent)
- ✅ **FCRModel/FCRModelStage**: Correct (stage-based, duration in relative days)
- ✅ **MortalityModel/Stage**: Correct (percentage-based, not date-dependent)
- ✅ **Scenario**: Correct (start_date is intentionally calendar-specific)
- ✅ **ScenarioProjection**: Correct (uses day_number pattern already!)

**Only TemperatureReading is broken.**

---

**Created**: 2025-10-13  
**Priority**: 🔴 CRITICAL  
**Status**: Plan ready, awaiting implementation


