# Factory.ai Workspace – AquaMind Setup Guide  
*Version 1.0 – July 2025*

This document walks you through creating a **Factory.ai** workspace that links the AquaMind backend & frontend repositories, enables automatic API-spec synchronisation, and configures Code- & Review-Droids.

---

## 1 Prerequisites

| Item | Notes |
|------|-------|
| GitHub repos | `github.com/aquarian247/AquaMind` (backend)  &  `github.com/aquarian247/AquaMind-Frontend` (frontend) |
| PAT secret | Fine-grained PAT scoped to **AquaMind-Frontend**, stored in backend repo as `FRONTEND_REPO_PAT` (already done). |
| Branches | `feature/api-contract-unification` pushed on both repos. |
| CI | GitHub Actions files merged (backend → OpenAPI generation & Schemathesis, frontend → type-check & build). |

---

## 2 Workspace JSON Configuration (Section 5)

Copy-paste this into the **“Create Workspace → Advanced → JSON”** panel:

```jsonc
{
  "workspace": "AquaMind",
  "repositories": [
    { "url": "github.com/aquarian247/AquaMind",          "mount": "/backend"  },
    { "url": "github.com/aquarian247/AquaMind-Frontend", "mount": "/frontend" }
  ],
  "watch": {
    "/backend/api/openapi.yaml": {
      "on_change": "run-script",
      "script": "/frontend/scripts/regenerate_api.sh"
    }
  },
  "droids": {
    "code":   { "enabled": true },
    "review": { "rules": ["spec-sync"] }
  }
}
```

### What it does  

| Key | Purpose |
|-----|---------|
| `repositories` | Mounts both repos into one workspace (`/backend`, `/frontend`). |
| `watch` | Whenever **openapi.yaml** changes in the backend, Factory runs `scripts/regenerate_api.sh` inside the frontend mount (equivalent to `npm run generate:api`). |
| `droids.code` | Allows Code-Droid to automate follow-up fixes. |
| `droids.review.rules` | Review-Droid will auto-assign PRs labelled `spec-sync`. Our cross-repo workflow already applies this label. |

---

## 3 Step-by-Step Setup in Factory.ai

1. **Create Workspace**  
   • Click **“New Workspace”** → choose **Multi-Repo**  
   • Paste the JSON config above → **Create**.

2. **Confirm Repo Mounts**  
   In the left sidebar you should see  
   - `/backend/...` (Django project)  
   - `/frontend/...` (React project)

3. **Add `scripts/regenerate_api.sh`**  
   Inside **/frontend/scripts/** create:

   ```bash
   #!/usr/bin/env bash
   set -e
   echo "🌀 Regenerating TypeScript client from OpenAPI spec..."
   npm ci
   npm run generate:api
   echo "✅ Client regenerated"
   ```

   Make it executable (`chmod +x`).

4. **Run Initial Sync**  
   In Factory terminal:

   ```
   cd /backend && python manage.py spectacular --file api/openapi.yaml
   # Factory detects change → runs regenerate script in /frontend
   ```

5. **Commit & Push**  
   Factory will show unstaged changes in `/frontend/src/api/generated`.  
   Commit them, push, open the auto-created **spec-sync** PR.

---

## 4 Validating the Automation Chain

1. **Backend Change**  
   Add a trivial docstring change to a view → commit & push.  
   CI regenerates `openapi.yaml`, uploads **api-spec** artifact.

2. **Front-end Workflow**  
   `sync-openapi-to-frontend.yml` dispatches; `regenerate-api-client.yml` opens PR with updated client.  

3. **CI Gates**  
   - Backend: Schemathesis job must pass.  
   - Frontend: `frontend-ci.yml` type-check & build must pass.  
   - Review-Droid surfaces both PRs; merge when green.

---

## 5 Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `api-spec` artifact missing | Backend workflow failed | Check Schemathesis errors / serializer issues. |
| Frontend PR not created | `FRONTEND_REPO_PAT` scope wrong | Ensure PAT has **Contents & Metadata (Read)** and **Actions (Write)**. |
| Type errors in generated client | Missing type hints in serializers | Add `@extend_schema_field` or annotate return types (see _openapi_issues_to_fix.md_). |
| Drift detected on `src/api/generated` | Someone edited generated code manually | Re-run `npm run generate:api` and recommit. |

---

## 6 Next Steps

1. **Fix remaining serializer errors & warnings** – see `docs/progress/openapi_issues_to_fix.md`.  
2. **Enable nightly Cypress smoke tests** (optional).  
3. **Invite team members** to the workspace; set default task templates.

Workspace setup is now complete – happy coding!
