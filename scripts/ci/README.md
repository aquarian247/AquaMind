# CI Scripts – AquaMind

This directory contains **small, self-contained utilities** that are executed
exclusively by Continuous-Integration jobs.  
They are **not** imported by application code and therefore have **zero
runtime impact** on production.

---

## Contents

| Script | Purpose |
|--------|---------|
| `create_test_token.py` | Creates (or re-uses) a CI user and prints a DRF auth-token so Schemathesis can call protected endpoints during contract testing. |

---

## 1 create_test_token.py

### What it does

1. Boots Django with the settings module you specify (defaults to
   `aquamind.settings_ci`).
2. Gets or creates the hard-coded user **`schemathesis_ci`**.
3. Resets the password every time (guarantees the user is usable).
4. Returns a permanent DRF Token for that user **to stdout only**.

Nothing is written to disk except the token contained in the DB.

### Usage in GitHub Actions

```yaml
- name: 🔐 Create CI auth token
  run: |
    TOKEN=$(python scripts/ci/create_test_token.py \
            --settings=aquamind.settings_ci)
    echo "::add-mask::$TOKEN"
    echo "Token: $TOKEN"   # for debugging, masked in logs
```

The downstream Schemathesis step then injects the header:

```bash
schemathesis run \
  --header "Authorization: Token $TOKEN" \
  api/openapi.yaml
```

### Local debugging

```bash
# Activate your virtualenv first
export DJANGO_SETTINGS_MODULE=aquamind.settings_ci
python scripts/ci/create_test_token.py
```

If you need a **fresh token** (for example, after truncating tables) just run
the script again—DRF will issue a new token automatically.

### Security Notes

* The generated user is **staff=false**, **superuser=false**.
* Only available in CI (`settings_ci`) or dev settings.  
  Never include this script in production images.
* The token is masked in GitHub Actions logs via `::add-mask::`.

---

## 2 Extending the Directory

Place any future CI-only helpers here—examples:

* Fixture import bootstrapper
* Temporary database seeding
* Coverage report post-processor

Keep each script:

* Self-contained (`import …` from Django is fine, **no local app imports**)
* Executable (`chmod +x`) if run directly
* Documented in this README.

Happy testing! 🚀
