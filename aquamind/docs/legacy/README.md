# Legacy API Documentation (Deprecated)

These files are kept only for historical reference.  
They **no longer represent the authoritative AquaMind API** and **will not receive further updates**.

## New Single-Source-of-Truth

| Resource | Location |
|----------|----------|
| **OpenAPI 3.1 spec** | `api/openapi.yaml` (in the backend repository) |
| **Swagger UI** | `/api/schema/swagger-ui/` |
| **ReDoc** | `/api/schema/redoc/` |

The OpenAPI specification is generated automatically from the Django codebase and is published by CI on every successful backend build.  
Frontend TypeScript clients are now regenerated directly from this spec.

## What to Do

* Developers and integrators should use the endpoints listed above.  
* If you find references to these legacy Markdown or Postman files, please update them to point to the Swagger UI or the raw `openapi.yaml` spec.  
* Feel free to delete any unused legacy snippets in your branches once confirmations are complete.

> **Reminder:** Pull requests that modify the API must update the OpenAPI spec (generated automatically) and pass contract tests in CI.
