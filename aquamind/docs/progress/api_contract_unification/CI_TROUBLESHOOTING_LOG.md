# CI Troubleshooting Log  
_AquaMind – API Contract Unification_

---

## 1. Overview
This document records every significant CI failure we hit while unifying the AquaMind API contract and the actions taken to resolve them.  
Primary focus: the “Validate API contract with Schemathesis” stage inside `AquaMind CI/CD`.

Legend:  
* ✅ = fixed / no longer occurs  
* ❌ = still failing / needs work  
* ⚠️ = mitigated but not root-cause-fixed  

---

## 2. Chronological Troubleshooting Attempts

| Date (2025) | Symptom / CI Error | Root Cause | Action / Fix | Result |
|-------------|-------------------|------------|--------------|--------|
| **Jul 11** | `django.db.utils.OperationalError` – Windows runner could not apply migrations | Non-ASCII chars in old migration & file-path length limits | Deleted offending migration / squashed, added `.gitattributes` for UTF-8 | ✅ |
| **Jul 12** | SQLite integer overflow during Schemathesis data generation | OpenAPI `maximum` / `minimum` values exceeded SQLite 64-bit range | Added `clamp_integer_schema_bounds` post-processing hook | ✅ |
| **Jul 13** | 401 / *ignored_auth* for every endpoint (977 failures) | Spec lacked global `security:` block, so Schemathesis sent no header | Added `ensure_global_security` hook; added `TokenAuthentication` globally | ⚠️ (reduced failures but some persisted) |
| **Jul 14** | Still ~600 *ignored_auth*; duplicate `tokenAuth` entries clutter spec | DRF-Spectacular duplicated security arrays per op | Added `cleanup_duplicate_security` hook (dedup only) | ⚠️ |
| **Jul 15** | *ignored_auth* down to 392 but CI user got 403 on admin routes | CI user lacked superuser/staff flags | Management command `get_ci_token` now sets `is_staff` + `is_superuser` | ✅ |
| **Jul 15** | Pagination tests returning 404 / 500 on `page=0` or huge ints | DRF default paginator raised `NotFound` | Implemented `ValidatedPageNumberPagination` (returns 400, handles OOR) | ✅ |
| **Jul 16** _(today)_ | *ignored_auth* still ~392; `- {}` anonymous entries in spec | DRF-Spectacular emits `{}` when `AllowAny` present; existed on many ops | Enhanced `cleanup_duplicate_security` to strip `{}` from **all** ops except `/api/v1/auth/token/` & `/dev-auth/`; regenerated spec; committed | ✅ spec cleaned, but CI still fails |
| **Jul 16** | Schemathesis **status_code_conformance** failures on auth token endpoint (expects 2xx, gets 400) | Fuzzed credentials obviously invalid; schema declares *200 only* | Not solved – need to broaden expected responses or mark as negative test | ❌ |
| **Jul 16** | 404 on `/api/v1/infrastructure/*` routes | Schemathesis hitting stale paths that were renamed to `/api/v1/batch/*` | URLConf updated previously but **schema** still contains old tags | ❌ awaiting router–schema sync |

---

## 3. Current Known CI Issues (2025-07-16 EOD)

1. ❌ **Schemathesis “ignored_auth” failures remain (≈ 392).**  
   • Header _is_ passed (`Authorization: Token …`) but tool still flags certain ops – need to verify per-request header injection.

2. ❌ **`status_code_conformance` on authentication endpoints.**  
   Spec only lists `200`. Need to document/allow `400` for invalid creds or tell Schemathesis to skip.

3. ❌ **404 for legacy `/api/v1/infrastructure/*` paths.**  
   OpenAPI spec not aligned with router renames; regenerate or drop obsolete paths.

4. ⚠️ **Log verbosity / truncation.**  
   Large Schemathesis output (20 k + lines) trimmed by GitHub, obscuring failures. Plan to upload artefact file.

---

## 4. Lessons Learned

* Always regenerate the OpenAPI schema **after** URL or permission changes; stale paths create false 404s.
* A top-level `security:` block is mandatory for Schemathesis; rely on a hook to enforce.
* DRF-Spectacular inserts `{}` whenever any permission class includes `AllowAny`.  
  – Strip these unless the endpoint is _truly_ public to avoid *ignored_auth*.
* SQLite contract testing needs integer range clamping; put this in one reusable hook and enable only for CI settings.
* Give the CI service account superuser rights; otherwise random admin redirects produce unauthorized noise.
* When Schemathesis fuzzes auth endpoints it will send garbage creds – schema must declare 4xx codes or we must mark operation as negative-test-ignored.
* Preserve troubleshooting output: redirect `schemathesis run > schemathesis.txt` and upload artefact for easier offline analysis.

---

_End of log – last updated 2025-07-16_  
