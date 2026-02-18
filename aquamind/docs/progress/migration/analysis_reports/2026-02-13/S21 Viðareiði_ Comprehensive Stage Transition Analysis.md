# S21 Viðareiði: Comprehensive Stage Transition Analysis

**Author:** Manus AI  
**Date:** February 13, 2026  
**Station:** S21 Viðareiði  
**Batch Analyzed:** Bakkafrost S-21 jan 25 (Input: 25.01)

---

## 1. Introduction

This document presents a comprehensive analysis of the "Bakkafrost S-21 jan 25" batch at the S21 Viðareiði freshwater station. The analysis is based on the provided FishTalk swimlane visualization and corresponding CSV data [1, 2]. The primary goal is to deconstruct the batch's lifecycle progression and present the data in a structured, machine-readable format suitable for a coding agent to execute the migration into the AquaMind system.

This enriched document consolidates all previously discussed details, including granular container-level data, full JSON schemas for agent implementation, detailed validation logic, and a step-by-step migration approach. A key finding is a significant data quality issue within the FishTalk CSV export, where production stage labels are incorrect. This document outlines a robust migration strategy that relies on hall-to-stage mapping to ensure data integrity and provides a clear path for handling the in-progress nature of this batch.

---

## 2. S21 Hall to Lifecycle Stage Mapping

The operational flow at station S21 Viðareiði is defined by a clear mapping between its halls and the lifecycle stages of the fish. This mapping is critical for correcting the inaccurate stage data found in the CSV export.

| Hall Prefix | Lifecycle Stage | Description |
| :--- | :--- | :--- |
| **Rogn** | Egg, Alevin | Initial hatching stage. |
| **A** | Egg, Alevin | The starting point for the "Bakkafrost S-21 jan 25" batch. |
| **5M** | Fry | The first feeding stage, following the initial growth in Hall A. |
| **BA, BB** | Parr | The primary growth stage for parr. |
| **C, D, B** | Smolt | The smoltification stage. The use of "B" hall appears to be for overflow or specific smolt groups. |
| **E, F** | Post-Smolt | The final freshwater stage before transfer to sea. |

---

## 3. Critical Finding: Data Quality of Stage Labels

The most significant challenge identified for this migration is the unreliability of the `Production Stage` field in the provided CSV data. 

> **Observation:** The CSV file [2] labels all 10 currently active containers for the "Bakkafrost S-21 jan 25" batch as being in the "Fry" stage.

This is demonstrably incorrect. Based on the established hall-to-stage mapping, the containers are located in halls C, D, and B, which correspond to the **Smolt** stage. The batch has been in these halls since August 2025, making a "Fry" designation impossible.

**Conclusion:** The `Production Stage` data from the FishTalk CSV export cannot be trusted for this station. The migration logic **must ignore this field** and instead rely on programmatic stage inference based on the hall-to-stage mapping.

---

## 4. Detailed Lifecycle Progression Analysis

The "Bakkafrost S-21 jan 25" batch has progressed through four distinct lifecycle stages over approximately 13 months and is currently active in the Smolt stage.

### 4.1. Transition 1: Egg/Alevin (A Høll) → Fry (5M Hall)

- **Source Hall:** A Høll
- **Target Hall:** 5M
- **Transition Date:** ~Early April 2025
- **Workflow Type:** Lifecycle Stage Transition
- **Pattern:** 7-to-6 consolidation

#### Source Assignments (A Høll, R1-R7)

| Container | Period | Pop. In | Pop. Out | Biomass In (kg) | Biomass Out (kg) | Mortality % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| A-R1 | Jan 05 - Apr 05 | ~28,000 | ~27,500 | ~0.3 | ~8.0 | ~1.8% |
| A-R2 | Jan 05 - Apr 05 | ~29,000 | ~28,400 | ~0.3 | ~8.5 | ~2.1% |
| A-R3 | Jan 05 - Apr 05 | ~28,500 | ~27,900 | ~0.3 | ~8.2 | ~2.1% |
| A-R4 | Jan 05 - Apr 05 | ~27,800 | ~27,200 | ~0.3 | ~8.0 | ~2.2% |
| A-R5 | Jan 05 - Apr 05 | ~28,200 | ~27,600 | ~0.3 | ~8.1 | ~2.1% |
| A-R6 | Jan 05 - Apr 05 | ~27,500 | ~26,900 | ~0.3 | ~7.9 | ~2.2% |
| A-R7 | Jan 05 - Apr 05 | ~28,000 | ~27,400 | ~0.3 | ~8.0 | ~2.1% |
| **Total** | | **~197,000** | **~192,900** | **~2.1** | **~56.7** | **~2.1%** |

#### Target Assignments (5M Hall, 5M 1-5M 6)

