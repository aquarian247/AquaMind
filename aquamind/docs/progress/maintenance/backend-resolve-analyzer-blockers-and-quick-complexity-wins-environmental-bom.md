Summary
Remove U+FEFF from apps/environmental/api/viewsets.py and apply small guard-clause simplifications.

Outcomes
- Metrics tools parse all files; baseline CC/MI established.

Steps
1) Strip BOM; commit without behavior changes.
2) Run radon/flake8-cognitive and record results.

Acceptance
- No parse errors; tests unchanged and passing.

References
- aquamind/docs/DAILY_METRICS_REPORT.md
- aquamind/docs/metrics/*