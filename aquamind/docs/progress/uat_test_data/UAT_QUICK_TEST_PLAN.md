# AquaMind UAT Quick Test Plan

**Date**: January 12, 2026  
**Purpose**: Validate core system functionality using UAT-optimized test data  
**Scope**: Main workflows only - not comprehensive UAT

---

## Test Data Overview

| Metric | Value |
|--------|-------|
| Total Active Batches | 51 |
| Completed Batches | 85 |
| Data Freshness | TODAY (Jan 12, 2026) |
| PlannedActivities | 1,020 |

---

## Test Case 1: Batch List & Details View

**Goal**: Verify batch browsing and detail pages work correctly

### Steps
1. Navigate to Batch List page
2. Verify batches are displayed with correct status indicators
3. Apply filters:
   - Filter by Stage: `Smolt`
   - Filter by Status: `ACTIVE`
4. Click on batch **SCO-UAT-358** (ID: 2946)
5. Verify batch detail page shows:
   - Lifecycle stage: "Atlantic Salmon - Smolt (Stage 4)"
   - Days in production: ~358
   - Active assignments listed

### Specific Batches to Check
| Batch | ID | Stage | Days | Purpose |
|-------|-----|-------|------|---------|
| SCO-UAT-025 | 3010 | Egg&Alevin | 25 | Early stage batch |
| SCO-UAT-358 | 2946 | Smolt | 358 | Near FW→Sea transition |
| FAR-UAT-780 | 2977 | Adult | 780 | Near harvest |

---

## Test Case 2: Executive Dashboard

**Goal**: Verify dashboard displays correct batch distribution and KPIs

### Steps
1. Navigate to Executive Dashboard
2. Verify the 3-tier display:
   - **PLANNED**: Batches with planned scenarios
   - **PROJECTED**: Batches with live projections
   - **NEEDS_PLANNING**: Batches requiring attention
3. Check stage distribution chart shows batches across all 6 stages
4. Verify KPIs:
   - Active batch count: ~51
   - Upcoming activities count
   - Overdue activities: should be 0

### Expected Distribution
```
Egg&Alevin:  10 batches
Fry:          8 batches
Parr:         8 batches
Smolt:        8 batches
Post-Smolt:   8 batches
Adult:        9 batches
```

---

## Test Case 3: Live Forward Projection

**Goal**: Verify projection engine generates forward projections from current state

### Steps
1. Navigate to a batch detail page: **SCO-UAT-480** (ID: 2978)
2. View the Live Forward Projection section/tab
3. Verify projection shows:
   - Current state (from ActualDailyAssignmentState)
   - Forward projection extending to harvest
   - Growth curve visualization
4. Check projection parameters:
   - Temperature bias applied
   - TGC-based growth calculation

### Batches with Good Projection Data
| Batch | ID | Stage | Days | Why Test |
|-------|-----|-------|------|----------|
| SCO-UAT-480 | 2978 | Adult | 480 | Good growth history |
| FAR-UAT-358 | 2951 | Smolt | 358 | Critical transition point |
| SCO-UAT-195 | 2930 | Parr | 195 | Mid-lifecycle |

---

## Test Case 4: Growth Analysis / ActualDailyAssignmentState

**Goal**: Verify daily state records are being tracked

### Steps
1. Navigate to batch **FAR-UAT-285** (ID: 2932)
2. View growth/daily state data
3. Verify records exist for recent dates (up to Jan 12, 2026)
4. Check key metrics are populated:
   - Population count
   - Average weight
   - Biomass
   - Cumulative mortality

### Assignment IDs to Check
| Batch | Assignment ID | Container |
|-------|---------------|-----------|
| FAR-UAT-285 | 93631 | FI-FW-01-D-C06 |
| SCO-UAT-358 | 94206 | S-FW-04-D-C01 |

---

## Test Case 5: Stage Transition Workflow (Egg&Alevin → Fry)

**Goal**: Test the first stage transition - First Feeding

### Target Batches (Ready for Transition)
| Batch | ID | Days | Stage | Assignments |
|-------|-----|------|-------|-------------|
| SCO-UAT-088 | 2914 | 88 | Egg&Alevin | 92497, 92496 |
| FAR-UAT-088 | 2915 | 88 | Egg&Alevin | 92507, 92506 |
| SCO-UAT-082 | 2911 | 82 | Egg&Alevin | 92346, 92355 |

### Steps
1. Navigate to batch **SCO-UAT-088** (ID: 2914)
2. Locate the stage transition or transfer workflow action
3. Initiate transition to Fry stage
4. Verify:
   - Workflow is created
   - Stage updates after completion
   - Container assignments update if needed

---

## Test Case 6: FW→Sea Transfer Workflow (Smolt → Post-Smolt) ⭐ CRITICAL

**Goal**: Test the most important transfer - Freshwater to Sea transition

### Target Batches (Ready for FW→Sea)
| Batch | ID | Days | Current Stage | Current Container |
|-------|-----|------|---------------|-------------------|
| SCO-UAT-358 | 2946 | 358 | Smolt | S-FW-04-D-C01 |
| FAR-UAT-358 | 2951 | 358 | Smolt | FI-FW-04-D-C10 |

