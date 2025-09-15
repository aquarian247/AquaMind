Summary
Reduce CC in key batch serializers by extracting helper functions.
Targets: apps/batch/api/serializers/growth.py, composition.py, transfer.py.

Outcomes
- CC < 15 for targeted methods; serializer interfaces unchanged; tests added for helpers.

Steps
1) Identify logical groups of checks; extract to helpers with docstrings.
2) Add/adjust unit tests; run radon/flake8-cognitive.

Acceptance
- CC targets met; tests pass; API unchanged.

References
- aquamind/docs/quality_assurance/code_organization_guidelines.md
- aquamind/docs/DAILY_METRICS_REPORT.md