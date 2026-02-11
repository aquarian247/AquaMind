# FW20 Before/After Delta (2026-02-11)

## Summary
- PASS before/after: `17/20 -> 20/20`
- FAIL before/after: `3/20 -> 0/20`
- Gate improved batches: `3`
- Gate regressed batches: `0`

## Compact Findings Table
| batch | non-bridge zero assignments before/after | gate result before/after | transition basis changes |
| --- | --- | --- | --- |
| AquaGen Mars 25 | 0/0 | PASS/PASS | basis 2/1 -> 2/1; reasons (direct=0, no_bridge_path=0, incomplete=0) -> (direct=0, no_bridge_path=0, incomplete=0) |
| BF mars 2025 | 0/0 | FAIL/PASS | basis 0/0 -> 2/1; reasons (direct=0, no_bridge_path=0, incomplete=0) -> (direct=0, no_bridge_path=0, incomplete=1) |
| BF oktober 2025 | 0/0 | PASS/PASS | basis 0/1 -> 0/1; reasons (direct=0, no_bridge_path=0, incomplete=0) -> (direct=0, no_bridge_path=0, incomplete=0) |
| Bakkafrost S-21 jan 25 | 0/0 | PASS/PASS | basis 3/0 -> 3/0; reasons (direct=0, no_bridge_path=0, incomplete=0) -> (direct=0, no_bridge_path=0, incomplete=0) |
| Bakkafrost S-21 okt 25 | 0/0 | PASS/PASS | basis 0/1 -> 0/1; reasons (direct=0, no_bridge_path=0, incomplete=0) -> (direct=0, no_bridge_path=0, incomplete=0) |
| Bakkafrost feb 2025 | 0/0 | PASS/PASS | basis 1/2 -> 2/1; reasons (direct=0, no_bridge_path=1, incomplete=0) -> (direct=1, no_bridge_path=0, incomplete=0) |
| Benchmark Gen Septembur 2025 | 0/0 | PASS/PASS | basis 0/1 -> 0/1; reasons (direct=0, no_bridge_path=0, incomplete=0) -> (direct=0, no_bridge_path=0, incomplete=0) |
| Benchmark Gen. Desembur 2024 | 0/0 | PASS/PASS | basis 3/1 -> 3/1; reasons (direct=0, no_bridge_path=0, incomplete=1) -> (direct=0, no_bridge_path=0, incomplete=1) |
| Benchmark Gen. Mars 2025 | 0/0 | PASS/PASS | basis 1/3 -> 1/3; reasons (direct=0, no_bridge_path=0, incomplete=1) -> (direct=0, no_bridge_path=0, incomplete=1) |
| Benchmark Gen. Septembur 2024 | 0/0 | PASS/PASS | basis 4/0 -> 4/0; reasons (direct=0, no_bridge_path=0, incomplete=0) -> (direct=0, no_bridge_path=0, incomplete=0) |
| StofnFiskur S-21 apr 25 | 0/0 | PASS/PASS | basis 1/2 -> 1/2; reasons (direct=0, no_bridge_path=0, incomplete=1) -> (direct=0, no_bridge_path=0, incomplete=1) |
| StofnFiskur S-21 juli25 | 0/0 | PASS/PASS | basis 1/1 -> 1/1; reasons (direct=0, no_bridge_path=0, incomplete=0) -> (direct=0, no_bridge_path=0, incomplete=0) |
| StofnFiskur okt. 2024 | 0/0 | PASS/PASS | basis 2/2 -> 2/2; reasons (direct=0, no_bridge_path=0, incomplete=2) -> (direct=0, no_bridge_path=0, incomplete=2) |
| Stofnfiskur Aug 2024 | 0/0 | PASS/PASS | basis 4/0 -> 4/0; reasons (direct=0, no_bridge_path=0, incomplete=0) -> (direct=0, no_bridge_path=0, incomplete=0) |
| Stofnfiskur Des 24 | 0/0 | PASS/PASS | basis 3/1 -> 3/1; reasons (direct=0, no_bridge_path=0, incomplete=0) -> (direct=0, no_bridge_path=0, incomplete=0) |
| Stofnfiskur Nov 2024 | 0/0 | PASS/PASS | basis 0/4 -> 0/4; reasons (direct=0, no_bridge_path=0, incomplete=3) -> (direct=0, no_bridge_path=0, incomplete=3) |
| Stofnfiskur Okt 25 | 0/0 | PASS/PASS | basis 0/1 -> 0/1; reasons (direct=0, no_bridge_path=0, incomplete=0) -> (direct=0, no_bridge_path=0, incomplete=0) |
| Stofnfiskur feb 2025 | 0/0 | FAIL/PASS | basis 0/3 -> 1/2; reasons (direct=0, no_bridge_path=1, incomplete=1) -> (direct=1, no_bridge_path=0, incomplete=1) |
| Stofnfiskur mai 2025 | 0/0 | FAIL/PASS | basis 1/1 -> 2/0; reasons (direct=0, no_bridge_path=1, incomplete=0) -> (direct=1, no_bridge_path=0, incomplete=0) |
| Stofnfiskur sept 24 | 0/0 | PASS/PASS | basis 4/0 -> 4/0; reasons (direct=0, no_bridge_path=0, incomplete=0) -> (direct=0, no_bridge_path=0, incomplete=0) |
