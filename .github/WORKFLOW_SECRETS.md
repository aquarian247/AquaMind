# GitHub Actions Secrets for Cross-Repo API Contract Automation  
*(applies to Section 3.3 of `api_contract_unification_plan.md`)*

| Secret Name | Repository that **stores** it | Used By (workflow / job) | Required Scopes | Purpose |
|-------------|------------------------------|--------------------------|-----------------|---------|
| `FRONTEND_REPO_PAT` | **aquarian247/AquaMind** (backend) | `.github/workflows/sync-openapi-to-frontend.yml` → “Trigger frontend repository update” step | **repo** (contents + metadata) on *frontend* repo | Allows the backend workflow to fire a `repository_dispatch` event that kicks off client-regeneration in `AquaMind-Frontend`. |

## Details & Setup

1. **Generate PAT**  
   ‑ Owner of `AquaMind-Frontend` creates a fine-grained PAT limited to that repository with the **Repository Contents** and **Metadata** permissions.  
   ‑ Recommended expiration: **90 days**; enable email notification before expiry.

2. **Store Secret in Backend Repo**  
   ‑ Navigate to: `Settings → Secrets → Actions` in `aquarian247/AquaMind`.  
   ‑ Add new secret named **`FRONTEND_REPO_PAT`** and paste the token value.  
   ‑ Do **not** add this secret to the frontend repo.

3. **Built-in `GITHUB_TOKEN`**  
   - The frontend workflow (`regenerate-api-client.yml`) uses the repository-provided `GITHUB_TOKEN` to commit regenerated code and open a PR.  
   - No extra secret is needed on the frontend side.

4. **Rotation Policy**  
   - Rotate `FRONTEND_REPO_PAT` at least every 90 days or immediately if any team member with access leaves the project.  
   - After rotation, update the secret value in the backend repository.

5. **Validation**  
   - After adding or rotating the secret, trigger a dummy backend commit or rerun the last successful backend workflow to ensure the artifact sync and dispatch steps succeed.

> Keep this file updated whenever additional secrets are introduced (e.g., deployment keys, container registry creds) so new team members can set up CI/CD without guesswork.
