Summary
Separate IO from computation in apps/inventory/services/fcr_service.py; add guard clauses and extract pure functions.

Outcomes
- CC < 15 for main functions; behavior verified by unit tests.

Steps
1) Extract compute steps into private helpers with docstrings.
2) Add unit tests for helpers; run metrics; ensure outputs unchanged.

Acceptance
- CC target met; tests pass.

References
- apps/inventory/services/fcr_service.py
- aquamind/docs/metrics/*