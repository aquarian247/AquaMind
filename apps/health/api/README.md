# Health App API

## Overview

The Health app API provides endpoints for managing fish health monitoring, including health sampling events, lab samples, treatments, and mortality tracking. This API follows a standardized pattern for consistent behavior across all endpoints.

## Architecture

The Health app API follows a modular architecture with clear separation of concerns:

### Models

Models are organized by domain:
- `health_observation.py` - Models for health sampling events and observations
- `journal_entry.py` - Models for health journal entries
- `lab_sample.py` - Models for laboratory samples
- `mortality.py` - Models for mortality tracking
- `treatment.py` - Models for treatments and vaccinations

### Serializers

Serializers are organized by domain and follow a standardized pattern:
- All serializers inherit from `HealthBaseSerializer` for consistent error handling and field management
- Specialized mixins provide reusable functionality:
  - `HealthDecimalFieldsMixin` - For decimal field validation
  - `NestedHealthModelMixin` - For handling nested models
  - `UserAssignmentMixin` - For automatic user assignment

### Viewsets

Viewsets are organized by domain and follow a standardized pattern:
- All viewsets use mixins for consistent behavior:
  - `UserAssignmentMixin` - For automatic user assignment
  - `OptimizedQuerysetMixin` - For efficient database queries
  - `StandardFilterMixin` - For consistent filtering capabilities
- Specialized filter handling for complex field relationships

### Utilities

Utility modules provide reusable functionality:
- `utils.py` - Common utility functions and mixins
- `validation.py` - Complex validation logic
- `base.py` - Standardized serializer base classes

## API Endpoints

### Health Observation

- `/api/v1/health/health-parameters/` - CRUD operations for health parameters
- `/api/v1/health/health-sampling-events/` - CRUD operations for health sampling events
- `/api/v1/health/individual-fish-observations/` - CRUD operations for individual fish observations
- `/api/v1/health/fish-parameter-scores/` - CRUD operations for fish parameter scores

### Lab Samples

- `/api/v1/health/sample-types/` - CRUD operations for sample types
- `/api/v1/health/health-lab-samples/` - CRUD operations for health lab samples

### Mortality

- `/api/v1/health/mortality-reasons/` - CRUD operations for mortality reasons
- `/api/v1/health/mortality-records/` - CRUD operations for mortality records
- `/api/v1/health/lice-counts/` - CRUD operations for lice counts

### Treatment

- `/api/v1/health/vaccination-types/` - CRUD operations for vaccination types
- `/api/v1/health/treatments/` - CRUD operations for treatments

### Journal Entries

- `/api/v1/health/journal-entries/` - CRUD operations for journal entries

## Usage Examples

### Creating a Health Sampling Event

```python
# Example POST request to create a health sampling event
data = {
    "assignment": 1,
    "sampling_date": "2025-05-27",
    "number_of_fish_sampled": 10,
    "notes": "Regular health check",
    "individual_fish_observations": [
        {
            "fish_identifier": "F001",
            "weight_g": 250.5,
            "length_cm": 25.3,
            "parameter_scores": [
                {"parameter": 1, "score": 5},
                {"parameter": 2, "score": 4}
            ]
        },
        # Additional fish observations...
    ]
}
```

### Creating a Lab Sample

```python
# Example POST request to create a lab sample
data = {
    "batch_id": 1,
    "container_id": 2,
    "sample_type": 1,
    "sample_date": "2025-05-27",
    "date_sent_to_lab": "2025-05-28",
    "lab_reference_id": "LAB-2025-001",
    "findings_summary": "No pathogens detected"
}
```

## Error Handling

All API endpoints use standardized error handling:
- Field-specific errors are returned with descriptive messages
- Validation errors include the field name and reason for failure
- Complex validation errors are grouped by field

## Authentication and Permissions

All endpoints require authentication and use Django's built-in permission system.
