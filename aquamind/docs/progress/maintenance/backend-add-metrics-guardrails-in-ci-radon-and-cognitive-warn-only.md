Summary
Add radon and flake8-cognitive steps to CI to publish CC/MI/cognitive reports (warn-only initially).

Outcomes
- Continuous visibility on complexity and maintainability trends.

Steps
1) Add scripts to run radon (cc, mi, hal, raw) and flake8 cognitive; export artifacts.
2) Wire to CI; document thresholds and remediation workflow.

Acceptance
- CI artifacts present; pipeline stable; docs updated.

References
- aquamind/docs/metrics/*
- aquamind/docs/DAILY_METRICS_REPORT.md