# AquaMind — Testing Guide

_Last updated July 2025_

## 1. Test Pillars

| Layer          | Purpose                                           | Frameworks / Tools                  |
|----------------|---------------------------------------------------|-------------------------------------|
| **Unit**       | Isolate functions, methods, model logic           | `django.test.TestCase`, `pytest`    |
| **Integration**| Verify components working together (DB/API)       | DRF test client, Playwright*        |
| **Contract**   | Enforce implementation ↔ OpenAPI 3.1 conformance  | **Schemathesis** (property-based)   |

\* Playwright UI tests live in `tests/` but are optional in CI.

---

## 2. Directory Layout

```
aquamind/
├── apps/
│   └── inventory/
│       └── tests/          # app-scoped Django tests
├── tests/                  # repo-wide or cross-app tests
└── docs/quality_assurance/ # legacy docs (being deprecated)
```

Place tests **next to the code they exercise** (`apps/<app>/tests/`), except truly cross-app scenarios which live in the root `tests/`.

---

## 3. Running Tests

### 3.1 Local Development

| Action                      | Command                                                                    |
|-----------------------------|----------------------------------------------------------------------------|
| Run all tests (PostgreSQL)  | `python manage.py test`                                                    |
| Mimic CI (SQLite, faster)   | `python manage.py test --settings=aquamind.settings_ci`                    |
| Single app                  | `python manage.py test apps.inventory`                                     |
| Specific test file          | `python manage.py test apps.inventory.tests.test_serializers`              |
| Coverage report             | `coverage run --source='.' manage.py test && coverage report`              |

### 3.2 Continuous Integration

GitHub Action `.github/workflows/django-tests.yml` automatically:

1. Installs deps & runs migrations (SQLite, `settings_ci`).
2. Executes full unit/integration suite.
3. Runs Schemathesis contract tests (section 6).
4. Uploads coverage & artefacts.

---

## 4. Smart Test Design

### 4.1 Principles

| # | Principle | Quick Take |
|---|-----------|------------|
| 1 | **Leverage existing patterns** | Re-use fixture helpers in `tests/base.py` and app fixtures such as `apps/infrastructure/tests/test_models.py`. |
| 2 | **Focus on app-specific logic** | Test business rules & domain behaviour, not Django or DRF internals. |
| 3 | **Reuse utilities** | Use shared helpers (e.g. `get_api_url()`, `BaseAPITestCase`) instead of re-implementing request logic. |
| 4 | **Keep tests simple & focused** | 200-300 LOC of meaningful assertions > 600+ LOC of duplicated setup. |

### 4.2 Proven Patterns

* **Minimal fixtures** – Prefer `Model.objects.get_or_create()` and factory defaults over hand-crafting long hierarchies.  
* **Selective imports** – Import only the models under test; avoid deep relationship trees when not required.  
* **Environment-specific skips** – Gate TimescaleDB or external-service tests behind `@unittest.skipIf`.  
* **Focus areas** – String representations, validators, computed properties, permission checks, and critical services.

| Pattern                       | Example                                  |
|-------------------------------|------------------------------------------|
| Minimal fixture               | `batch, _ = Batch.objects.get_or_create(...)` |
| Single-purpose test class     | `class LiceCountLogicTest(TestCase): ...` |
| Skip for PG-only feature      | `@skipIf(not is_postgres(), "PG only")`  |
| Assert validation             | `with self.assertRaises(ValidationError): obj.full_clean()` |

### 4.3 Coverage Strategy

| Target                     | Goal |
|----------------------------|------|
| **Per new test file**      | ≥ 80 % line coverage |
| **Per app overall**        | ≥ 50 % line coverage |
| **Prioritisation**         | 1. Business-critical paths<br>2. Bug-prone areas<br>3. Edge cases |
| **Philosophy**             | _Quality > Quantity_ – prefer fewer, meaningful assertions to large boilerplate suites. |

Apply these guidelines to avoid maintenance overhead while steadily increasing confidence.

---

## 5. Contract Testing

Contract tests live in `tests/contract/` and validate that the **structure** of the
REST API matches our documented standards before we even exercise the endpoints
with property-based tools:

