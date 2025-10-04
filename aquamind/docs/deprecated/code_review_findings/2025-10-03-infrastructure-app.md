## AquaMind Infrastructure Review – 2024-10-04

### Scope
- Backend containerisation and runtime configuration (`Dockerfile.dev`, `docker-compose*.yml`, deployment scripts, devcontainer).
- CI/CD workflows touching build, deploy, and schema sync.
- Frontend operational infrastructure (Dockerfile, Nginx, runtime server, env handling).

### Key Findings
1. **Secrets checked into source and baked into images.** Hard-coded Timescale credentials, Django secret key, and default admin password appear in compose, `.env`, shell scripts, and the Docker build context (no `.dockerignore`).
2. **Development images reused for deployments.** Backend container runs `runserver`, mounts the entire repo, and is built from `Dockerfile.dev`; frontend proxy expects the backend host `web`, so the test deploy mirrors local dev rather than a hardened stack.
3. **Deployment automation relies on fragile paths and missing assets.** Backend compose references `../AquaMind-Frontend`, monitoring service expects `monitoring/prometheus.yml`, and Nginx mounts `./ssl` although none are committed.
4. **Devcontainer and local tooling drift.** Devcontainer `.devcontainer/devcontainer.json` installs `npm` from backend root (fails) and sets a different `DATABASE_URL` password than compose.
5. **Predictable superuser seeding.** `scripts/create_admin_user.py` creates `admin/admin123`, run automatically in deployment workflows.
6. **CI inefficiencies and spec drift risk.** Django workflow executes tests twice (coverage pass), still fakes Timescale migrations against SQLite, OpenAPI validation spawns Postgres but uses SQLite settings, and frontend workflow always pulls `api/openapi.yaml` from backend `main` rather than the PR branch.
7. **Frontend runtime inconsistencies.** Express proxy expects `process.env.DJANGO_API_URL`, but `.env` only defines `VITE_DJANGO_API_URL`; middleware logs full JSON payloads for every `/api` call; Dockerfile lacks cache busting controls and hardening.

### Mitigation Suggestions
1. **Centralise secret management.** Replace inline secrets with env references (Compose `.env`, GitHub Secrets, server env files), add a `.dockerignore`, and rotate the exposed credentials immediately.
2. **Introduce production-grade Dockerfiles.** Create separate backend/ frontend production images (gunicorn + whitenoise or ASGI server, multi-stage build) and adjust deployment workflows to build/pull those tags.
3. **Stabilise deployment assets.** Publish frontend artifacts to an OCI registry (or package tarball) and update compose to consume them; commit Prometheus/Nginx assets or parameterise mounts; add Docker healthchecks instead of bare `depends_on`.
4. **Align devcontainer setup with project layout.** Move `npm install` into the frontend repo via a repo-specific dev container or root-level script, and ensure the devcontainer `.env` mirrors compose defaults without hard-coded passwords.
5. **Harden default user provisioning.** Convert `create_admin_user.py` into an idempotent “ensure superuser” script that reads credentials from env/secret storage and disable it in automated deploys.
6. **Streamline CI pipelines.** Split lint/test/coverage stages to avoid duplicate Django runs, adjust schema validation to use Postgres when Postgres is provisioned, and teach frontend workflows to fetch the OpenAPI artifact from the corresponding backend branch run.
7. **Tighten frontend runtime hygiene.** Normalise env usage (`DJANGO_API_URL` vs `VITE_DJANGO_API_URL`), downgrade API logging to summary-only (no payloads), and add best-practice hardening (non-root user, `USER` directive, static file cache headers) to the Docker/Nginx stack.

### Follow-up Opportunities
- Consider Terraform/Ansible (or Docker Swarm/K8s manifests) to formalise infrastructure instead of ad-hoc compose deploys.
- Extend monitoring by committing alerting rules and ensuring Prometheus assets live alongside workflows.
- Evaluate using GH environments with protection rules for the `test` deploy pipeline.
