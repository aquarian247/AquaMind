# AquaMind — Testing Guide

_Last updated July 2025_

## 1. Test Pillars

| Layer          | Purpose                                           | Frameworks / Tools                 |
|----------------|---------------------------------------------------|------------------------------------|
| **Unit**       | Isolate functions, methods, model logic           | `django.test.TestCase` (Django runner) |
| **Integration**| Verify components working together (DB/API)       | DRF test client, Playwright*       |
| **API Smoke**  | Verify critical REST surfaces stay healthy        | DRF test client (`tests/api`)      |

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

> **Note**: We rely on Django’s built-in test runner (`python manage.py test`). `pytest` is available in the environment for developers who prefer its style, but CI relies solely on the Django runner.

### 3.2 Continuous Integration

GitHub Action `.github/workflows/django-tests.yml` automatically:

1. Installs deps & runs migrations (SQLite, `settings_ci`).
2. Executes full unit/integration suite (including `tests/api`).
3. Uploads coverage & artefacts.

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

## 5. API Test Suite

API regression coverage lives in `tests/api/`. These tests focus on essential read/write flows, authentication enforcement, and regression checks for high-risk endpoints.

### 5.1 Running API tests

```bash
# execute only API smoke/integration tests
python manage.py test tests.api

# run a single module for targeted debugging
python manage.py test tests.api.test_finance_nav_exports
```

### 5.2 Authoring guidelines

- Reuse helpers such as `get_api_url()` from existing test modules for path consistency.
- Exercise real serializers and permission classes; avoid mocking unless an external dependency cannot be hit in CI.
- Keep assertions focused on HTTP status, payload shape, and critical field values.
- When covering new endpoints, mirror the pagination/filter patterns already present in `tests/api`.

---

## 6. Decimal Formatting Standards

| Context                          | Decimal Places | Example  |
|---------------------------------|---------------|----------|
| Currency / Mass inputs (kg)     | **2**         | `100.00` |
| Precision feed amounts (kg)     | **4**         | `5.0000` |

Unit & contract tests assert these exact formats to avoid drift.

---

## 7. Troubleshooting Checklist

| Symptom / Error                              | Likely Cause & Fix                                                         |
|----------------------------------------------|----------------------------------------------------------------------------|
| _`OverflowError: int too large for SQLite`_  | Run with `--settings=aquamind.settings_ci`; this config clamps integers     |
| REST API test timeouts                       | Ensure dev server (where required) or mocked services run locally          |
| Failing decimal assertions                   | Check serializer `decimal_places` vs test expectation (2 vs 4)             |
| Missing Playwright browser                   | `npx playwright install` before running UI tests                           |

---

## 8. Further Reading

* `api_contract_synchronization.md` — cross-repo spec workflow  
* `api_standards.md` — docstring conventions  
* GitHub Actions workflow: `.github/workflows/django-tests.yml`

---

**Keep tests lean, deterministic, and contract-aware.** When adding new endpoints:

1. Write/extend DRF tests.  
2. Regenerate & commit `openapi.yaml`.  
3. Run targeted API regression tests (`python manage.py test tests.api`).  
4. Push & let CI validate with the full Django test suite.  
