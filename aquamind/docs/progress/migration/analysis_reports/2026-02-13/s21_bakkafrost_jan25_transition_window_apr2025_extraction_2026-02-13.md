# S21 Bakkafrost S-21 jan 25 transition-window extraction (Apr 2025)

Date: 2026-02-13  
Scope: extract deterministic values visible in user-supplied Jan-Apr and Apr-May swimlane screenshots for `Bakkafrost S-21 jan 25`.

## Inputs

- `/Users/aquarian247/.cursor/projects/Users-aquarian247-Projects/assets/image-e71ea13c-025e-4072-b538-e6857e6e4e81.png` (Jan-Apr Rogn lanes with readable values)
- `/Users/aquarian247/.cursor/projects/Users-aquarian247-Projects/assets/image-4f39e184-6c86-4f41-94a0-acb72f73b6b1.png` (zoom of outgoing R lanes at transition boundary)
- `/Users/aquarian247/.cursor/projects/Users-aquarian247-Projects/assets/image-f21e5f22-3fe5-436c-86ff-0849cee84d06.png` (Apr-May incoming 5M lanes)
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-13/S21_jan25_to_today.csv` (current-state station export, known to have stage-label quality issues)

## Deterministic extraction completed

The following row-level values were legible and transcribed from the Jan-Apr Rogn lanes:

- `R1..R7` `count_start`, `count_delta`, `count_end`
- `R1..R7` `biomass_start_kg`, `biomass_end_kg`
- `R1..R7` `mortality_pct`

Structured output:

- `S21_Bakkafrost_S21_jan25_Rogn_outgoing_snapshot_2026-02-13.csv`

Aggregate outgoing totals at the Apr boundary (Rogn -> next stage):

- `count_end_total = 1,389,877`
- `biomass_end_total = 139.00 kg`

## What is visible but not yet deterministic

- The Apr-May screenshot confirms the `R -> 5M` transition window and 7-to-6 pattern.
- Exact line-level `R* -> 5M*` pairings are visually occluded by crossing transition lines at this zoom.
- User-observed same-day zero-count assignment artifacts (`6` rows around `2 April`) are plausible in this window but cannot be fully enumerated from current pixel-level readability.

## Migration implication

- This evidence is strong enough to model the transition as a stage workflow with aggregate conservation checks.
- It is not strong enough yet for deterministic per-line source-target action mapping without either:
  - clearer per-transition images, or
  - operation-linked transfer/action extract rows.

