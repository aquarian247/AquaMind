# Pre-Merge Checklist  
Feature branch `feature/api-contract-unification` → `main`  
_Applies to both repositories: `AquaMind` (backend) and `AquaMind-Frontend` (frontend)_

---

## 1. Continuous Integration

- [ ] **CI pipelines complete successfully**  
      • GitHub Actions status shows green ✔ for latest commit on `feature/api-contract-unification` in **both** repos.  
      • No skipped or flaky steps; backend run (~10 min) finished.

- [ ] **Security scans pass**  
      • Backend: Bandit + Django-secure-check.  
      • Frontend: `npm audit` / Snyk OSS.

---

## 2. Source Control Hygiene

- [ ] Working directory **clean** (`git status` → “nothing to commit, working tree clean”) in both repos.  
- [ ] Latest commits **pushed** to origin; branch up-to-date (`git push` shows nothing to upload).  
- [ ] Pull Requests authored and **linked cross-repo**; description references the other PR and OpenAPI spec commit.

---

## 3. Contract Synchronisation

- [ ] Backend `api/openapi.yaml` reflects current implementation (`manage.py spectacular` or equivalent run).  
- [ ] Frontend TypeScript client regenerated (`npm run generate:api`) and committed.  
- [ ] Contract tests (Schemathesis) pass in CI & locally.

---

## 4. Functional Verification

- [ ] **Backend unit tests** (`pytest`) green locally.  
- [ ] **Frontend type-check & build** (`npm run type-check`, `npm run build`) succeed.  
- [ ] **Local smoke test**  
      1. Start backend (`docker compose up backend db` or `python manage.py runserver`).  
      2. Start frontend (`npm run dev`).  
      3. Perform login via JWT; hit at least one protected endpoint using regenerated client.  
      4. Verify expected 200 responses and no console errors.

- [ ] **End-to-End happy path** run (Cypress/Playwright) on feature branch in staging or local.

---

## 5. Documentation & Communication

- [ ] New/updated docs committed:  
      • `AquaMind_Frontend_OpenAPI_Integration_Plan.md`  
      • `AquaMind_Frontend_Integration_Success_Report.md`  
      • `AquaMind_Frontend_Development_Strategy.md`  
      • `AquaMind_Authentication_Architecture_Strategy.md`  
      • `Merge_Decision_Analysis.md`  
      • Factory development strategy docs.  

- [ ] Changelog entry drafted for **v1-contract-unified** release (both repos).  
- [ ] Announcement message prepared for Slack/Teams.

---

## 6. Review & Approvals

- [ ] Minimum reviewers approved (≥2 backend, ≥1 frontend).  
- [ ] No unresolved PR comments.  
- [ ] Merge commit strategy confirmed (squash or merge-commit) and branch protections satisfied.

---

## 7. Release & Tagging

- [ ] Version/tag set: `v1-contract-unified` created **after** merge on `main`.  
- [ ] CI on `main` post-merge still green; images/packages published.

---

## 8. Rollback Plan

- [ ] Revert PR link noted and tested (`git revert -m 1 <merge_commit_sha>`).  
- [ ] Previous container images / static bundles retained for quick redeploy.

---

## 9. Final “GO” Decision

- [ ] All boxes above checked.  
- [ ] Team lead (or designated release manager) gives verbal/Slack approval to press “Merge”.

---

_Once merged and CI is green on `main`, delete `feature/api-contract-unification` branches locally and on origin._
