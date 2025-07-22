# Front-End API Integration Guide

> File: `aquamind/docs/integration/frontend_api_integration.md`  
> Status: **Authoritative – supersedes all earlier frontend API docs**

## 1. Overview of the Simplified Architecture

```
┌────────────┐      ┌───────────────────────┐      ┌─────────────────────────┐
│ Svelte UI  │──▶──▶│  ApiService (generated) │──▶──│ AquaMind REST API (DRF) │
└────────────┘      └───────────────────────┘      └─────────────────────────┘
```

* **Single hop** from UI components to the backend.
* The generated `ApiService` (via `openapi-typescript-codegen`) is the sole gateway for network traffic.
* No intermediate “helper” layers (e.g., `django-api.ts`) are needed.

## 2. Decision to Remove `django-api.ts`

The former flow:

```
UI  → api.ts  → django-api.ts  → apiRequest  → REST API
```

Problems observed:

* Duplicate logic for headers, error handling, and base URL selection.
* Developers uncertain where to patch bugs.
* Harder to enforce authentication consistently.

**Outcome:** `client/src/lib/django-api.ts` is **deprecated and will be deleted**. All calls are routed through `ApiService`.

## 3. Direct Use of Generated `ApiService`

`openapi-typescript-codegen` creates type-safe clients from our OpenAPI spec.  
Key export: `ApiService` (plus resource-specific namespaces, e.g., `UsersService`, `ProjectsService`).

```ts
import { UsersService } from '$lib/generated';

const profile = await UsersService.usersMeRetrieve();
```

Why `ApiService` is sufficient:

* Handles `Authorization` header injection (see Section 5).
* Respects global security scheme defined in the OpenAPI contract.
* Automatically updates whenever the backend schema changes.

## 4. Configuration Requirements

File: `client/src/lib/config.ts`

```ts
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

export const AUTH_TOKEN_KEY = 'aquamine_token'; // localStorage key
```

Environment variables supported:

| Variable                 | Example                          | Purpose                       |
|--------------------------|----------------------------------|-------------------------------|
| `VITE_API_BASE_URL`      | `https://api.aquamind.ai/api`    | Base URL for the REST API     |
| `VITE_DEFAULT_PAGE_SIZE` | `20`                             | (Optional) pagination default |

The build pipeline (`vite`) injects these at compile-time.

## 5. Authentication Flow & Token Management

1. **Login**
   ```ts
   import { AuthService } from '$lib/generated';

   const { auth_token } = await AuthService.authLoginCreate({ username, password });
   localStorage.setItem(AUTH_TOKEN_KEY, auth_token);
   ```
2. **ApiService hook**

   `generated/core/ApiService.ts` is patched during generation to read the token:

   ```ts
   // executed before every request
   request.headers['Authorization'] = `Token ${localStorage.getItem(AUTH_TOKEN_KEY)}`;
   ```

3. **Logout**

   ```ts
   localStorage.removeItem(AUTH_TOKEN_KEY);
   ```

4. **Token refresh / expiry**

   Not yet implemented; planned via DRF-knox or simple re-login flow.

## 6. Example Code Snippets

### Fetch current user

```ts
import { UsersService } from '$lib/generated';

export async function getCurrentUser() {
  try {
    return await UsersService.usersMeRetrieve();
  } catch (e) {
    if (e.status === 401) {
      // redirect to login
    }
    throw e;
  }
}
```

### Create a new project

```ts
import { ProjectsService } from '$lib/generated';

export async function createProject(data) {
  return ProjectsService.projectsCreate({ requestBody: data });
}
```

### Global error handler (optional)

```ts
import { ApiError } from '$lib/generated';

window.addEventListener('unhandledrejection', (event) => {
  if (event.reason instanceof ApiError) {
    console.error('API error', event.reason);
  }
});
```

## 7. Benefits of the New Approach

* **Single source of truth** – authentication, base URL, and error handling live in one place.
* **Type safety** – all requests/ responses are strongly typed.
* **Less boilerplate** – no ad-hoc wrappers or duplicated fetch logic.
* **Easier upgrades** – regenerating the client after backend changes is usually sufficient.
* **Consistency** – aligns the frontend directly with the OpenAPI contract used by backend & tests.

## 8. Migration Notes (Three-Layer → Single-Layer)

| Step | Action | Tip |
|------|--------|-----|
| 1 | Delete imports from `django-api.ts`. | Search the codebase: `import .*django-api`. |
| 2 | Replace calls with generated service equivalents. | Use auto-import hints in IDE. |
| 3 | Remove `django-api.ts` and `apiRequest` utilities. | Ensure no build errors remain. |
| 4 | Verify environment variables are set (`VITE_API_BASE_URL`). | Local dev default will work if omitted. |
| 5 | Test login flow & a few CRUD operations. | Schemathesis CI guarantees contract conformance. |

> After completing these steps the legacy helper files may be deleted in a dedicated cleanup PR.

---

### Recommended Approach Going Forward

All **new** API calls **must** use the generated client. Custom wrappers should only be introduced if:

1. The OpenAPI generator cannot express a particular pattern, **and**
2. A shared abstraction demonstrably reduces code duplication.

When in doubt, use `ApiService` directly and keep logic close to features.
