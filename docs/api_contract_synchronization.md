# API Contract Synchronization

This document describes the automated system for maintaining synchronization between the AquaMind API implementation and its OpenAPI specification. This system ensures that the TypeScript client generated for the frontend always matches the actual API behavior.

## 1. Overview

The API contract synchronization system consists of several integrated components:

- **Automated tests** that verify OpenAPI specification completeness and correctness
- **Pre-commit hooks** that regenerate the OpenAPI spec when API code changes
- **GitHub workflow checks** that prevent merging PRs with out-of-sync specifications
- **Management commands** for validating and fixing OpenAPI specification issues
- **Spectacular hooks** that ensure proper response documentation

Together, these components form a comprehensive system that:

1. Prevents API contract mismatches between backend and frontend
2. Ensures all endpoints document proper response codes (401, 403, 404, 500)
3. Maintains proper integer bounds for SQLite compatibility
4. Validates schema conformance with OpenAPI standards
5. Automates the regeneration of the OpenAPI specification

## 2. Pre-commit Hooks

### 2.1 Configuration

The pre-commit hooks are configured in `.pre-commit-config.yaml`:

```yaml
# Custom hook to regenerate OpenAPI spec
- repo: local
  hooks:
    - id: regenerate-openapi-spec
      name: Regenerate OpenAPI Spec
      entry: python manage.py spectacular --file api/openapi.yaml --settings=aquamind.settings
      language: system
      pass_filenames: false
      files: >
        (apps/.+/(api|viewsets|serializers|routers)/.+\.py)|
        (aquamind/api/.+\.py)|
        (aquamind/utils/openapi_utils\.py)
      types: [python]
      stages: [commit]
      verbose: true
```

### 2.2 Helper Script

For manual regeneration, use the `scripts/regenerate_openapi.sh` script:

```bash
# Regenerate the OpenAPI spec
./scripts/regenerate_openapi.sh
```

This script:
1. Regenerates the spec using the Django management command
2. Checks if the spec has changed
3. Stages the changes for commit if needed

### 2.3 Installation

To install the pre-commit hooks:

```bash
# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install
```

## 3. GitHub Workflow Checks

### 3.1 Dedicated OpenAPI Check Workflow

The `.github/workflows/openapi-spec-check.yml` workflow runs on every PR that modifies API-related files:

- Triggers on changes to API code or the OpenAPI spec file
- Generates a fresh OpenAPI spec
- Compares it with the committed version
- Fails if they don't match, with detailed error information
- Provides instructions on how to fix the issue

### 3.2 Integration with Main CI/CD Pipeline

The main CI/CD pipeline (`.github/workflows/django-tests.yml`) includes:

- Running the OpenAPI spec completeness tests
- Generating the OpenAPI spec as an artifact
- Running Schemathesis validation against the spec
- Triggering the frontend repository to regenerate the TypeScript client

## 4. Management Commands

### 4.1 validate_openapi

The `validate_openapi` management command provides a comprehensive validation tool:

```bash
# Check if the OpenAPI spec is valid and in sync
python manage.py validate_openapi

# Check and automatically fix issues
python manage.py validate_openapi --fix

# Run in CI mode (exit with error code on failure)
python manage.py validate_openapi --check

# Run schemathesis validation
python manage.py validate_openapi --schemathesis

# Save the generated spec to a file
python manage.py validate_openapi --output=/tmp/spec.yaml
```

This command validates:
- Schema format compliance with OpenAPI standards
- Required hook configuration
- Response code documentation
- Synchronization with the committed spec
- (Optional) Schemathesis validation for runtime contract compliance

## 5. Testing the OpenAPI Spec

### 5.1 OpenAPISpecTestCase

The `OpenAPISpecTestCase` in `apps/infrastructure/tests/test_openapi_spec.py` provides comprehensive tests for:

- Schema generation without errors
- Schema validation against OpenAPI standards
- Response code documentation (200, 401, 403, 404, 500)
- Integer field bounds for SQLite compatibility
- Validation error responses for write operations
- Security requirements documentation
- Spectacular hook configuration
- Inclusion of all viewsets and custom actions

### 5.2 Running the Tests

```bash
# Run all OpenAPI spec tests
python manage.py test apps.infrastructure.tests.test_openapi_spec

# Run a specific test
python manage.py test apps.infrastructure.tests.test_openapi_spec.OpenAPISpecTestCase.test_all_endpoints_have_proper_response_documentation
```

