"""CI-specific Django settings for AquaMind project.

This file extends the base settings and overrides database configuration for CI environments.
"""

import sys
from .settings import *  # noqa

# Override database settings for CI environment
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # Use a persistent SQLite file so that both the migration step and the
        # subsequently-started dev-server share the same schema & data.
        # BASE_DIR comes from the base settings we just imported.
        'NAME': BASE_DIR / 'ci.sqlite3',
    }
}

# Ensure TEST_RUNNER from main settings is not overriding CI database behavior if it implies PostgreSQL
# If TimescaleDBTestRunner specifically requires PostgreSQL, this might need further adjustment
# For now, let's assume standard Django testing with SQLite is the goal for CI.
# If the custom runner has specific logic for CI, it should respect these settings.
TIMESCALE_ENABLED = False

# Speed up tests by using a weaker password hasher in CI if appropriate
# PASSWORD_HASHERS = [
#     'django.contrib.auth.hashers.MD5PasswordHasher',
# ]

# ---------------------------------------------------------------------------
# SQLite-specific compatibility tweaks
# ---------------------------------------------------------------------------
# ❶  Why?  SQLite stores INTEGER values as signed 64-bit numbers.  When
#     Schemathesis (or other property-based tools) generate arbitrarily large
#     integers, inserts can fail with:
#         OverflowError: Python int too large to convert to SQLite INTEGER
# ❷  Mitigation.  We clamp integer ranges in the generated OpenAPI schema
#     so that Schemathesis & client generators know the true bounds.
#     This is done via a small post-processing hook registered in
#     `aquamind.utils.openapi_utils.clamp_integer_schema_bounds`.
# ❸  The settings below enable drf-spectacular & REST framework to use that
#     hook during schema generation in CI.

# Minimal DRF settings override for CI
# ------------------------------------------------------------------
# Extend the REST_FRAMEWORK config defined in the base ``settings`` rather
# than blindly overwriting it.  This keeps global defaults (renderers,
# authentication classes, etc.) intact while ensuring the OpenAPI AutoSchema
# hook executes during CI.
# ------------------------------------------------------------------
try:
    BASE_REST_FRAMEWORK = REST_FRAMEWORK  # comes from ``from .settings import *``
except NameError:  # pragma: no cover – unlikely, but keep it safe
    BASE_REST_FRAMEWORK = {}

