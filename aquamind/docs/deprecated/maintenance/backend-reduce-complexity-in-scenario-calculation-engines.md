Summary
Extract algorithmic helpers in scenario calculation engines (projection, tgc, mortality, fcr) to reduce branching and nesting.

Outcomes
- CC < 15 for heavy functions; stronger unit tests.

Steps
1) Identify hot functions in apps/scenario/services/calculations/*.
2) Extract helpers; annotate types; add early returns.
3) Add tests; run metrics.

Acceptance
- CC targets met; tests pass.

References
- aquamind/docs/metrics/*
- apps/scenario/services/calculations/*