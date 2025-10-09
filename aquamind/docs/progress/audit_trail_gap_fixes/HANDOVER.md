# Audit Trail Gap Fixes – Handover Notes

## Current Scope
- Branch: `feature/audit-trail-gaps` (aligned with playbook).
- Apps completed: Infrastructure, Batch, Inventory, Broodstock (models have `HistoricalRecords`, viewsets inherit `HistoryReasonMixin`).
- Core fix: `HistoryReasonMixin.perform_create` now guards `refresh_from_db()` against `DoesNotExist`.
- Latest migrations: `batch.0022`, `inventory.0013`, `broodstock.0004` (applied with `--settings=aquamind.settings_ci`).

## Verified State
- Recent tests this branch: `python manage.py test apps.inventory --settings=aquamind.settings_ci` and `python manage.py test apps.broodstock --settings=aquamind.settings_ci` (pass).
- Earlier iterations already exercised Infrastructure/Batch suites; rerun if substantial changes occur.
- Post-migration audit shell checks for each completed app show 100% history coverage on models and mixins wired for viewsets.

## Pending Work
1. Scenario app audit and remediation.
2. Harvest app audit and remediation.
3. Users app audit and remediation (low priority per playbook).
4. Environmental app review (confirm whether audit trail needed).
5. Regenerate and commit updated OpenAPI schema once all apps complete.
6. Run full regression test suite (entire project) prior to PR.
7. Compile final `AUDIT_TRAIL_COMPLIANCE_REPORT.md` summarizing coverage stats and findings.

## Operational Notes
- Continue using `--settings=aquamind.settings_ci` for migrations/tests to bypass TimescaleDB dependency.
- When adding history to remaining apps, follow Health app patterns (HistoryReasonMixin first in MRO, set `user_field` where applicable).
- Maintain minimal docstring changes: only mention audit capture when mixing in history.
- Ensure documentation moves remain confined to `aquamind/docs/deprecated/` unless explicitly requested otherwise.

## Suggested Next Steps
1. Audit Scenario models/viewsets (use shell report helper in playbook), add missing history and migrations, run targeted tests.
2. Repeat for Harvest, then Users/Environmental per priority.
3. After code complete, regenerate schema and run `python manage.py test --settings=aquamind.settings_ci` for full coverage.
4. Draft compliance report and prep PR (include migrations + schema).

## Helpful References
- `AUDIT_TRAIL_VERIFICATION_PLAYBOOK.md` and `BACKEND_AUDIT_TRAIL_FIXES.md` in this directory.
- `history_mixins.py` for shared logic and recent guard clause addition.
