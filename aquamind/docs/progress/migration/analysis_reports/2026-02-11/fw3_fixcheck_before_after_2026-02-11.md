# Targeted Before/After Delta (3 Previously Failing Batches)

| batch | non-bridge zero before/after | gate before/after | transition basis before/after (bridge/entry) | transition basis change detail |
| --- | --- | --- | --- | --- |
| Stofnfiskur mai 2025 | 0/0 | FAIL/PASS | 1/1 -> 2/0 | no_bridge_path 0 -> 0; direct_linkage 1 |
| Stofnfiskur feb 2025 | 0/0 | FAIL/PASS | 0/3 -> 1/2 | no_bridge_path 1 -> 0; direct_linkage 1; incomplete_linkage now 1 |
| BF mars 2025 | n/a (migration abort)/0 | FAIL/PASS | n/a -> 2/1 | stage-resolution blocker removed (R-Høll unresolved -> resolved); incomplete_linkage now 1 (excluded from hard fail) |