### Steps
1. Navigate to batch **SCO-UAT-358** (ID: 2946)
2. This batch is at Day 358 - ready for FW→Sea transition (typical: 360 days)
3. Initiate Transfer Workflow:
   - Source: Freshwater containers (S-FW-04-D-*)
   - Destination: Sea cages (S-SEA-*)
   - Stage change: Smolt → Post-Smolt
4. Walk through multi-step workflow:
   - Workflow creation
   - Population count verification
   - Weight sampling (if required)
   - Execute transfer
   - Confirm completion
5. Verify after completion:
   - Batch stage is now "Post-Smolt"
   - New assignments in sea containers
   - Old freshwater assignments deactivated

### Assignment Details
```
SCO-UAT-358 current assignments:
  - Assignment 94206: S-FW-04-D-C01 (Scotland Freshwater)
  - Assignment 94212: S-FW-04-D-C07 (Scotland Freshwater)

FAR-UAT-358 current assignments:
  - Assignment 94615: FI-FW-04-D-C10 (Faroes Freshwater)
  - Assignment 94612: FI-FW-04-D-C07 (Faroes Freshwater)
```

---

## Test Case 7: Harvest-Ready Batch

**Goal**: Verify batch near harvest shows appropriate data

### Target Batch
| Batch | ID | Days | Stage | Weight (expected) |
|-------|-----|------|-------|-------------------|
| FAR-UAT-780 | 2977 | 780 | Adult | ~5kg+ |

### Steps
1. Navigate to batch **FAR-UAT-780** (ID: 2977)
2. This is the oldest active batch at Day 780
3. Verify:
   - Expected weight is approaching harvest size (~5-6kg)
   - Forward projection shows harvest window
   - Biomass calculations are reasonable
4. Check harvest planning:
   - PlannedActivity for harvest should exist
   - Harvest projections visible

### Assignment Details
```
FAR-UAT-780 assignments:
  - Assignment 96015: FI-SEA-03-Ring-08
  - Assignment 96013: FI-SEA-03-Ring-05
```

---

## Test Case 8: Planned Activities

**Goal**: Verify PlannedActivities system is working

### Steps
1. Navigate to PlannedActivities or Operations view
2. Verify activities are displayed with correct status
3. Check activity distribution:
   - Feed changes: ~306
   - Sampling: ~255
   - Transfers: ~255
   - Treatments: ~102
   - Vaccinations: ~51
   - Harvests: ~51
4. Filter for "Upcoming 7 days" - should show ~29 activities
5. Verify no overdue activities (should be 0)

---

## Test Case 9: Environmental Monitoring

**Goal**: Verify environmental readings are associated with containers

### Steps
1. Navigate to any container with active batches
2. Check environmental readings:
   - Temperature
   - Oxygen levels
   - Other sensors
3. Verify readings have recent timestamps (within last 1-2 days)

### Containers to Check
| Container | Has Batch | Notes |
|-----------|-----------|-------|
| S-FW-01-A-C05 | SCO-UAT-025 | Early stage freshwater |
| FI-SEA-03-Ring-08 | FAR-UAT-780 | Harvest-ready sea cage |

---

## Test Case 10: Multi-Company Data Isolation

**Goal**: Verify Scotland and Faroes data are properly separated

### Steps
1. Switch context/view to Scotland company
2. Verify only SCO-* batches are visible
3. Switch to Faroes company  
4. Verify only FAR-* batches are visible
5. Check cross-company operations are blocked

### Key Batches by Company
**Scotland (SCO)**:
- SCO-UAT-025, SCO-UAT-088, SCO-UAT-358, etc.

**Faroes (FAR)**:
- FAR-UAT-025, FAR-UAT-088, FAR-UAT-358, etc.

---

## Quick Reference: Key Batches

### By Lifecycle Stage
| Stage | Scotland Batch | Faroes Batch | Days |
|-------|----------------|--------------|------|
| Egg&Alevin (early) | SCO-UAT-025 (3010) | FAR-UAT-025 (2899) | 25 |
| Egg&Alevin (transition) | SCO-UAT-088 (2914) | FAR-UAT-088 (2915) | 88 |
| Fry (transition) | SCO-UAT-175 (2926) | FAR-UAT-175 (2927) | 175 |
| Parr (mid) | SCO-UAT-195 (2930) | FAR-UAT-195 (2931) | 195 |
| Smolt (FW→Sea) ⭐ | SCO-UAT-358 (2946) | FAR-UAT-358 (2951) | 358 |
| Post-Smolt | SCO-UAT-448 (2974) | FAR-UAT-448 (2897) | 448 |
| Adult (mid) | SCO-UAT-480 (2978) | FAR-UAT-480 (2925) | 480 |
| Adult (harvest) | SCO-UAT-720 (2947) | FAR-UAT-780 (2977) | 720/780 |

---

## Pass Criteria

- [ ] Batch list loads and filters work
- [ ] Batch details display correctly
- [ ] Executive Dashboard shows proper distribution
- [ ] Live Forward Projection generates for active batches
- [ ] Growth data (ActualDailyAssignmentState) is current
- [ ] At least one stage transition completes successfully
- [ ] FW→Sea transfer workflow can be initiated
- [ ] PlannedActivities display with correct counts
- [ ] Environmental readings are accessible
- [ ] Multi-company isolation works

---

## Notes

- This is a quick validation test, not comprehensive UAT
- UI specifics (button locations, exact navigation) may vary - explore as needed
- Focus on data flow and business logic correctness
- Report any blocking issues immediately
