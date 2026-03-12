# FW Hardening Queue

Date: 2026-03-06

## Summary

- Scope batches analyzed: `20`
- Scope batches exposed to the old transfer split-loss bug: `17`
- Additional transfer-rerun canaries outside the mapped scope: `4`
- Manual reconstruction batches: `4`
- No-immediate-action batches: `3`

## Wave 1: Transfer Rerun Canaries

| Batch ID | Batch Number | Batch Key | Missing Split Legs | Reason |
|---|---|---|---:|---|
| `1344` | `Stofnfiskur Des 23 - Vár 2024` | `Stofnfiskur Des 23|6|2023` | `60` | Manually validated S03 cohort with missing split legs (801/802/806 -> 901/903/904) under the old replay behavior. |
| `1348` | `Stofnfiskur S-21 feb24 - Vár 2024` | `Stofnfiskur S-21 feb24|1|2024` | `127` | Creation-repaired canary outside the mapped scope; transfer replay is still exposed to the old split-loss bug. |
| `1349` | `Stofnfiskur S-21 juni24 - Summar 2024` | `Stofnfiskur S-21 juni24|2|2024` | `112` | Creation-repaired canary outside the mapped scope; transfer replay is still exposed to the old split-loss bug. |
| `1352` | `Stofnfiskur desembur 2023 - Vár 2024` | `Stofnfiskur desembur 2023|4|2023` | `165` | Creation-repaired S24 canary; egg-stage counts were fixed, but transfer replay still predates the root-source split-leg patch. |

## Wave 2: Mapped FW Scope Transfer Reruns

| Batch Key | Missing Split Legs | Member Count | Raw SubTransfers |
|---|---:|---:|---:|
| `Stofnfiskur Aug 2024|4|2024` | `98` | `314` | `194` |
| `Bakkafrost S-21 jan 25|1|2025` | `80` | `268` | `175` |
| `Bakkafrost Okt 2023|4|2023` | `79` | `277` | `172` |
| `Stofnfiskur Nov 2024|5|2024` | `74` | `237` | `138` |
| `Benchmark Gen. Septembur 2024|3|2024` | `71` | `272` | `152` |
| `Bakkafrost Juli 2023|3|2023` | `67` | `226` | `141` |
| `Stofnfiskur Juni 24|2|2024` | `58` | `215` | `129` |
| `Stofnfiskur Aug 23|4|2023` | `56` | `234` | `130` |
| `Stofnfiskur mai 2024|3|2024` | `54` | `183` | `113` |
| `Stofnfiskur feb 2025|1|2025` | `51` | `157` | `98` |
| `StofnFiskur S-21 apr 25|2|2025` | `44` | `158` | `100` |
| `Stofnfiskur mai 2025|3|2025` | `26` | `79` | `48` |
| `AquaGen juni 25|2|2025` | `23` | `69` | `41` |
| `StofnFiskur S-21 juli25|3|2025` | `20` | `60` | `33` |
| `Stofnfiskur August 25|4|2025` | `7` | `24` | `12` |
| `24Q1 LHS ex-LC|13|2023` | `5` | `28` | `15` |
| `Bakkafrost S-21 okt 25|5|2025` | `3` | `16` | `8` |

## Manual Reconstruction First

| Batch ID | Batch Number | Batch Key | Missing Split Legs | Creation Total Gap Signal |
|---|---|---|---:|---|
| `1116` | `24Q1 LHS ex-LC` | `24Q1 LHS ex-LC|13|2023` | `5` | apply run `0` -> `0` vs creation `1368746` |
| `1133` | `Stofnfiskur feb 2025 - Vár 2025` | `Stofnfiskur feb 2025|1|2025` | `51` | guarded dryrun `263736` -> `1044146` vs creation `1500410` |
| `1329` | `Benchmark Gen. Mars 2025 - Vár 2025` | `Benchmark Gen. Mars 2025|1|2025` | `119` | guarded dryrun `22439` -> `3432883` vs creation `3500200` |
| `1330` | `Gjógv/Fiskaaling mars 2023 - Heyst 2023` | `Gjógv/Fiskaaling mars 2023|5|2023` | `2` | apply run `0` -> `0` vs creation `657722` |

## No Immediate Action

| Batch | Reason |
|---|---|
| `Bakkafrost feb 2024|1|2024` | Creation repair already applied and no internal-only split-loss exposure was detected in the transfer replay. Mapped-scope batch analyzed against the patched root-source expansion and did not show additional internal split legs. |
| `SF nov 2025|6|2025` | Mapped-scope batch analyzed against the patched root-source expansion and did not show additional internal split legs. |
| `Stofnfiskur S21 okt 25|4|2025` | Mapped-scope batch analyzed against the patched root-source expansion and did not show additional internal split legs. |

## Recommended Execution Order

- Rerun transfer workflows for the Wave 1 canaries first.
- If the Wave 1 canaries validate cleanly in AquaMind, rerun the 17 affected mapped-scope FW batches.
- Do not bulk-rerun `1116`, `1133`, `1329`, or `1330` before their FW reconstruction strategy is decided.
