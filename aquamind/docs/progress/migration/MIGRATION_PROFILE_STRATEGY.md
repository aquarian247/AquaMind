# Migration Profile Strategy (FW Cohorts < 30 Months)

## Goal

Maximize migration success across freshwater cohorts without forking core scripts into many unmaintainable variants.

## Decision

Use a **single migration core** with explicit, named **profiles** for cohort-family behavior.

This is preferred over script forks because profiles are:

- discoverable (`--migration-profile`)
- auditable (one module with explicit knobs)
- testable (same regression pack, different profile selectors)
- reversible (switch profile without code changes)

## Initial profile schema

Implemented in `scripts/migration/tools/migration_profiles.py`.

Each profile can control:

- lifecycle stage selection mode (`frontier` vs `latest_member`)
- frontier window (`lifecycle_frontier_window_hours`)
- same-stage supersede short-window (`same_stage_supersede_max_hours`)
- latest-holder consistency gate for active containers
- orphan-zero assignment suppression

## Initial profile set

- `fw_default` (default)
  - Hardened FW behavior used for current S21/Benchmark/Stofn checks.
- `fw_relaxed_holder`
  - Frontier stage selection with relaxed active-holder constraints (diagnostics/backtesting).
- `legacy_latest_member`
  - Legacy-biased stage mode (`latest_member`) for troubleshooting historical behavior.

## Recommended cohort grouping path

Do not pre-create many profiles. Start with evidence-based grouping:

1. **Run all candidate FW cohorts using `fw_default`.**
2. **Classify failures by signature**, not by station name alone:
   - active-holder outside component
   - stage frontier disagreement
   - superseded/bridge over- or under-suppression
   - station/site semantic mismatch
3. **Create a new profile only when >= 3 cohorts share a stable failure signature** and the fix is policy-like (not one-off data repair).
4. **Name profiles by behavior, then optionally map stations/eras** in reporting metadata.

Tooling support:

- `scripts/migration/tools/migration_profile_cohort_classifier.py`
  - reads semantic summary JSONs
  - assigns signature + recommended profile + confidence
  - emits grouped markdown/json report for profile decisions

## Operational guardrails

- Keep AquaMind runtime FishTalk-agnostic.
- Keep all source-specific behavior in migration tooling only.
- Require regression checks on known anchors (`B01/B02`, active-frontier snapshots, semantic gates) before promoting a profile.
- Prefer profile selection in runbooks over script copies.
- Run extract freshness preflight before migrations/classification to detect
  table cut-offs early.

## CLI usage

- Component migration:
  - `pilot_migrate_component.py --migration-profile fw_default ...`
- Input-batch pipeline:
  - `pilot_migrate_input_batch.py --migration-profile fw_default ...`
  - (default preflight enabled) `--extract-horizon-date YYYY-MM-DD` recommended
    for backup-bound runs.
  - Current default horizon is set to backup date: `2026-01-22`.
  - `operation_stage_changes` lag threshold is enforced by default; use
    `--extract-allow-operation-stage-lag` only for controlled diagnostics.

- Standalone extract preflight:
  - `extract_freshness_guard.py --csv-dir scripts/migration/data/extract --horizon-date 2026-01-22`
  - optional relaxation: `--allow-operation-stage-lag`

- Cohort signature grouping:
  - `migration_profile_cohort_classifier.py --analysis-dir aquamind/docs/progress/migration/analysis_reports/2026-02-16 --extract-horizon-date 2026-01-22`

Both tools still allow targeted knob overrides (for controlled experiments):

- `--lifecycle-frontier-window-hours`
- `--same-stage-supersede-max-hours`
