# AquaMind Testing Strategy

This document outlines the testing approach for the AquaMind project, including testing practices, conventions, and when and how tests should be run.

## 1. Testing Philosophy
*(content unchanged)*

## 2. Types of Tests
*(content unchanged)*

## 3. Testing Structure
*(content unchanged)*

## 4. Testing Best Practices
*(content unchanged)*

## 5. When to Run Tests
*(content unchanged)*

## 6. Test Coverage
*(content unchanged)*

## 7. Test Performance
*(content unchanged)*

## 8. Continuous Integration Setup
*(content unchanged)*

## 9. Test Troubleshooting
*(content unchanged)*

## 10. Platform-Specific Considerations
*(content unchanged)*

---

## 11. API Contract Testing with Schemathesis

### 11.1 Why Schemathesis?
We chose **Schemathesis** because it bridges two important needs:
1. **Contract validation** – Verifies at runtime that every endpoint implementation conforms to our generated OpenAPI 3.1 specification (`api/openapi.yaml`).
2. **Property-based testing** – Automatically generates a diverse set of requests (payload shapes, edge-case values, parameter combinations) uncovering cases humans rarely think to write.

Compared with snapshot-style “golden” tests or manually-authored Postman collections, Schemathesis gives deeper coverage with less maintenance.

### 11.2 How Property-Based Testing Works
Schemathesis is built on Hypothesis.  
For each operation in the OpenAPI spec it:
1. Derives Hypothesis strategies from the parameter & schema constraints.
2. Generates *examples* that satisfy those strategies (including boundary values, unexpected combinations, etc.).
3. Sends the requests to the running server and asserts status codes, JSON schema validity, headers, etc.
4. Shrinks failures to a minimal reproducible example.

### 11.3 SQLite Integer-Overflow Challenges
Our CI pipeline runs against **SQLite** for speed. SQLite stores `INTEGER` values in signed 64-bit range (−2^63 … 2^63−1).  
Hypothesis may create much larger integers, causing:

```
OverflowError: Python int too large to convert to SQLite INTEGER
```

**Solution implemented:**

* A post-processing hook (`aquamind.utils.openapi_utils.clamp_integer_schema_bounds`) clamps every integer in the generated OpenAPI schema to SQLite-safe limits.
* `settings_ci.py` registers this hook via `SPECTACULAR_SETTINGS['POSTPROCESSING_HOOKS']`.
* CI workflow reduces example count and suppresses noisy health-checks (see below).

### 11.4 CI Configuration
Key flags in `.github/workflows/django-tests.yml`:

```
schemathesis run \
  --base-url=http://127.0.0.1:8000 \
  --checks all \
  --hypothesis-max-examples=10 \
  --hypothesis-suppress-health-check=filter_too_much,data_too_large \
  --hypothesis-derandomize \
  --header "Authorization: Token $TOKEN" \
  api/openapi.yaml
```

* **`--hypothesis-max-examples=10`**   Faster runs while still exercising each endpoint.  
* **Health-check suppressions** avoid false-positive noise in CI logs.  
* **Auth header** uses a token generated via `get_ci_token` management command.  

### 11.5 Running Schemathesis Locally

```
# Activate your venv first
pip install schemathesis

# 1. Start the dev server on SQLite (mirrors CI)
python manage.py migrate --settings=aquamind.settings_ci
python manage.py runserver 8000 --settings=aquamind.settings_ci &

# 2. Fetch a token
TOKEN=$(python manage.py get_ci_token --settings=aquamind.settings_ci)

# 3. Run contract tests (same flags as CI)
schemathesis run \
  --base-url=http://127.0.0.1:8000 \
  --checks all \
  --hypothesis-max-examples=10 \
  --hypothesis-derandomize \
  --header "Authorization: Token $TOKEN" \
  api/openapi.yaml
```

Tips:

* Use `--app=django` if you prefer the “Django-in-thread” mode (`schemathesis run --app=aquamind.asgi:application …`) but note that it bypasses URL routing middlewares.
* Add `-q` for quieter output or `-v` for verbose Hypothesis tracing.

### 11.6 Benefits of Contract Testing

| Benefit | Impact |
|---------|--------|
| **Early detection of spec drift** | CI fails as soon as an endpoint response deviates from the OpenAPI spec. |
| **Security checks** | Schemathesis fuzzes headers & bodies revealing 400/500s, unhandled errors, and auth leaks. |
| **Living documentation** | Passing tests guarantee our spec truly matches the implementation, enabling reliable code-gen for the React client. |
| **Regression resistance** | A newly introduced bug is caught even without an explicit unit test because Hypothesis re-discovers edge cases. |
| **Reduced manual test burden** | Developers focus on critical business logic; Schemathesis handles permutations. |

---

## 12. Future Testing Strategy
*(section renumbered; content unchanged)*

## 13. Testing Resources
*(section renumbered; content unchanged)*
