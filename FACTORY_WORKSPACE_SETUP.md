# Factory.ai Workspace Setup – “AquaMind”

This guide walks you through creating the Factory.ai workspace required by **Section&nbsp;5** of the *API Contract Unification Plan*.  
The workspace knits the backend (`AquaMind`) and frontend (`AquaMind-Frontend`) repositories together, automating OpenAPI generation and client regeneration.

---

## 1 Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Factory Bridge | ≥ 0.19 | Installed & running locally |
| Git | any recent | Repos must be cloned locally *(or use Factory’s “clone” dialog)* |
| Python | 3.11.x | Matches backend requirements |
| Node JS | ≥ 18 LTS | Matches frontend requirements |
| Bash / PowerShell | | For `scripts/regenerate_api.(sh|ps1)` |

Make sure you can run both projects individually before integrating them in Factory.

---

## 2 Workspace JSON Configuration

Copy the JSON block below; you will paste it into the Factory workspace editor in Step 3.

```jsonc
{
  "workspace": "AquaMind",
  "repositories": [
    { "url": "github.com/aquarian247/AquaMind",           "mount": "/backend"  },
    { "url": "github.com/aquarian247/AquaMind-Frontend",  "mount": "/frontend" }
  ],
  "watch": {
    "/backend/api/openapi.yaml": {
      "on_change": "run-script",
      "script": "/frontend/scripts/regenerate_api.sh --frontend --validate"
    }
  },
  "droids": {
    "code":   { "enabled": true },
    "review": { "rules": ["spec-sync"] }
  }
}
```

Key points  
• The **watch rule** fires whenever the generated `openapi.yaml` changes, running the Bash script that (a) validates the spec and (b) regenerates the TS client in the frontend repo.  
• If you are on Windows, change the `script` path to `.ps1` **or** keep Bash via WSL/Git Bash.  
• Labels under `droids.review.rules` route PRs with `spec-sync` to Review-Droid automatically.

---

## 3 Step-by-Step Setup

### 3.1 Create the Workspace

1. Open Factory → *Workspaces* → **New Workspace**.  
2. Name it **AquaMind**.  
3. Select **Manual JSON** mode (or *Advanced* tab).  
4. Paste the JSON configuration above, **editing paths if your folder layout differs**.  
5. Click **Create**.

### 3.2 Mount Local Repositories

Factory will prompt you to choose local folders for each `mount` path:

| Mount Path | Local Folder (example) |
|------------|------------------------|
| `/backend` | `C:\Users\YOU\Projects\AquaMind` |
| `/frontend`| `C:\Users\YOU\Projects\AquaMind-Frontend` |

Verify that `manage.py` lives in `/backend` and `package.json` in `/frontend`.

### 3.3 Configure Environment

Inside the workspace settings:

1. Set **Python interpreter** for `/backend` to Python 3.11.  
2. Add a **virtual environment** or point to an existing one with all backend deps installed (`pip install -r requirements.txt`).  
3. For `/frontend` enable **Node runtime** and run `npm install` once (Terminal tab).  
4. Optional: add workspace-level *Env Vars* (`DJANGO_SETTINGS_MODULE=aquamind.settings`) if you switch settings frequently.

### 3.4 Verify Watch Rule

1. In `/backend`, run  
   ```bash
   python manage.py spectacular --file api/openapi.yaml
   ```  
2. Save a tiny change to any serializer and regenerate the schema again – you should see Factory’s **Task Runner** trigger `/frontend/scripts/regenerate_api.sh`.  
3. Inspect the Task output panel; you should see:  
   ```
   ✓ OpenAPI spec generated successfully
   ✓ OpenAPI spec validation passed
   ✓ Frontend TypeScript client generated successfully
   ```

If nothing fires, double-check the watch path spelling (`/backend/api/openapi.yaml`) relative to the workspace root.

---

## 4 Daily Workflow Tips

| Action | How it Works in Factory |
|--------|------------------------|
| Edit serializers/models | On save → run `spectacular` manually or via VCS hook<br>→ watch rule regenerates client |
| Run backend tests | Open `/backend` terminal → `pytest` or `python manage.py test` |
| Run frontend dev server | `/frontend` terminal → `npm run dev` (Vite) |
| Commit spec-sync changes | After the script runs, `git status` in `/frontend` shows updated `src/api/generated/…` – commit with message prefix `chore: regenerate API client` and label `spec-sync` |

---

## 5 Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Watch script not executed | Wrong path or script not executable | Ensure correct mount paths and run `chmod +x regenerate_api.sh` |
| “Command not found: openapi” | Code-gen package missing | `npm i -D openapi-typescript-codegen` inside frontend |
| Token 401s in Schemathesis | CI user/token missing | Verify `.github/workflows/django-tests.yml` snippet committed |

---

## 6 Next Actions

1. Commit this `FACTORY_WORKSPACE_SETUP.md` to `/backend/docs/`.  
2. Push all CI fixes and verify green pipelines.  
3. In Factory, hit **Run Tests** (or GitHub UI) to ensure the watch rule & droids behave as expected.  
4. Merge `feature/api-contract-unification` → **develop** once all checks pass.

Happy coding – your unified API contract is now fully automated! 🚀
