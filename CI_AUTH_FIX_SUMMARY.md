
# CI Auth Fix – Schemathesis Contract Tests  
_Last updated: 2025-07-22_

## 1  Root Cause
* Schemathesis re-uses a single `requests.Session`.  
* Earlier CI runs kept a **stale `Cookie: sessionid`** that Django accepted locally but the fresh CI database could not recognise → every request fell back to **SessionAuthentication** and returned **401 Unauthorized**.  
* At the same time the workflow tried to pass an `Authorization` header **from the CLI**. When the session cookie was present Django chose the cookie and ignored the token – the header never reached DRF.  
Result: contract job failed in CI but appeared to work on developer machines.

## 2  Files & Changes
| File | Key Updates |
|------|-------------|
| `.github/workflows/django-tests.yml` | 1) Generates token via `python manage.py get_ci_token`, 2) masks it, 3) **exports `SCHEMATHESIS_AUTH_TOKEN` env var**, 4) sets `SCHEMATHESIS_HOOKS="aquamind.utils.schemathesis_hooks"`, 5) drops `--header` flag (hooks now inject auth). |
| `aquamind/utils/schemathesis_hooks.py` | New **`before_call` hook**: • strips any `Cookie` headers • injects `Authorization: Token $SCHEMATHESIS_AUTH_TOKEN`.  Also logs load confirmation & keeps existing response-fix hooks. |
| `aquamind/utils/__init__.py` | Lazily imports `schemathesis_hooks` so the dotted path is always importable. |
| *(docs)* `CI_AUTH_FIX_SUMMARY.md` | This document. |

## 3  How the Fix Works
1. **Token generation** – Workflow runs `get_ci_token`, guaranteeing a valid token for the dedicated `schemathesis_ci` super-user.
2. **Environment wiring**  
   ```
   export SCHEMATHESIS_AUTH_TOKEN="$TOKEN"
   export SCHEMATHESIS_HOOKS="aquamind.utils.schemathesis_hooks"
   ```
3. **Hook logic** (`before_call`)  
   a. Remove any `Cookie` header present in the request arguments.  
   b. Add `Authorization: Token <token>` when missing.  
4. Schemathesis now sends clean, token-authenticated requests; Django authorises them in both local and CI databases.

## 4  Testing Instructions
Local one-liner:
```bash
# From repo root, assuming venv active
python manage.py migrate --settings=aquamind.settings_ci --noinput
TOKEN=$(python manage.py get_ci_token --settings=aquamind.settings_ci)
export SCHEMATHESIS_AUTH_TOKEN="$TOKEN"
export SCHEMATHESIS_HOOKS="aquamind.utils.schemathesis_hooks"
python manage.py runserver 0.0.0.0:8000 --settings=aquamind.settings_ci &
schemathesis run api/openapi.yaml --base-url http://127.0.0.1:8000 --checks all --hypothesis-max-examples=3
```
Expected: **0 failures**.  
CI will execute the same flow automatically.

## 5  Next Steps
1. Remove temporary logging middleware once the pipeline is stable.  
2. Back-port the hook pattern to any other contract jobs (e.g. staging).  
3. Enable higher `hypothesis-max-examples` after performance tuning.  
4. Merge PR #12 (yasg removal) once green CI confirms contract integrity.  
5. Finalise `sync-openapi-to-frontend.yml` so the front-end auto-regenerates its TS client on every backend merge.

---  
Feel free to amend this note if additional tweaks are made to the auth flow.