| Container | Period | Pop. In | Pop. Out | Biomass In (kg) | Biomass Out (kg) | Mortality % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 5M-1 | Apr 05 - Jun 01 | ~32,000 | ~31,400 | ~9.5 | ~120 | ~1.9% |
| 5M-2 | Apr 05 - Jun 01 | ~32,500 | ~31,800 | ~9.5 | ~122 | ~2.2% |
| 5M-3 | Apr 05 - Jun 01 | ~32,200 | ~31,500 | ~9.5 | ~121 | ~2.2% |
| 5M-4 | Apr 05 - Jun 01 | ~31,800 | ~31,100 | ~9.5 | ~119 | ~2.2% |
| 5M-5 | Apr 05 - Jun 01 | ~32,100 | ~31,400 | ~9.5 | ~120 | ~2.2% |
| 5M-6 | Apr 05 - Jun 01 | ~32,300 | ~31,600 | ~9.5 | ~121 | ~2.2% |
| **Total** | | **~192,900** | **~188,800** | **~57.0** | **~723** | **~2.1%** |

### 4.2. Transition 2: Fry (5M Hall) → Parr (BA/BB Halls)

- **Source Hall:** 5M
- **Target Halls:** BA, BB
- **Transition Date:** ~Early June 2025
- **Workflow Type:** Lifecycle Stage Transition
- **Pattern:** 6-to-10 expansion

#### Target Assignments (BA/BB Halls)

| Container | Period | Pop. In | Pop. Out | Biomass In (kg) | Biomass Out (kg) | Mortality % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| BA-1 | Jun 01 - Aug 15 | ~19,000 | ~18,600 | ~72 | ~280 | ~2.1% |
| BA-2 | Jun 01 - Aug 15 | ~18,800 | ~18,400 | ~72 | ~275 | ~2.1% |
| ... | ... | ... | ... | ... | ... | ... |
| BB-5 | Jun 01 - Aug 15 | ~18,900 | ~18,500 | ~72 | ~277 | ~2.1% |
| **Total** | | **~189,600** | **~185,600** | **~722** | **~2,782** | **~2.1%** |

### 4.3. Transition 3: Parr (BA/BB Halls) → Smolt (C/D/B Halls)

- **Source Halls:** BA, BB
- **Target Halls:** C, D, B
- **Transition Date:** ~Mid-August 2025
- **Workflow Type:** Lifecycle Stage Transition
- **Pattern:** 10-to-10 stable transfer
- **Status:** This is the **current active stage**.

#### Target Assignments (C/D/B Halls - CURRENT STATE)

| Container | Period Start | Period End | Pop. In | Pop. Out (Current) | Biomass In (kg) | Biomass Out (kg) (Current) | Mortality % (Current) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| B01 | ~2025-08-15 | **Ongoing** | ~18,500 | ~18,100 | ~278 | ~1,200 | ~2.2% |
| B13 | ~2025-08-15 | **Ongoing** | ~18,600 | ~18,200 | ~279 | ~1,210 | ~2.2% |
| C09 | ~2025-08-15 | **Ongoing** | ~18,700 | ~18,300 | ~280 | ~1,215 | ~2.1% |
| C12 | ~2025-08-15 | **Ongoing** | ~18,400 | ~18,000 | ~276 | ~1,195 | ~2.2% |
| D1 | ~2025-08-15 | **Ongoing** | ~18,800 | ~18,400 | ~281 | ~1,220 | ~2.1% |
| D2 | ~2025-08-15 | **Ongoing** | ~18,500 | ~18,100 | ~278 | ~1,200 | ~2.2% |
| D3 | ~2025-08-15 | **Ongoing** | ~18,600 | ~18,200 | ~279 | ~1,210 | ~2.2% |
| D4 | ~2025-08-15 | **Ongoing** | ~18,700 | ~18,300 | ~280 | ~1,215 | ~2.1% |
| D5 | ~2025-08-15 | **Ongoing** | ~18,400 | ~18,000 | ~276 | ~1,195 | ~2.2% |
| D6 | ~2025-08-15 | **Ongoing** | ~18,500 | ~18,100 | ~278 | ~1,200 | ~2.2% |
| **Total** | | | **~185,700** | **~181,700** | **~2,785** | **~12,060** | **~2.2%** |

### 4.4. Transition 4: Smolt (C/D/B Halls) → Post-Smolt (E/F Halls)

- **Status:** **PENDING**. This transition has not yet occurred.

---

## 5. Migration Logic and Data Structures

### 5.1. Core Migration Principles

1.  **Stage Inference is Mandatory:** The agent must determine the lifecycle stage of each container assignment by mapping the container's hall prefix to the correct stage. The CSV stage label must be disregarded.
2.  **Handle In-Progress Batches:** The current Smolt stage assignments are active. The migration must create `BatchContainerAssignment` records with a `NULL` end date and reflect the latest known population and biomass as the current state.
3.  **Standard Hall-to-Hall Transitions:** All transitions are standard `Lifecycle Stage Transition Workflows`.

### 5.2. Full JSON Data Structure for Agent

This JSON schema represents the complete set of transitions for the batch. The agent should generate this structure.

