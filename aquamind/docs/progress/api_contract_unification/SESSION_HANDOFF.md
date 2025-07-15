# Session-Handoff – API-Contract CI Stabilisation  
*File*: `aquamind/docs/progress/api_contract_unification/SESSION_HANDOFF.md`  
*Last updated*: 2025-07-15  

---

## 1. Snapshot

| Area | Local State | GitHub CI State | Blocking Issue |
|------|-------------|-----------------|----------------|
| **Backend tests** | ✅ 482/482 pass (PostgreSQL) | ✅ Unit tests pass (SQLite) | — |
| **Schemathesis contract** | ❓ not run locally yet | 🔴 Fails – 401 (auth) | CI token not captured |
| **Frontend compile** | ✅ `npm run tsc` clean | 🟡 building | — (watch for new errors) |

---

## 2. Re-pro Commands

### 2.1 Backend – CI-style SQLite
```bash
# be in backend repo root
python manage.py migrate          --settings=aquamind.settings_ci --noinput
python manage.py get_ci_token     --settings=aquamind.settings_ci --debug   # EXPECTS token in stdout
python manage.py runserver 8000   --settings=aquamind.settings_ci
# In another shell:
schemathesis run --base-url=http://127.0.0.1:8000 --header "Authorization: Token <TOKEN>" api/openapi.yaml
```

### 2.2 Backend – PostgreSQL full suite
```bash
python manage.py test --keepdb             # 482 tests, all pass
```

### 2.3 Frontend
```bash
# inside AquaMind-Frontend
npm ci
npm run tsc          # TypeScript compile only
npm run dev          # sanity check
```

---

## 3. Current Problem: Token Capture

```
TOKEN=$(python manage.py get_ci_token --settings=aquamind.settings_ci)
[CI log] TOKEN length = 0 ➜ Schemathesis sends header "Token " ➜ 401
```

Facts:
1. Migration `0003_create_ci_test_user` **does** create user + token (verified locally).
2. `get_ci_token` prints nothing inside GitHub runner but works locally.
3. Removing `sys.exit(0)` did not fix CI output.

Suspicions:
- stdout buffering in GitHub bash step.
- Silent error inside command that is swallowed when not using `--debug`.
- Token row created but `Token.objects.get_or_create` fails to fetch due to db routing?

---

## 4. Next-Session Action Plan

| Priority | Task | Owner |
|----------|------|-------|
| P0 | Add **length debug** to workflow: `echo "TOKEN[$TOKEN] LEN=${#TOKEN}"` before check | Backend |
| P0 | Modify management command: `print(token.key, flush=True)` and add explicit `self.stdout.flush()` | Backend |
| P0 | Run command **inside** GitHub Action using `python - <<'PY' ... PY` to eliminate entry-point issues | Backend |
| P1 | Locally run Schemathesis against SQLite to verify 200s with captured token | Backend |
| P1 | If still failing, bypass token migration entirely: create token in workflow via `python -m django shell -c` one-liner | Backend |
| P2 | Monitor frontend CI; continue type-error grind if any surface | Frontend |
| P2 | Update docs: add note in `testing_strategy.md` about Windows/Unicode and `PYTHONIOENCODING=utf-8` | Docs |

---

## 5. Important Paths / Scripts

```
backend/.github/workflows/django-tests.yml        # token capture logic
apps/users/management/commands/get_ci_token.py    # command under scrutiny
apps/users/migrations/0003_create_ci_test_user.py # data migration
```

---

## 6. Questions for Next Pair

1. Does the management command produce any stderr in CI (`--debug` is run first but output may be lost)?  
2. Should we switch to `print("CI_TOKEN="+token.key)` and parse with grep instead of pure stdout capture?  
3. Is Schemathesis actually hitting endpoints that require authenticated user permissions?

---

### End-of-Session Checklist

- [ ] Token printed in CI (`len(TOKEN) > 0`)
- [ ] Schemathesis passes (0 failures)
- [ ] Frontend compile green
- [ ] Update this handoff doc with outcomes & new blockers

Happy debugging! 🚀
