# FW 3-Batch Targeted Fix Check (2026-02-11)

- Scope: rerun only previously failing batches after tooling updates.
- Commands: DB wipe + migration + semantic gates + counts per batch.

- Gate pass: `3/3`

| batch | site | gate | migrate_rc | semantic_rc | bridge/entry | no_bridge_path | direct_linkage | incomplete_linkage | non-bridge zero | transition alerts | excluded incomplete alerts |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Stofnfiskur mai 2025 | S16 Glyvradalur | PASS | 0 | 0 | 2/0 | 0 | 1 | 0 | 0 | 0 | 0 |
| Stofnfiskur feb 2025 | S16 Glyvradalur | PASS | 0 | 0 | 1/2 | 0 | 1 | 1 | 0 | 0 | 0 |
| BF mars 2025 | S08 Gjógv | PASS | 0 | 0 | 2/1 | 0 | 0 | 1 | 0 | 0 | 1 |
