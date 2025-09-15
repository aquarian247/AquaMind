Summary
Split batch/api/viewsets.py by resource or adopt mixins; isolate filter logic and keep routes intact.

Outcomes
- MI improves (>50 target); route behavior unchanged; OpenAPI remains aligned.

Steps
1) Identify resource boundaries; create files/mixins and update imports/routers.
2) Extract filter logic into helpers or django-filter classes.
3) Run tests and radon; verify openapi matches committed spec.

Acceptance
- MI increase; tests green; openapi unchanged.

References
- aquamind/docs/progress/api_consolidation/api_consolidation_improvement_plan.md
- api/openapi.yaml