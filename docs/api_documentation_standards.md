# AquaMind API Documentation Standards

## 1. Overview

This document outlines the standards and best practices for documenting APIs within the AquaMind project. Consistent and comprehensive API documentation is crucial for developers consuming the API, whether they are internal team members or external integrators.

Our primary tool for generating API documentation is `drf-yasg`, which creates OpenAPI (Swagger) specifications from Django REST Framework (DRF) views, viewsets, serializers, and their docstrings. Adhering to these standards will ensure the generated documentation is accurate, informative, and user-friendly.

## 2. General Principles

-   **Clarity**: Documentation should be easy to understand, avoiding jargon where possible or explaining it if necessary.
-   **Completeness**: All endpoints, parameters, request bodies, and response structures (including error responses) should be documented.
-   **Consistency**: Use consistent terminology, formatting, and level of detail across all API documentation.
-   **Conciseness**: Be informative but avoid unnecessary verbosity.
-   **Audience-Focused**: Write for the API consumer, anticipating their questions and needs.

## 3. Docstring Standards

Docstrings are the primary source of information for `drf-yasg`. Well-written docstrings are essential.

### 3.1. ViewSets and APIViews

The main docstring for a ViewSet or APIView should provide a high-level overview of the resource or endpoint group.

```python
class BatchViewSet(viewsets.ModelViewSet):
    """
    Manages aquaculture batches.

    Provides CRUD operations for batches, including filtering and searching.
    Users must be authenticated to access these endpoints.
    """
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    # ...
```

### 3.2. ViewSet Actions and APIView Methods

Each action method (`list`, `create`, `retrieve`, `update`, `partial_update`, `destroy`) and any custom actions (`@action` decorated methods) within a ViewSet, or HTTP methods (`get`, `post`, `put`, `patch`, `delete`) in an APIView, should have its own docstring.

This docstring should detail:
-   A brief summary of what the operation does.
-   Any specific request parameters (path, query).
-   Expected request body (if applicable).
-   Successful response status codes and a description of the response body.
-   Potential error response status codes and their meanings.

```python
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class BatchViewSet(viewsets.ModelViewSet):
    # ...
    @swagger_auto_schema(
        operation_summary="List all batches",
        operation_description="Retrieves a paginated list of all aquaculture batches. Supports filtering by species and status.",
        manual_parameters=[
            openapi.Parameter('species_id', openapi.IN_QUERY, description="Filter by species ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by batch status (e.g., 'active', 'harvested')", type=openapi.TYPE_STRING)
        ],
        responses={
            200: BatchSerializer(many=True),
            401: "Unauthorized",
            403: "Permission denied"
        }
    )
    def list(self, request, *args, **kwargs):
        """
        List all batches.

        Retrieves a paginated list of all aquaculture batches.
        Supports filtering by `species_id` (integer) and `status` (string, e.g., 'active', 'harvested').
        """
        # ... implementation ...
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a new batch",
        request_body=BatchCreateSerializer,
        responses={
            201: BatchSerializer(),
            400: "Invalid input data"
        }
    )
    def create(self, request, *args, **kwargs):
        """
        Create a new batch.

        Requires batch number, species, and initial population count.
        """
        # ... implementation ...
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a specific batch",
        responses={
            200: BatchSerializer(),
            404: "Batch not found"
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific batch by its ID.
        """
        # ... implementation ...
        return super().retrieve(request, *args, **kwargs)

    # ... similar docstrings for update, partial_update, destroy ...
```

### 3.3. Serializers and Fields

Serializer docstrings should describe the data structure they represent. Each field within a serializer should have a `help_text` attribute explaining its purpose, format, and any constraints.

```python
from rest_framework import serializers
from .models import Batch

class BatchSerializer(serializers.ModelSerializer):
    """
    Serializer for Batch model. Represents an aquaculture batch.
    """
    batch_number = serializers.CharField(
        help_text="Unique identifier for the batch (e.g., BATCH001)."
    )
    species_name = serializers.CharField(
        source='species.common_name',
        read_only=True,
        help_text="Common name of the species in this batch."
    )
    # ... other fields ...

    class Meta:
        model = Batch
        fields = ['id', 'batch_number', 'species_name', 'status', 'created_at']
        help_text = "Detailed representation of an aquaculture batch."
```

## 4. Using `drf-yasg` Features

### 4.1. `@swagger_auto_schema` Decorator

For fine-grained control over the generated documentation for a specific view or action, use the `@swagger_auto_schema` decorator. This allows you to:
-   Set `operation_summary` and `operation_description`.
-   Manually define request parameters using `openapi.Parameter` in `manual_parameters`.
-   Specify the `request_body` serializer or schema.
-   Define `responses` with status codes and their corresponding serializers or descriptions.
-   Tag operations using `tags=['Your Tag']`.

### 4.2. `openapi.Parameter`

When `drf-yasg` cannot automatically infer query or path parameters (e.g., for complex filtering not handled by `django-filter`), define them manually:

```python
from drf_yasg import openapi

manual_parameters=[
    openapi.Parameter(
        'custom_filter',
        openapi.IN_QUERY,
        description="A custom filter parameter for specific logic.",
        type=openapi.TYPE_STRING,
        required=False
    )
]
```

### 4.3. Documenting Responses

Clearly document all possible HTTP response codes for each endpoint.
-   **2xx (Success)**: Describe the successful response body. Use the relevant serializer.
-   **4xx (Client Errors)**:
    -   `400 Bad Request`: For validation errors. `drf-yasg` usually handles this by showing the request serializer's fields.
    -   `401 Unauthorized`: If authentication is required and not provided/invalid.
    -   `403 Forbidden`: If the authenticated user does not have permission.
    -   `404 Not Found`: If the requested resource does not exist.
-   **5xx (Server Errors)**: General server error.

Example using `@swagger_auto_schema`:
```python
    @swagger_auto_schema(
        responses={
            200: SuccessResponseSerializer(),
            401: openapi.Response("Authentication credentials were not provided or were invalid."),
            403: openapi.Response("You do not have permission to perform this action."),
            404: openapi.Response("The requested resource was not found.")
        }
    )
    def get(self, request):
        # ...
```

## 5. Markdown in Docstrings

`drf-yasg` supports Markdown in docstrings. Use it to format descriptions, add lists, or emphasize important points.

## 6. Review and Maintenance

-   API documentation should be written concurrently with API development.
-   Documentation should be reviewed as part of the code review process.
-   Regularly check the generated Swagger/ReDoc UI to ensure accuracy and completeness.
-   Update documentation whenever the API changes.

## 7. Sharing Documentation

-   The primary way to access API documentation is via the `/swagger/` and `/redoc/` endpoints provided by `drf-yasg`.
-   The raw OpenAPI schema (e.g., `openapi.yaml` or `swagger.json`) can be downloaded from these UIs.
-   Consider committing the schema file to the repository (e.g., in `docs/api/openapi.yaml`) for versioning and easy sharing. GitHub can render these files.