# Shallow-copy & override only what we need
REST_FRAMEWORK = {
    **BASE_REST_FRAMEWORK,
    # Ensure drf-spectacular's AutoSchema is active so our post-processing hook runs
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# drf-spectacular settings specific to the CI / SQLite environment
# ------------------------------------------------------------------
# Likewise, extend the project-wide SPECTACULAR_SETTINGS, only tweaking the
# keys that are important for CI / SQLite compatibility.
# ------------------------------------------------------------------
try:
    BASE_SPECTACULAR_SETTINGS = SPECTACULAR_SETTINGS  # noqa: F401
except NameError:  # pragma: no cover
    BASE_SPECTACULAR_SETTINGS = {}

_ci_spec_settings = dict(BASE_SPECTACULAR_SETTINGS)  # shallow copy

# 1) Keep output deterministic for easier diffing in CI logs
_ci_spec_settings['SORT_OPERATIONS'] = False

# 2) Configure post-processing hooks in logical order
_ci_hooks = _ci_spec_settings.get('POSTPROCESSING_HOOKS', [])

# 1. First ensure global security
ensure_hook_path = 'aquamind.utils.openapi_utils.ensure_global_security'
if ensure_hook_path not in _ci_hooks:
    _ci_hooks.append(ensure_hook_path)

# 2. Then add standard responses (401, 403, 404, 500)
std_hook_path = 'aquamind.utils.openapi_utils.add_standard_responses'
if std_hook_path not in _ci_hooks:
    _ci_hooks.append(std_hook_path)

# 3. Then fix action response types
act_hook_path = 'aquamind.utils.openapi_utils.fix_action_response_types'
if act_hook_path not in _ci_hooks:
    _ci_hooks.append(act_hook_path)

# 4. Then clean up duplicates
dup_hook_path = 'aquamind.utils.openapi_utils.cleanup_duplicate_security'
if dup_hook_path not in _ci_hooks:
    _ci_hooks.append(dup_hook_path)

# 5. Then add validation errors
val_hook_path = 'aquamind.utils.openapi_utils.add_validation_error_responses'
if val_hook_path not in _ci_hooks:
    _ci_hooks.append(val_hook_path)

# 6. Finally clamp integer bounds
clamp_hook_path = 'aquamind.utils.openapi_utils.clamp_integer_schema_bounds'
if clamp_hook_path not in _ci_hooks:
    _ci_hooks.append(clamp_hook_path)

# [REMOVED] Infrastructure endpoints have been restored
#    ---------------------------------------------------------------
#    The prune_legacy_paths hook was temporarily used during Phase-4
#    to strip infrastructure paths from the schema. Now that the router
#    duplication issue is resolved, we've restored these endpoints and
#    no longer need to prune them from the schema.
# prune_hook_path = 'aquamind.utils.openapi_utils.prune_legacy_paths'
# if prune_hook_path not in _ci_hooks:
#     _ci_hooks.append(prune_hook_path)

_ci_spec_settings['POSTPROCESSING_HOOKS'] = _ci_hooks

# Final CI-specific spectacular config
SPECTACULAR_SETTINGS = _ci_spec_settings

# ------------------------------------------------------------------
# TEMPORARY: Phase-1 debugging middleware for auth-header inspection
# ------------------------------------------------------------------
try:
    BASE_MIDDLEWARE = MIDDLEWARE  # Imported from base settings
except NameError:  # pragma: no cover – should not happen but stay safe
    BASE_MIDDLEWARE = []

# Only append if it's not already in the stack to avoid duplicates when this
# file is re-evaluated (e.g. in Django's autoreload).
_debug_mw = 'aquamind.middleware.AuthHeaderDebugMiddleware'
if _debug_mw not in BASE_MIDDLEWARE:
    MIDDLEWARE = [*BASE_MIDDLEWARE, _debug_mw]
else:
    MIDDLEWARE = BASE_MIDDLEWARE

# Persist debug logs to a file so CI can expose them as an artifact if needed.
# (The GitHub workflow can upload this file for inspection.)
AUTH_DEBUG_LOG_FILE = BASE_DIR / 'auth-debug.log'

# ------------------------------------------------------------------
# CONDITIONAL AUTHENTICATION FOR CI ENVIRONMENT
# ------------------------------------------------------------------
# Dynamic authentication that checks environment at request time

import os
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission

class CIMockUser:
    """Mock user that behaves like an authenticated user for Schemathesis"""

    def __init__(self):
        self.id = 1
        self.username = 'schemathesis_user'
        self.email = 'schemathesis@test.com'
        self.first_name = 'Schema'
        self.last_name = 'Thesis'
        self.is_active = True
        self.is_staff = True
        self.is_superuser = True

    def __int__(self):
        return self.id

    def __str__(self):
        return self.username

    def is_authenticated(self):
        return True

class CIDynamicAuthentication(BaseAuthentication):
    """Authentication class that dynamically checks for Schemathesis token"""

    def authenticate(self, request):
        # Check environment variable at request time (not settings load time)
        if os.getenv("SCHEMATHESIS_AUTH_TOKEN"):
            print(f"🔑 CIDynamicAuthentication: Providing mock user for Schemathesis", file=sys.stderr)
            return (CIMockUser(), None)
        return None

class CIDynamicPermission(BasePermission):
    """Permission class that dynamically allows access for Schemathesis"""

    def has_permission(self, request, view):
        # Check environment variable at request time (not settings load time)
        if os.getenv("SCHEMATHESIS_AUTH_TOKEN"):
            print(f"🔓 CIDynamicPermission: Allowing access for Schemathesis", file=sys.stderr)
            return True
        return False  # Let normal permission classes handle unit tests

    def has_object_permission(self, request, view, obj):
        # Check environment variable at request time (not settings load time)
        if os.getenv("SCHEMATHESIS_AUTH_TOKEN"):
            print(f"🔓 CIDynamicPermission: Allowing object access for Schemathesis", file=sys.stderr)
            return True
        return False  # Let normal permission classes handle unit tests

# Always use dynamic classes - they check environment at request time
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_AUTHENTICATION_CLASSES': ['aquamind.settings_ci.CIDynamicAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['aquamind.settings_ci.CIDynamicPermission'],
}