```json
{
  "batch_key": {
    "name": "Bakkafrost S-21 jan 25",
    "input_number": "25.01",
    "year_class": 2025,
    "station": "S21 Viðareiði"
  },
  "stage_transitions": [
    {
      "transition_id": 1,
      "stage_from": "Egg/Alevin",
      "stage_to": "Fry",
      "hall_from": "A",
      "hall_to": "5M",
      "transition_date": "2025-04-05",
      "workflow_type": "lifecycle_stage_transition",
      "source_assignments": [
        {
          "container_name": "A-R1",
          "period_start": "2025-01-05",
          "period_end": "2025-04-05",
          "population_in": 28000,
          "population_out": 27500,
          "biomass_in_kg": 0.3,
          "biomass_out_kg": 8.0,
          "mortality_pct": 1.8
        }
        // ... 6 more source containers
      ],
      "target_assignments": [
        {
          "container_name": "5M-1",
          "period_start": "2025-04-05",
          "period_end": "2025-06-01",
          "population_in": 32000,
          "population_out": 31400,
          "biomass_in_kg": 9.5,
          "biomass_out_kg": 120.0,
          "mortality_pct": 1.9
        }
        // ... 5 more target containers
      ]
    },
    {
      "transition_id": 2,
      "stage_from": "Fry",
      "stage_to": "Parr",
      "hall_from": "5M",
      "hall_to": "BA, BB",
      "transition_date": "2025-06-01",
      "workflow_type": "lifecycle_stage_transition",
      "source_assignments": [ /* 6 source containers from 5M */ ],
      "target_assignments": [ /* 10 target containers in BA/BB */ ]
    },
    {
      "transition_id": 3,
      "stage_from": "Parr",
      "stage_to": "Smolt",
      "hall_from": "BA, BB",
      "hall_to": "C, D, B",
      "transition_date": "2025-08-15",
      "workflow_type": "lifecycle_stage_transition",
      "source_assignments": [ /* 10 source containers from BA/BB */ ],
      "target_assignments": [
        {
          "container_name": "B01",
          "period_start": "2025-08-15",
          "period_end": null,
          "is_active": true,
          "population_in": 18500,
          "population_out": 18100,
          "biomass_in_kg": 278.0,
          "biomass_out_kg": 1200.0,
          "mortality_pct": 2.2
        }
        // ... 9 more active target containers
      ]
    }
  ]
}
```

### 5.3. Detailed Validation Logic

-   **Population and Biomass Conservation:** The agent must validate that the total population and biomass are conserved across each transition, within a small tolerance (<2%) for transfer mortality.
-   **Mortality Reconciliation:** Calculated mortality (`pop_in - pop_out`) must align with the stated `mortality_pct` for each assignment.
-   **Timeline Continuity:** The end date of one stage's assignments must align with the start date of the next.
-   **Stage-Hall Consistency:** A new, critical check for S21. After inferring stages from halls, the agent must verify that the sequence is biologically correct (e.g., Egg → Fry → Parr → Smolt).

    ```python
    def validate_stage_hall_consistency(batch_transitions):
        """
        Ensure that inferred stages follow the expected biological progression.
        """
        expected_progression = ["Egg/Alevin", "Fry", "Parr", "Smolt", "Post-Smolt"]
        for i, transition in enumerate(batch_transitions):
            stage_from = transition["stage_from"]
            stage_to = transition["stage_to"]
            from_idx = expected_progression.index(stage_from)
            to_idx = expected_progression.index(stage_to)
            assert to_idx == from_idx + 1, f"Stage transition {stage_from} -> {stage_to} is out of order."
    ```

---

## 6. Conclusion

The migration of the "Bakkafrost S-21 jan 25" batch is defined by two key characteristics: a standard hall-to-hall lifecycle progression and a critical data quality issue in the source CSV data. The migration strategy is therefore straightforward in its workflow logic but requires robust data correction capabilities.

**Key Recommendations for the Migration Agent:**

1.  **Implement Hall-Based Stage Inference:** This is the most critical requirement. The agent must contain a mapping of S21 hall prefixes to AquaMind lifecycle stages and use this to override the incorrect data from the FishTalk CSV.
2.  **Model the Current State Correctly:** The migration must create the 10 active Smolt assignments with `NULL` end dates to reflect that the batch is in-progress.
3.  **Validate Stage Progression:** After inferring stages, the agent should confirm that the batch progresses through the expected lifecycle sequence without skipping stages.
4.  **Document the Data Quality Issue:** The migration logs should clearly state that the FishTalk CSV stage labels were overridden and why, providing an audit trail for the data transformation.

By following these recommendations, the agent can successfully migrate this complex, in-progress batch while correcting for known data quality issues in the source system.

---

## 7. References

[1] `S21_jan25_to_today.jpg` (FishTalk swimlane visualization)  
[2] `S21_jan25_to_today.csv` (FishTalk data export)
