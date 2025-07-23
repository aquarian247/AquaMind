# Merge Decision Analysis  
_Branch under review: `feature/api-contract-unification`_  
_Date: 2025-07-22_

---

## 1. What’s Been Completed & Verified

| Area | Status | Evidence |
|------|--------|----------|
| OpenAPI spec unified | ✅ | `api/openapi.yaml` committed & validated with drf-spectacular |
| TypeScript client regeneration | ✅ | `npm run generate:api` passes; no TS errors (`npm run type-check`) |
| Backend ↔ Frontend communication | ✅ | Dev servers running; proxy requests hit Django and return expected 401s when unauthenticated |
| Local builds | ✅ | `npm run build` completes without errors or warnings (aside from size hints) |
| Manual smoke | ✅ | Swagger UI reachable, React app loads, network traffic routes correctly |

## 2. What’s Still Missing (Out of Scope of This Branch)

| Missing Item | Impact on Users | Blocker for Merge? |
|--------------|-----------------|--------------------|
| Login page / JWT acquisition | Cannot log in yet | ❌ (handled in separate UI feature branch) |
| CRUD UI for Species, Infrastructure, etc. | No data entry from frontend | ❌ |
| Automated CI result confirmation | Push just triggered; status pending | ⚠️ Needs green check before merge |
| End-to-end Playwright smoke tests | None written yet | ❌ |

*Note:* These gaps are **feature-level**, not contract-integration issues.

## 3. Pros & Cons of Merging Now vs. Waiting

| Decision | Pros | Cons |
|----------|------|------|
| **Merge Now** | • Unblocks all other teams to branch from up-to-date main<br>• Prevents long-lived divergence & future merge pain<br>• Contract work is isolated & stable<br>• Encourages incremental PRs for UI work | • CI might reveal hidden failures (can still revert/fix)<br>• Main will not yet have functional login/UI (might disappoint casual testers) |
| **Wait** (keep feature branch) | • Keep main “demonstrable” until basic UI exists | • Ongoing drift risk; repeated rebasing<br>• Other devs duplicate effort or branch from outdated main<br>• Harder to enforce contract freeze across repos |

## 4. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CI pipeline fails after merge | Medium (pending status) | Low – revert or hot-fix | Wait for green CI before pressing **Merge** |
| Upstream spec changes shortly after merge | Medium | Medium – frontend may drift again | Establish spec-watch GitHub Action (already in workflow) |
| Stakeholders expect full UI on main | Low-Medium | Low – communicate change log & roadmap | Add release notes explaining missing UI |
| Hidden auth/permissions issues surface later | Low | Medium | Covered in upcoming login feature branch & test suite |

## 5. Recommendation

**Proceed with merging `feature/api-contract-unification` into `main` once CI reports green**.

Rationale:
1. **Contract Integration Scope Met** – All acceptance criteria for this branch are satisfied.
2. **Minimises Divergence** – Short-lived branches reduce merge complexity and keep both repos aligned.
3. **Enables Parallel Work** – UI teams can branch from main immediately to build login, species, infrastructure screens.
4. **Risks Manageable** – Remaining gaps are feature work, not regressions; CI catch-all is still pending but expected to pass given local checks.

_Action Items Before Pressing Merge_  
1. Monitor GitHub Actions for the newly pushed commit; ensure all checks 🟢.  
2. Tag the merge commit `v1-contract-unified` for easy rollback if required.  
3. Publish release notes on Slack/Teams summarising:  
   • Contract unified  
   • Generated client in place  
   • UI work starts next (login, species, infra).

Once merged, start **Phase 0: Login Page** on a new feature branch off `main`.
