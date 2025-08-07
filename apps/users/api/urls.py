"""
Development-only authentication endpoints
=========================================

This URL configuration **must not** be enabled in production environments.
It exists solely to support:

1.  **Automated test suites** (unit tests, Schemathesis, CI pipelines) that
    need a quick token without going through the full JWT flow.
2.  **Local API exploration** via tools like `httpie` or `curl` where devs want
    a throw-away token (or the built-in `dev-auth/` helper) while iterating.

Key differences from the *production* authentication system exposed in
`apps.users.urls`:

* Uses **DRF TokenAuthentication** (`Token` model) instead of JWT.
* Mounted under `/auth/…` in `aquamind/api/router.py`, whereas the primary JWT
  endpoints live under `/users/auth/…`.
* The `dev-auth/` helper is **disabled when `DEBUG` is False** to prevent
  accidental exposure in staging/production.
"""

from django.urls import path

from .views import CustomObtainAuthToken, dev_auth

urlpatterns = [
    # ------------------------------------------------------------------ #
    # Obtain a DRF auth token (username & password required)              #
    # ------------------------------------------------------------------ #
    path('token/', CustomObtainAuthToken.as_view(), name='api-token-auth'),

    # ------------------------------------------------------------------ #
    # Development helper – returns a token for a default 'devuser'.       #
    # Only available when settings.DEBUG is True.                         #
    # ------------------------------------------------------------------ #
    path('dev-auth/', dev_auth, name='api-dev-auth'),
]
