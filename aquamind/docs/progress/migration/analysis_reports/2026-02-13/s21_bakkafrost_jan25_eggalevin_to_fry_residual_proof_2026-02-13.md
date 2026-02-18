# S21 Bakkafrost S-21 jan 25 Egg&Alevin -> Fry residual proof

Date: 2026-02-13  
Scope: validate line-level mapping hypothesis for `R1..R7` (Rogn) to `5M 1..5M 6` (Fry) using extracted boundary values from image evidence.

## Input values used

Outgoing at Rogn boundary:

- `R1=200,364`
- `R2=209,198`
- `R3=215,280`
- `R4=198,185`
- `R5=195,865`
- `R6=191,417`
- `R7=179,568`

Incoming at Fry boundary:

- `5M 1=230,292`
- `5M 2=239,126`
- `5M 3=245,208`
- `5M 4=228,113`
- `5M 5=225,793`
- `5M 6=221,345`

## Arithmetic result

Assume direct mapping:

- `R1 -> 5M 1`
- `R2 -> 5M 2`
- `R3 -> 5M 3`
- `R4 -> 5M 4`
- `R5 -> 5M 5`
- `R6 -> 5M 6`

Residual per target:

- `5M i - R(i)` is exactly `29,928` for all six targets.

Therefore:

- residual total = `6 * 29,928 = 179,568 = R7`

This proves `R7` splits evenly across all six `5M` containers in count terms.

## Biomass cross-check

Outgoing biomass (kg):

- `R1=20.04`, `R2=20.92`, `R3=21.53`, `R4=19.82`, `R5=19.59`, `R6=19.14`, `R7=17.96`

Incoming biomass (kg):

- `5M 1=23.03`, `5M 2=23.91`, `5M 3=24.52`, `5M 4=22.81`, `5M 5=22.58`, `5M 6=22.13`

Per-target residual biomass:

- each target residual is `2.99 kg` (to 2 decimal precision in UI)

Residual biomass total:

- `6 * 2.99 = 17.94 kg`, which matches `R7=17.96 kg` within `0.02 kg` UI-rounding tolerance.

## Conclusion

The user hypothesis is strongly supported and effectively deterministic for this transition window:

- `R1..R6` map one-to-one into `5M 1..5M 6`
- `R7` is evenly distributed across all six Fry targets.

Structured transfer-action candidate file:

- `S21_Bakkafrost_S21_jan25_EggAlevin_to_Fry_inferred_transfer_actions_2026-02-13.csv`