| What is verified? | Examples of checks |
|-------------------|--------------------|
| **Viewset registration** | Every viewset class is registered in at least one router & exposed under `/api/v1/…` URLs |
| **Required attributes**  | `serializer_class` and authentication permissions are declared |
| **URL consistency**      | All paths start with the version prefix `/api/v1/` |
| **OpenAPI coverage**     | The generated OpenAPI document contains every route and passes OpenAPI 3.1 validation |
| **Security docs**        | Token / JWT security schemes are present in the schema |

### 5.1 Running contract tests

```bash
# run only the structural contract suite
python manage.py test tests.contract
```

Contract tests are fast (pure introspection) and run **before** Schemathesis in
CI so that obvious structural problems fail quickly.

### 5.2 Contract vs Schemathesis

* **Contract tests**: Static assertions about routers, viewsets & schema
  generation.
* **Schemathesis** (next section): Dynamic, property-based testing that makes
  HTTP requests generated from the schema.

Both layers are complementary and together give high confidence in API quality.

---

## 6. Contract Testing with Schemathesis

| Key Point                         | Value / Command                                                                                          |
|----------------------------------|-----------------------------------------------------------------------------------------------------------|
| Spec source                       | `api/openapi.yaml` (generated by `drf-spectacular` ≥0.28, OpenAPI 3.1)                                    |
| Hooks module                      | `aquamind.utils.schemathesis_hooks` (exported via `SCHEMATHESIS_HOOKS`)                                   |
| Auth token generation             | `python manage.py get_ci_token --settings=aquamind.settings_ci`                                           |
| Example count                     | **10** (`--hypothesis-max-examples=10`) — balance coverage vs speed                                       |
| Common flags                      | `--checks all --hypothesis-derandomize --hypothesis-suppress-health-check=filter_too_much,data_too_large` |
| Integer-clamp hook                | `clamp_integer_schema_bounds` prevents SQLite int overflow                                                |

### Local quick-start

```bash
# 1. Install & migrate (SQLite)
pip install schemathesis
python manage.py migrate --settings=aquamind.settings_ci

# 2. Run dev server
python manage.py runserver 8000 --settings=aquamind.settings_ci &

# 3. Fetch auth token
TOKEN=$(python manage.py get_ci_token --settings=aquamind.settings_ci)

# 4. Contract test
schemathesis run \
  --base-url=http://127.0.0.1:8000 \
  --checks all \
  --hypothesis-max-examples=10 \
  --header "Authorization: Token $TOKEN" \
  api/openapi.yaml
```

---

## 7. Decimal Formatting Standards

| Context                          | Decimal Places | Example  |
|---------------------------------|---------------|----------|
| Currency / Mass inputs (kg)     | **2**         | `100.00` |
| Precision feed amounts (kg)     | **4**         | `5.0000` |

Unit & contract tests assert these exact formats to avoid drift.

---

## 8. Troubleshooting Checklist

| Symptom / Error                              | Likely Cause & Fix                                                         |
|----------------------------------------------|----------------------------------------------------------------------------|
| _`OverflowError: int too large for SQLite`_  | Ensure hooks env var set; run with `settings_ci`; integer clamp hook active |
| Schemathesis hangs at server start           | Dev server not running; check port 8000 or wait-loop in workflow           |
| Failing decimal assertions                   | Check serializer `decimal_places` vs test expectation (2 vs 4)             |
| `ModuleNotFoundError` for hooks              | Export `SCHEMATHESIS_HOOKS=aquamind.utils.schemathesis_hooks`              |
| Playwright cannot find browser               | `npx playwright install` before running UI tests                           |

---

## 9. Further Reading

* `api_contract_synchronization.md` — cross-repo spec workflow  
* `api_standards.md` — docstring conventions  
* GitHub Actions workflow: `.github/workflows/django-tests.yml`

---

**Keep tests lean, deterministic, and contract-aware.** When adding new endpoints:

1. Write/extend DRF tests.  
2. Regenerate & commit `openapi.yaml`.  
3. Verify Schemathesis passes locally (`max-examples=1` for speed).  
4. Push & let CI validate with full suite (10 examples).  