## 6. Troubleshooting Common Issues

### 6.1 Missing Response Codes

**Problem**: The OpenAPI spec is missing standard response codes (401, 403, 404, 500)

**Solution**: 
1. Ensure the `add_standard_responses` hook is configured in settings
2. Run `python manage.py validate_openapi --fix` to regenerate the spec

### 6.2 Hook Configuration Issues

**Problem**: Required hooks are missing or in the wrong order

**Solution**:
Ensure these hooks are configured in both `settings.py` and `settings_ci.py`:

```python
SPECTACULAR_SETTINGS = {
    # ... other settings ...
    'POSTPROCESSING_HOOKS': [
        'aquamind.utils.openapi_utils.ensure_global_security',
        'aquamind.utils.openapi_utils.add_standard_responses',
        'aquamind.utils.openapi_utils.fix_action_response_types',
        'aquamind.utils.openapi_utils.cleanup_duplicate_security',
        'aquamind.utils.openapi_utils.add_validation_error_responses',
        'aquamind.utils.openapi_utils.clamp_integer_schema_bounds',
    ],
}
```

### 6.3 Schema Validation Errors

**Problem**: The schema fails validation with drf-spectacular

**Solution**:
1. Check for proper type hints in serializers
2. Add `@extend_schema_field` for custom fields
3. Fix serializer method fields with proper return type annotations

### 6.4 Out-of-Sync Specification

**Problem**: The GitHub workflow fails because the spec is out of sync

**Solution**:
```bash
# Regenerate and commit the spec
./scripts/regenerate_openapi.sh
git commit -m "Update OpenAPI spec to match implementation"
```

## 7. Developer Workflow Guidelines

### 7.1 When Adding or Modifying Endpoints

1. Implement the endpoint with proper docstrings and type hints
2. Run `./scripts/regenerate_openapi.sh` to update the spec
3. Run `python manage.py validate_openapi` to verify completeness
4. Commit both the implementation and updated spec together

### 7.2 When Reviewing PRs

1. Check that the OpenAPI spec has been updated if API changes are present
2. Verify that the OpenAPI spec check workflow passes
3. Ensure all endpoints have proper response documentation

## 8. Adding New Endpoints Properly

### 8.1 Documentation Requirements

```python
@extend_schema(
    description="Retrieves infrastructure overview statistics",
    responses={
        200: InfrastructureOverviewSerializer,
        401: OpenApiResponse("Unauthorized"),
        403: OpenApiResponse("Forbidden"),
        500: OpenApiResponse("Internal Server Error"),
    },
    tags=["infrastructure"]
)
def get(self, request):
    """
    Get infrastructure overview statistics.
    
    Returns aggregated data about containers, biomass, and feeding events.
    """
    # Implementation...
```

### 8.2 Response Code Standards

All endpoints must document:
- `200` - Successful response
- `401` - Unauthorized (missing authentication)
- `403` - Forbidden (insufficient permissions)
- `500` - Internal Server Error

Additional codes based on endpoint type:
- Detail endpoints: `404` - Not Found
- Write operations: `400` - Validation Error

### 8.3 Testing Considerations

1. Add the endpoint to `test_all_actions_included` if it's a custom action
2. Ensure it passes `test_all_endpoints_have_proper_response_documentation`
3. Add Schemathesis tests if it has complex validation or business logic

## 9. Best Practices

### 9.1 OpenAPI Documentation

- Use descriptive operation IDs and summaries
- Document all parameters with descriptions and examples
- Provide comprehensive response schemas
- Use proper tags for logical API grouping

### 9.2 Response Documentation

- Always document all possible response codes
- Include detailed error response schemas
- Use consistent error response formats

### 9.3 Schema Maintenance

- Run `validate_openapi` regularly to catch issues early
- Keep the pre-commit hooks enabled
- Update the spec whenever API changes are made
- Run the OpenAPI spec tests as part of your development workflow

### 9.4 TypeScript Client Compatibility

- Ensure all response types are properly documented
- Maintain consistent naming conventions
- Avoid breaking changes to existing endpoints
- Test the generated TypeScript client against the frontend

## 10. References

- [DRF Spectacular Documentation](https://drf-spectacular.readthedocs.io/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Schemathesis Documentation](https://schemathesis.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)
