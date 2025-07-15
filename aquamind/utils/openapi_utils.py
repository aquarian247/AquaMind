"""
OpenAPI Schema Utilities for AquaMind

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
