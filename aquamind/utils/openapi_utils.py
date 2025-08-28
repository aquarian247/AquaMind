"""
OpenAPI Schema Utilities for AquaMind.

This module provides utilities for modifying and enhancing OpenAPI schemas,
particularly for compatibility with different database backends.

The primary focus is on making schemas compatible with SQLite in CI environments
by limiting integer ranges to prevent overflow errors during testing.
"""
import logging
from typing import Dict, Any, Optional, List, Union

# Define SQLite integer limits
# SQLite stores INTEGER values as 64-bit signed integers
SQLITE_MAX_INT = 9223372036854775807  # 2^63 - 1
SQLITE_MIN_INT = -9223372036854775808  # -2^63

logger = logging.getLogger(__name__)


def clamp_integer_schema_bounds(
    result: Dict[str, Any],
    *,
    generator: Any = None,
    request: Any = None,
    public: bool | None = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Post-processing hook for drf-spectacular that clamps integer fields to SQLite's safe range.
    
    This function is designed to be used as a post-processing hook in drf-spectacular's
    SPECTACULAR_SETTINGS to ensure that all integer fields in the schema have bounds
    that are compatible with SQLite's INTEGER storage limitations.
    
    This signature follows drf-spectacular's post-processing hook contract
    (``hook(result=..., generator=..., request=..., public=...)``). Only the
    ``result`` parameter is used – the others are accepted for compatibility.

    Args:
        result: The OpenAPI schema dictionary to modify
        
    Returns:
        The modified schema with integer bounds clamped to SQLite's safe range
        
    Example:
        # In settings_ci.py:
        SPECTACULAR_SETTINGS = {
            'POSTPROCESSING_HOOKS': [
                'aquamind.utils.openapi_utils.clamp_integer_schema_bounds',
            ],
        }
    """
    logger.info("Applying SQLite integer bounds to OpenAPI schema")
    
    # spectacular passes the schema in ``result`` – keep original name for
    # clarity in the rest of the function.
    schema = result

    # Process components schemas
    if 'components' in schema and 'schemas' in schema['components']:
        _process_schema_objects(schema['components']['schemas'])
    
    # Process path parameters and responses
    if 'paths' in schema:
        _process_paths(schema['paths'])
    
    return schema


def ensure_global_security(
    result: Dict[str, Any],
    *,
    generator: Any = None,
    request: Any = None,
    public: bool | None = None,
    **kwargs,
) -> Dict[str, Any]:
    """Ensure a *global* ``security`` requirement exists in the OpenAPI spec.

    Some tooling (including Schemathesis) relies on a top-level ``security``
    block to decide which authentication headers to send by default.  While
    drf-spectacular infers ``components.securitySchemes`` from DRF
    authentication classes, it will emit the top-level list only if *every*
    view explicitly declares a requirement—an easily missed detail that
    results in anonymous requests during contract testing.

    This hook ensures that the schema always contains::

        security:
          - tokenAuth: []

    If a different or more specific set of schemes is already present, the hook
    leaves it untouched.

    Note: Public endpoints (like health-check) will still be marked as requiring
    auth in the global security block, but their individual view permissions
    take precedence at runtime.
    """
    schema = result  # alias
    if not schema.get("security"):
        logger.info("Adding global tokenAuth security requirement to OpenAPI schema")
        schema["security"] = [{"tokenAuth": []}]

        # Remove security requirements from explicitly public endpoints
        public_endpoints = ['/health-check/']
        for endpoint_path in public_endpoints:
            if endpoint_path in schema.get("paths", {}):
                for method, operation in schema["paths"][endpoint_path].items():
                    if isinstance(operation, dict) and "security" in operation:
                        logger.info(f"Removing security requirement from public endpoint: {endpoint_path}")
                        del operation["security"]

    return schema


# --------------------------------------------------------------------------- #
#                    ***  NEW POST-PROCESSING HOOK  ***                       #
# --------------------------------------------------------------------------- #
def add_standard_responses(
    result: Dict[str, Any],
    *,
    generator: Any = None,
    request: Any = None,
    public: bool | None = None,
    **kwargs,
) -> Dict[str, Any]:
    """Insert baseline error responses (401, 403, 404, 500) where missing.

    The hook adds minimal ``description`` stubs only when a response is not
    already documented:
    • 404 – for any path containing a parameter segment (e.g. ``/items/{id}/``)
    • 401 & 403 – for operations that declare a non-anonymous security block
    • 500 – for **all** operations
    
    Only minimal ``description`` stubs are inserted; project-specific schemas
    can still override them via ``components.responses``.
    """
    logger.info("Ensuring standard 401/403/404/500 responses are present")

    schema = result  # alias for clarity

    added_counts = {"401": 0, "403": 0, "404": 0, "500": 0}

    def _ensure_response(responses: Dict[str, Any], status: str, description: str) -> None:
        if status not in responses:
            responses[status] = {"description": description}
            added_counts[status] += 1

    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in {
                "get",
                "post",
                "put",
                "delete",
                "patch",
                "head",
                "options",
                "trace",
            }:
                continue

            # Ensure responses container exists
            responses: Dict[str, Any] = operation.setdefault("responses", {})

            # --- 404 for detail/templated paths ---------------------------------
            if "{" in path and "}" in path:
                _ensure_response(responses, "404", "Not Found")

            # ------------------------------------------------------------------
            # 401 / 403 for *all* non-public endpoints
            # ------------------------------------------------------------------
            # Public endpoints are:
            #   • the API root (/api/)
            #   • schema endpoints (/api/v1/schema …)
            #   • authentication endpoints (/api/auth/… or /api/v1/auth/…)
            #
            # Everything else should advertise that unauthenticated /
            # unauthorised access is possible (401, 403).
            is_public_endpoint = (
                path == "/api/"
                or path.startswith("/api/v1/schema")
                or path.startswith("/api/auth/")
                or path.startswith("/api/v1/auth/")
            )

            if not is_public_endpoint:
                _ensure_response(responses, "401", "Unauthorized")
                _ensure_response(responses, "403", "Forbidden")

            # ------------------------------------------------------------------
            # SPECIAL-CASE: `/api/v1/auth/dev-auth/`
            # ------------------------------------------------------------------
            # This development endpoint is *intentionally* anonymous (`{}` in the
            # security array) but it can still return **401** when presented with
            # a *malformed* or expired token in the `Authorization` header that
            # Schemathesis fuzzes.  Ensure the 401 is documented so
            # status-code-conformance does not fail.
            if path == "/api/v1/auth/dev-auth/":
                _ensure_response(responses, "401", "Unauthorized")

            # --- 500 for all operations ----------------------------------------
            _ensure_response(responses, "500", "Internal Server Error")

    logger.info(
        "add_standard_responses added 401=%d, 403=%d, 404=%d, 500=%d entries",
        added_counts["401"],
        added_counts["403"],
        added_counts["404"],
        added_counts["500"],
    )
    return schema


# --------------------------------------------------------------------------- #
#             ***  HOOK: FIX @action LIST-STYLE RESPONSE TYPES  ***            #
# --------------------------------------------------------------------------- #
def fix_action_response_types(  # noqa: D202
    result: Dict[str, Any],
    *,
    generator: Any = None,
    request: Any = None,
    public: bool | None = None,
    **kwargs,
) -> Dict[str, Any]:
    """Handle DRF list-style ``@action`` responses.

    Many DRF ``@action(detail=False)`` endpoints are *list* actions that return
    **arrays** but drf-spectacular frequently documents them with the serializer
    for a *single* object.  Schemathesis then flags a type-mismatch when the
    implementation legitimately returns ``[]``.

    This hook looks for well-known list-action suffixes (``/recent/``,
    ``/stats/``, ``/by_batch/`` …) and, *for GET operations only*, wraps any
    object-type success schema (2xx) in an ``array`` when it is currently
    declared as an ``object``.

    It is deliberately conservative:
        • Touches **only** the first media-type in the success response.
        • Leaves schemas that already declare ``type: array`` untouched.
        • Skips operations that use ``oneOf`` / ``anyOf`` / ``allOf`` as these
          are assumed to be intentionally polymorphic.
    """  # noqa: D202

    list_suffixes = (
        "/recent/",
        "/stats/",
        "/by_batch/",
        "/by_container/",
        "/low_stock/",
        "/fifo_order/",
        "/active/",
        "/overdue/",
        "/compare/",
        "/lineage/",
    )

    schema = result  # alias
    patched_ops: list[str] = []

    for path, path_item in schema.get("paths", {}).items():
        if not any(path.endswith(suffix) for suffix in list_suffixes):
            continue  # Not a candidate

        for method, operation in path_item.items():
            if method != "get":
                continue

            responses: Dict[str, Any] = operation.get("responses", {})
            for status_code, response in responses.items():
                # Only patch 2xx responses
                if not status_code.startswith("2"):
                    continue
                content = response.get("content")
                if not content:
                    continue

                # Use first declared media-type (usually application/json)
                media_type_schema: Optional[Dict[str, Any]] = None
                for media in content.values():
                    media_type_schema = media.get("schema")
                    break
                if not media_type_schema:
                    continue

                # Skip if already array / polymorphic
                if media_type_schema.get("type") == "array":
                    continue
                if any(key in media_type_schema for key in ("oneOf", "anyOf", "allOf")):
                    continue

                # Wrap existing schema
                new_schema = {
                    "type": "array",
                    "items": media_type_schema.copy(),
                }
                # Apply inplace replacement
                for media in content.values():
                    media["schema"] = new_schema

                patched_ops.append(f"{method.upper()} {path} ({status_code})")

    if patched_ops:
        logger.info(
            "fix_action_response_types wrapped %d list-action responses: %s",
            len(patched_ops),
            "; ".join(patched_ops),
        )
    else:
        logger.info("fix_action_response_types: no endpoints required patching")

    return schema


def cleanup_duplicate_security(  # noqa: D202
    result: Dict[str, Any],
    *,
    generator: Any = None,
    request: Any = None,
    public: bool | None = None,
    **kwargs,
) -> Dict[str, Any]:
    """Remove duplicate entries from ``security`` blocks.

    This post-processing hook deduplicates repeated authentication schemes
    produced by drf-spectacular and strips anonymous markers where not allowed.

    The signature follows drf-spectacular's post-processing contract.
    Only the ``result`` (the full schema) is mutated.
    """
    logger.info("De-duplicating security requirements in OpenAPI schema")

    schema = result  # alias for clarity

    # Endpoints that legitimately allow anonymous access.  Keep the "{}"
    # placeholder for these so that contract-testing tools know anonymous
    # requests are valid here.
    EXEMPT_ANON_PATHS = {
        "/api/v1/auth/token/",
        "/api/v1/auth/dev-auth/",
    }

    def _deduplicate(security_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return a list with duplicates removed (order preserved)."""
        seen: List[Dict[str, Any]] = []
        for item in security_list:
            if item not in seen:
                seen.append(item)
        return seen

    # Deduplicate top-level security (if present)
    if "security" in schema and isinstance(schema["security"], list):
        schema["security"] = _deduplicate(schema["security"])

    # Deduplicate per-operation security requirements
    # Iterate with both *path* and *path_item* so we can reference the path
    # later when deciding whether to strip anonymous access.
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method in {
                "get",
                "post",
                "put",
                "delete",
                "patch",
                "head",
                "options",
                "trace",
            }:
                # ---------------------------------------------------------------------
                # (A) Operation *already* declares security requirements
                # ---------------------------------------------------------------------
                if "security" in operation and isinstance(operation["security"], list):
                    operation["security"] = _deduplicate(operation["security"])

                    # Strip the anonymous `{}` marker except for whitelisted endpoints
                    if path not in EXEMPT_ANON_PATHS:
                        operation["security"] = [
                            entry for entry in operation["security"] if entry
                        ]

                # ---------------------------------------------------------------------
                # (B) Operation declares *no* security field at all
                #     → For endpoints that should allow anonymous access, inject it.
                # ---------------------------------------------------------------------
                elif path in EXEMPT_ANON_PATHS:
                    # Explicitly mark as anonymous so contract-testing tools
                    # recognise that authentication is optional here.
                    operation["security"] = [{}]

    return schema

def prune_legacy_paths(  # noqa: D202
    result: Dict[str, Any],
    *,
    generator: Any = None,
    request: Any = None,
    public: bool | None = None,
    **kwargs,
) -> Dict[str, Any]:
    """Remove legacy infrastructure paths from schema.

    This post-processing hook **removes every path** beginning with
    ``/api/v1/infrastructure/`` from the generated OpenAPI schema.

    Why remove the whole prefix?
    ----------------------------
    During **Phase 4 – API Contract Unification** the *infrastructure* API
    surface was migrated to the new batch-centric design.  The underlying
    Django routers have been deleted, yet drf-spectacular still discovers the
    (now-stale) viewsets via historical imports, leading to hundreds of `404`
    failures in Schemathesis runs.

    Stripping the entire prefix at schema-generation time guarantees the
    contract reflects only live endpoints without needing to micro-manage an
    ever-growing allow/deny list.
    """  # noqa: D202

    schema = result  # alias for clarity

    paths_dict = schema.get("paths", {})
    if not paths_dict:  # Nothing to do
        return schema

    removed_paths: list[str] = []

    # Cast to list to avoid 'dictionary changed size during iteration'
    for path in list(paths_dict.keys()):
        if path.startswith("/api/v1/infrastructure/"):
            removed_paths.append(path)
            paths_dict.pop(path, None)

    if removed_paths:
        logger.info("Pruned legacy infrastructure paths from OpenAPI schema: %s",
                    removed_paths)

    return schema

def add_validation_error_responses(  # noqa: D202
    result: Dict[str, Any],
    *,
    generator: Any = None,
    request: Any = None,
    public: bool | None = None,
    **kwargs,
) -> Dict[str, Any]:
    """Append a ``422 ValidationError`` response where missing.

    Contract-test tooling (e.g. Schemathesis) expects validation errors to be
    documented explicitly.  This hook inserts a minimal 422 object if the spec
    lacks one for a given operation.
    
    Strategy
    --------
    1. Add a ``400`` response to every **POST / PUT / PATCH** operation
       (payload validation errors are always possible here).
    2. Add a ``400`` response to **GET** operations that expose a ``page``
       query parameter (pagination rejects ``page=0`` & non-ints).
    
    That’s it – no 401 / 422 / 500 handling here.  Keep it small; expand only
    if the test suite shows clear gaps.
    """
    logger.info("Adding minimal 400-validation responses to OpenAPI schema")
    
    schema = result  # alias for clarity
    
    error_400_schema = {
        "description": "Bad request (validation error)"
    }
    
    # Process all paths and operations
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in {
                "get", "post", "put", "delete", "patch", "head", "options", "trace"
            }:
                continue
                
            # Get or initialize the responses object
            if "responses" not in operation:
                operation["responses"] = {}
            responses = operation["responses"]
            
            # ------------------------------------------------------------------
            # (1) Always for write-methods
            # (2) GET + explicit `page` parameter
            # ------------------------------------------------------------------
            if method in {"post", "put", "patch"}:
                needs_400 = True
            elif method == "get":
                needs_400 = any(
                    isinstance(p, dict) and p.get("name") == "page"
                    for p in operation.get("parameters", [])
                )
            else:
                needs_400 = False

            if needs_400 and "400" not in responses:
                responses["400"] = error_400_schema
    
    return schema

def _process_schema_objects(schemas: Dict[str, Any]) -> None:
    """
    Recursively process schema objects to clamp integer bounds.
    
    Args:
        schemas: Dictionary of schema objects to process
    """
    for schema_name, schema_obj in schemas.items():
        _process_schema_object(schema_obj)


def _process_schema_object(schema_obj: Dict[str, Any]) -> None:
    """
    Process a single schema object to clamp integer bounds.
    
    Args:
        schema_obj: Schema object to process
    """
    # Handle direct integer type
    if schema_obj.get('type') == 'integer':
        _clamp_integer_bounds(schema_obj)
    
    # Handle properties in objects
    if 'properties' in schema_obj:
        for prop_name, prop_schema in schema_obj['properties'].items():
            if isinstance(prop_schema, dict):
                _process_schema_object(prop_schema)
    
    # Handle array items
    if 'items' in schema_obj and isinstance(schema_obj['items'], dict):
        _process_schema_object(schema_obj['items'])
    
    # Handle allOf, oneOf, anyOf
    for combiner in ['allOf', 'oneOf', 'anyOf']:
        if combiner in schema_obj:
            for sub_schema in schema_obj[combiner]:
                if isinstance(sub_schema, dict):
                    _process_schema_object(sub_schema)


def _process_paths(paths: Dict[str, Any]) -> None:
    """
    Process paths in the OpenAPI schema to clamp integer bounds.
    
    Args:
        paths: Dictionary of paths to process
    """
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace']:
                # Process parameters
                if 'parameters' in operation:
                    for param in operation['parameters']:
                        if 'schema' in param:
                            _process_schema_object(param['schema'])
                
                # Process request body
                if 'requestBody' in operation and 'content' in operation['requestBody']:
                    for content_type, media_type in operation['requestBody']['content'].items():
                        if 'schema' in media_type:
                            _process_schema_object(media_type['schema'])
                
                # Process responses
                if 'responses' in operation:
                    for status, response in operation['responses'].items():
                        if 'content' in response:
                            for content_type, media_type in response['content'].items():
                                if 'schema' in media_type:
                                    _process_schema_object(media_type['schema'])


def _clamp_integer_bounds(schema_obj: Dict[str, Any]) -> None:
    """
    Clamp the minimum and maximum values of an integer schema to SQLite's safe range.
    
    Args:
        schema_obj: Integer schema object to clamp
    """
    # Set maximum if not set or if set higher than SQLite limit
    if 'maximum' not in schema_obj or schema_obj['maximum'] > SQLITE_MAX_INT:
        schema_obj['maximum'] = SQLITE_MAX_INT
    
    # Set minimum if not set or if set lower than SQLite limit
    if 'minimum' not in schema_obj or schema_obj['minimum'] < SQLITE_MIN_INT:
        schema_obj['minimum'] = SQLITE_MIN_INT
    
    # Handle exclusiveMinimum/exclusiveMaximum if present
    if schema_obj.get('exclusiveMaximum', False) and schema_obj['maximum'] >= SQLITE_MAX_INT:
        schema_obj['maximum'] = SQLITE_MAX_INT - 1
        schema_obj['exclusiveMaximum'] = False
    
    if schema_obj.get('exclusiveMinimum', False) and schema_obj['minimum'] <= SQLITE_MIN_INT:
        schema_obj['minimum'] = SQLITE_MIN_INT + 1
        schema_obj['exclusiveMinimum'] = False
