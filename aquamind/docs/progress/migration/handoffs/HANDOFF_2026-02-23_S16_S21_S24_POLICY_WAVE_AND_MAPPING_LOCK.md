# HANDOFF 2026-02-23: S16/S21/S24 Policy Wave + Mapping Lock

## Session objective

Run a controlled policy-based replay/validation wave for the next station group (`S16`, `S21`, `S24`), then harden documentation so the current transfer-count logic is explicit and difficult to regress in future agent sessions.

## Outcome status

- Station-group wave replay: complete (`30/30` cohorts replayed successfully).
- Policy validation scoreboard generated for the full group.
- Mapping blueprint updated to lock the latest transfer-count and stage behavior.
- README index updated so this handoff is discoverable as the latest state.

## Primary evidence artifacts

- Replay execution scoreboard (per-batch replay + in-loop validation):
  - `scripts/migration/output/s16_s21_s24_policy_replay_validation_20260223_145808.md`
  - `scripts/migration/output/s16_s21_s24_policy_replay_validation_20260223_145808.json`
- Final-state policy scoreboard (authoritative post-wave snapshot):
  - `scripts/migration/output/s16_s21_s24_policy_validation_postwave_20260223_150643.md`
  - `scripts/migration/output/s16_s21_s24_policy_validation_postwave_20260223_150643.json`

## Policy scoreboard summary (post-wave authoritative board)

- Cohorts evaluated: `30`
- Non-zero assignment rows evaluated: `4,016`
- Total mismatches vs policy authority: `628`
- Mismatches where expected count was non-zero: `0`
- Mismatches where expected count was zero: `628`
- Seed-stage mismatches: `29` cohorts (one per cohort pattern), with one clean cohort (`Stofnfiskur S21 okt 25`).

## Interpretation

- The new transfer authority behavior is stable for non-zero expected counts:
  - no `expected_nonzero` mismatches were observed.
- Residual mismatches in this station group are all zero-expected cases at exact-start snapshots (seed/fan-out style starts), not drift between non-zero FishTalk counts and AquaMind counts.
- This indicates the wave did not reintroduce the prior lane-level transfer split issue seen in earlier S08 work (`20,000/10,000` synthetic split pattern).

## Documentation updates completed

- Updated: `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
  - version bumped to `5.2` (`2026-02-23`)
  - added explicit count-authority rules:
    - completed populations: exact start-time non-zero status count is authoritative
    - open populations: latest status count is authoritative
  - added biomass precision guardrail note (higher internal avg-weight precision before model rounding)
  - refined S08 `R-Holl` rule to material-first `Parr` then in-hall `Smolt`, with pre-initial micro-bridge zero-count retention
  - added regression policy guard language under container assignment mapping
- Updated: `aquamind/docs/progress/migration/README.md`
  - added this handoff to `Latest handoff`
  - moved low-context bootstrap pointer to this handoff + mapping blueprint

## Recommended next step

Implement a narrow policy exception for exact-start zero snapshots on component-root/fan-out initialization windows (without weakening non-zero authority), then rerun the same post-wave board to confirm residual collapse in the highest-mismatch cohorts (`166`, `167`, `161`, `163`, `165`).
