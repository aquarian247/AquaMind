# S21 Bakkafrost S-21 jan 25 Fry -> Parr mapping (user-confirmed)

Date: 2026-02-13  
Scope: capture deterministic line-level lane mapping for the Fry-to-Parr transition window from user zoom confirmation.

## Source confirmation

User-confirmed exact movement set (after high zoom visual tracing):

- `5M 1 -> A01, A03, A05, B10, B11`
- `5M 2 -> A01, A03, A05, B10, B11`
- `5M 3 -> A01, A05, B10`
- `5M 4 -> A01, A03, B11`
- `5M 5 -> A01, A03, B11`
- `5M 6 -> A01, A03, B11`

Note: upper-right lanes in the original crop were identified as another cohort and excluded.

## Structured artifact

- `S21_Bakkafrost_S21_jan25_Fry_to_Parr_user_confirmed_mapping_2026-02-13.csv`

Edge count:

- total edges: `22`

Source fan-out counts:

- `5M 1`: `5`
- `5M 2`: `5`
- `5M 3`: `3`
- `5M 4`: `3`
- `5M 5`: `3`
- `5M 6`: `3`

Target in-degree counts:

- `A01`: `6`
- `A03`: `5`
- `A05`: `3`
- `B10`: `3`
- `B11`: `5`

## Migration implication

- This resolves topology for `Fry -> Parr` at S21 (`5M` to `A/BA/BB` lanes represented here as `A01/A03/A05/B10/B11`) for this batch.
- Quantitative edge weights (`transferred_count`, `transferred_biomass_kg`) are still pending readable boundary values for this transition window.

