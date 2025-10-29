# Operational Scheduling API Specification

**Version**: 1.0  
**Last Updated**: October 28, 2025  
**Base URL**: `/api/v1/planning/`  
**Target Repository**: `aquarian247/AquaMind/aquamind/docs/progress/`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Common Patterns](#common-patterns)
4. [Endpoints](#endpoints)
   - [Planned Activities](#planned-activities)
   - [Activity Templates](#activity-templates)
   - [Scenario Integration](#scenario-integration)
   - [Batch Integration](#batch-integration)
5. [Error Handling](#error-handling)
6. [Examples](#examples)

---

## Overview

This document specifies the REST API for the Operational Scheduling feature in AquaMind. The API follows the AquaMind API Standards (see `aquamind/docs/quality_assurance/api_standards.md`) and uses Django REST Framework conventions.

### Base URL

All endpoints are prefixed with `/api/v1/`.

### Response Format

All responses use JSON format with consistent structure:

```json
{
  "id": 123,
  "field_name": "value",
  "nested_object": {
    "id": 456,
    "name": "Nested Object"
  },
  "computed_field": "computed_value"
}
```

List responses include pagination metadata:

```json
{
  "count": 100,
  "next": "https://api.example.com/api/v1/planning/planned-activities/?page=2",
  "previous": null,
  "results": [
    { "id": 1, "..." },
    { "id": 2, "..." }
  ]
}
```

---

## Authentication

All endpoints require authentication using Django REST Framework's token authentication or session authentication.

**Headers**:
```
Authorization: Token <your-api-token>
```

or use session-based authentication (cookies).

---

## Common Patterns

### Filtering

All list endpoints support filtering via query parameters:

```
GET /api/v1/planning/planned-activities/?scenario=1&status=PENDING
```

### Searching

List endpoints support full-text search via the `search` parameter:

```
GET /api/v1/planning/planned-activities/?search=vaccination
```

### Ordering

List endpoints support ordering via the `ordering` parameter:

```
GET /api/v1/planning/planned-activities/?ordering=-due_date
```

Use `-` prefix for descending order.

### Pagination

List endpoints are paginated by default (page size: 50). Use `page` parameter:

```
GET /api/v1/planning/planned-activities/?page=2
```

---

## Endpoints

### Planned Activities

#### List Planned Activities

**Endpoint**: `GET /api/v1/planning/planned-activities/`

**Description**: Retrieve a paginated list of planned activities.

**Query Parameters**:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `scenario` | integer | Filter by scenario ID | `?scenario=1` |
| `batch` | integer | Filter by batch ID | `?batch=206` |
| `activity_type` | string | Filter by activity type | `?activity_type=VACCINATION` |
| `status` | string | Filter by status | `?status=PENDING` |
| `container` | integer | Filter by container ID | `?container=977` |
| `overdue` | boolean | Filter overdue activities | `?overdue=true` |
| `due_date_after` | date | Filter activities after date | `?due_date_after=2024-12-01` |
| `due_date_before` | date | Filter activities before date | `?due_date_before=2024-12-31` |
| `search` | string | Full-text search in notes | `?search=vaccination` |
| `ordering` | string | Order results | `?ordering=-due_date` |
| `page` | integer | Page number | `?page=2` |

**Response**: `200 OK`

```json
{
  "count": 45,
  "next": "https://api.example.com/api/v1/planning/planned-activities/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "scenario": 1,
      "batch": 206,
      "activity_type": "VACCINATION",
      "activity_type_display": "Vaccination",
      "due_date": "2024-12-15",
      "status": "PENDING",
      "status_display": "Pending",
      "container": 977,
      "container_name": "Tank A-01",
      "notes": "First vaccination at 50g average weight",
      "created_by": 1,
      "created_by_name": "John Doe",
      "created_at": "2024-11-01T10:00:00Z",
      "updated_at": "2024-11-01T10:00:00Z",
      "completed_at": null,
      "completed_by": null,
      "completed_by_name": null,
      "transfer_workflow": null,
      "is_overdue": false
    }
  ]
}
```

---

#### Create Planned Activity

**Endpoint**: `POST /api/v1/planning/planned-activities/`

**Description**: Create a new planned activity.

**Request Body**:

```json
{
  "scenario": 1,
  "batch": 206,
  "activity_type": "VACCINATION",
  "due_date": "2024-12-15",
  "container": 977,
  "notes": "First vaccination at 50g average weight"
}
```

**Required Fields**:
- `scenario` (integer): Scenario ID
- `batch` (integer): Batch ID
- `activity_type` (string): Activity type (see choices below)
- `due_date` (date): Planned execution date (YYYY-MM-DD format)

**Optional Fields**:
- `container` (integer): Container ID
- `notes` (string): Free-text notes

**Activity Type Choices**:
- `VACCINATION`
- `TREATMENT`
- `CULL`
- `SALE`
- `FEED_CHANGE`
- `TRANSFER`
- `MAINTENANCE`
- `SAMPLING`
- `OTHER`

**Response**: `201 Created`

```json
{
  "id": 123,
  "scenario": 1,
  "batch": 206,
  "activity_type": "VACCINATION",
  "activity_type_display": "Vaccination",
  "due_date": "2024-12-15",
  "status": "PENDING",
  "status_display": "Pending",
  "container": 977,
  "container_name": "Tank A-01",
  "notes": "First vaccination at 50g average weight",
  "created_by": 1,
  "created_by_name": "John Doe",
  "created_at": "2024-11-28T14:30:00Z",
  "updated_at": "2024-11-28T14:30:00Z",
  "completed_at": null,
  "completed_by": null,
  "completed_by_name": null,
  "transfer_workflow": null,
  "is_overdue": false
}
```

**Error Responses**:

- `400 Bad Request`: Invalid data (missing required fields, invalid date format)
- `404 Not Found`: Referenced scenario, batch, or container does not exist

---

#### Retrieve Planned Activity

**Endpoint**: `GET /api/v1/planning/planned-activities/{id}/`

**Description**: Retrieve a single planned activity by ID.

**Path Parameters**:
- `id` (integer): Planned activity ID

**Response**: `200 OK`

```json
{
  "id": 123,
  "scenario": 1,
  "batch": 206,
  "activity_type": "VACCINATION",
  "activity_type_display": "Vaccination",
  "due_date": "2024-12-15",
  "status": "PENDING",
  "status_display": "Pending",
  "container": 977,
  "container_name": "Tank A-01",
  "notes": "First vaccination at 50g average weight",
  "created_by": 1,
  "created_by_name": "John Doe",
  "created_at": "2024-11-28T14:30:00Z",
  "updated_at": "2024-11-28T14:30:00Z",
  "completed_at": null,
  "completed_by": null,
  "completed_by_name": null,
  "transfer_workflow": null,
  "is_overdue": false
}
```

**Error Responses**:
- `404 Not Found`: Activity does not exist

---

#### Update Planned Activity

**Endpoint**: `PUT /api/v1/planning/planned-activities/{id}/`  
**Endpoint**: `PATCH /api/v1/planning/planned-activities/{id}/`

**Description**: Update a planned activity. Use `PUT` for full update, `PATCH` for partial update.

**Path Parameters**:
- `id` (integer): Planned activity ID

**Request Body** (PATCH example):

```json
{
  "due_date": "2024-12-20",
  "notes": "Updated notes: Delayed due to weather"
}
```

**Response**: `200 OK`

```json
{
  "id": 123,
  "scenario": 1,
  "batch": 206,
  "activity_type": "VACCINATION",
  "activity_type_display": "Vaccination",
  "due_date": "2024-12-20",
  "status": "PENDING",
  "status_display": "Pending",
  "container": 977,
  "container_name": "Tank A-01",
  "notes": "Updated notes: Delayed due to weather",
  "created_by": 1,
  "created_by_name": "John Doe",
  "created_at": "2024-11-28T14:30:00Z",
  "updated_at": "2024-11-28T15:45:00Z",
  "completed_at": null,
  "completed_by": null,
  "completed_by_name": null,
  "transfer_workflow": null,
  "is_overdue": false
}
```

**Error Responses**:
- `400 Bad Request`: Invalid data
- `404 Not Found`: Activity does not exist

---

#### Delete Planned Activity

**Endpoint**: `DELETE /api/v1/planning/planned-activities/{id}/`

**Description**: Delete a planned activity.

**Path Parameters**:
- `id` (integer): Planned activity ID

**Response**: `204 No Content`

**Error Responses**:
- `404 Not Found`: Activity does not exist

---

#### Mark Activity as Completed

**Endpoint**: `POST /api/v1/planning/planned-activities/{id}/mark-completed/`

**Description**: Mark a planned activity as completed. This is a custom action that updates the status, sets `completed_at` timestamp, and records the completing user.

**Path Parameters**:
- `id` (integer): Planned activity ID

**Request Body**: Empty (no body required)

**Response**: `200 OK`

```json
{
  "message": "Activity marked as completed",
  "activity": {
    "id": 123,
    "scenario": 1,
    "batch": 206,
    "activity_type": "VACCINATION",
    "activity_type_display": "Vaccination",
    "due_date": "2024-12-15",
    "status": "COMPLETED",
    "status_display": "Completed",
    "container": 977,
    "container_name": "Tank A-01",
    "notes": "First vaccination at 50g average weight",
    "created_by": 1,
    "created_by_name": "John Doe",
    "created_at": "2024-11-28T14:30:00Z",
    "updated_at": "2024-12-15T09:00:00Z",
    "completed_at": "2024-12-15T09:00:00Z",
    "completed_by": 2,
    "completed_by_name": "Jane Smith",
    "transfer_workflow": null,
    "is_overdue": false
  }
}
```

**Error Responses**:
- `400 Bad Request`: Activity is already completed
- `404 Not Found`: Activity does not exist

---

#### Spawn Transfer Workflow

**Endpoint**: `POST /api/v1/planning/planned-activities/{id}/spawn-workflow/`

**Description**: Create a Transfer Workflow from a planned TRANSFER activity. This action links the activity to the workflow and updates the activity status to `IN_PROGRESS`.

**Path Parameters**:
- `id` (integer): Planned activity ID

**Request Body**:

```json
{
  "workflow_type": "LIFECYCLE_TRANSITION",
  "source_lifecycle_stage": 3,
  "dest_lifecycle_stage": 4
}
```

**Required Fields**:
- `source_lifecycle_stage` (integer): Source lifecycle stage ID
- `dest_lifecycle_stage` (integer): Destination lifecycle stage ID

**Optional Fields**:
- `workflow_type` (string): Workflow type (default: `LIFECYCLE_TRANSITION`)

**Response**: `201 Created`

```json
{
  "id": 456,
  "batch": 206,
  "workflow_type": "LIFECYCLE_TRANSITION",
  "source_lifecycle_stage": 3,
  "dest_lifecycle_stage": 4,
  "planned_start_date": "2024-12-15",
  "planned_activity": 123,
  "status": "DRAFT",
  "created_by": 1,
  "created_at": "2024-11-28T16:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Activity type is not `TRANSFER`, or workflow already spawned
- `404 Not Found`: Activity does not exist

---

### Activity Templates

#### List Activity Templates

**Endpoint**: `GET /api/v1/planning/activity-templates/`

**Description**: Retrieve a paginated list of activity templates.

**Query Parameters**:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `activity_type` | string | Filter by activity type | `?activity_type=VACCINATION` |
| `trigger_type` | string | Filter by trigger type | `?trigger_type=DAY_OFFSET` |
| `is_active` | boolean | Filter by active status | `?is_active=true` |
| `search` | string | Full-text search in name/description | `?search=vaccination` |
| `ordering` | string | Order results | `?ordering=name` |

**Response**: `200 OK`

```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Standard Atlantic Salmon - First Vaccination",
      "description": "First vaccination at 50g average weight",
      "activity_type": "VACCINATION",
      "activity_type_display": "Vaccination",
      "trigger_type": "DAY_OFFSET",
      "trigger_type_display": "Day Offset",
      "day_offset": 30,
      "weight_threshold_g": null,
      "target_lifecycle_stage": null,
      "notes_template": "Administer first vaccination at 50g average weight",
      "is_active": true,
      "created_at": "2024-10-01T10:00:00Z",
      "updated_at": "2024-10-01T10:00:00Z"
    }
  ]
}
```

---

#### Create Activity Template

**Endpoint**: `POST /api/v1/planning/activity-templates/`

**Description**: Create a new activity template.

**Request Body**:

```json
{
  "name": "Standard Atlantic Salmon - First Vaccination",
  "description": "First vaccination at 50g average weight",
  "activity_type": "VACCINATION",
  "trigger_type": "DAY_OFFSET",
  "day_offset": 30,
  "notes_template": "Administer first vaccination at 50g average weight",
  "is_active": true
}
```

**Required Fields**:
- `name` (string): Template name (unique)
- `activity_type` (string): Activity type
- `trigger_type` (string): Trigger type (see choices below)

**Conditional Fields** (based on `trigger_type`):
- If `trigger_type` is `DAY_OFFSET`: `day_offset` (integer) is required
- If `trigger_type` is `WEIGHT_THRESHOLD`: `weight_threshold_g` (decimal) is required
- If `trigger_type` is `STAGE_TRANSITION`: `target_lifecycle_stage` (integer) is required

**Optional Fields**:
- `description` (string): Template description
- `notes_template` (string): Template for activity notes
- `is_active` (boolean): Whether template is active (default: `true`)

**Trigger Type Choices**:
- `DAY_OFFSET`: Create activity N days after batch creation
- `WEIGHT_THRESHOLD`: Create activity when batch reaches target weight
- `STAGE_TRANSITION`: Create activity when batch transitions to target lifecycle stage

**Response**: `201 Created`

```json
{
  "id": 10,
  "name": "Standard Atlantic Salmon - First Vaccination",
  "description": "First vaccination at 50g average weight",
  "activity_type": "VACCINATION",
  "activity_type_display": "Vaccination",
  "trigger_type": "DAY_OFFSET",
  "trigger_type_display": "Day Offset",
  "day_offset": 30,
  "weight_threshold_g": null,
  "target_lifecycle_stage": null,
  "notes_template": "Administer first vaccination at 50g average weight",
  "is_active": true,
  "created_at": "2024-11-28T17:00:00Z",
  "updated_at": "2024-11-28T17:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid data (missing required fields, duplicate name)

---

#### Retrieve Activity Template

**Endpoint**: `GET /api/v1/planning/activity-templates/{id}/`

**Description**: Retrieve a single activity template by ID.

**Path Parameters**:
- `id` (integer): Template ID

**Response**: `200 OK`

```json
{
  "id": 10,
  "name": "Standard Atlantic Salmon - First Vaccination",
  "description": "First vaccination at 50g average weight",
  "activity_type": "VACCINATION",
  "activity_type_display": "Vaccination",
  "trigger_type": "DAY_OFFSET",
  "trigger_type_display": "Day Offset",
  "day_offset": 30,
  "weight_threshold_g": null,
  "target_lifecycle_stage": null,
  "notes_template": "Administer first vaccination at 50g average weight",
  "is_active": true,
  "created_at": "2024-11-28T17:00:00Z",
  "updated_at": "2024-11-28T17:00:00Z"
}
```

**Error Responses**:
- `404 Not Found`: Template does not exist

---

#### Update Activity Template

**Endpoint**: `PUT /api/v1/planning/activity-templates/{id}/`  
**Endpoint**: `PATCH /api/v1/planning/activity-templates/{id}/`

**Description**: Update an activity template.

**Path Parameters**:
- `id` (integer): Template ID

**Request Body** (PATCH example):

```json
{
  "day_offset": 35,
  "notes_template": "Updated: Administer first vaccination at 50g average weight (adjusted timing)"
}
```

**Response**: `200 OK`

```json
{
  "id": 10,
  "name": "Standard Atlantic Salmon - First Vaccination",
  "description": "First vaccination at 50g average weight",
  "activity_type": "VACCINATION",
  "activity_type_display": "Vaccination",
  "trigger_type": "DAY_OFFSET",
  "trigger_type_display": "Day Offset",
  "day_offset": 35,
  "weight_threshold_g": null,
  "target_lifecycle_stage": null,
  "notes_template": "Updated: Administer first vaccination at 50g average weight (adjusted timing)",
  "is_active": true,
  "created_at": "2024-11-28T17:00:00Z",
  "updated_at": "2024-11-28T18:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid data
- `404 Not Found`: Template does not exist

---

#### Delete Activity Template

**Endpoint**: `DELETE /api/v1/planning/activity-templates/{id}/`

**Description**: Delete an activity template.

**Path Parameters**:
- `id` (integer): Template ID

**Response**: `204 No Content`

**Error Responses**:
- `404 Not Found`: Template does not exist

---

#### Generate Activity from Template

**Endpoint**: `POST /api/v1/planning/activity-templates/{id}/generate-for-batch/`

**Description**: Generate a planned activity from a template for a specific batch and scenario.

**Path Parameters**:
- `id` (integer): Template ID

**Request Body**:

```json
{
  "scenario": 1,
  "batch": 206,
  "override_due_date": "2024-12-20"
}
```

**Required Fields**:
- `scenario` (integer): Scenario ID
- `batch` (integer): Batch ID

**Optional Fields**:
- `override_due_date` (date): Override the calculated due date (YYYY-MM-DD format)

**Response**: `201 Created`

```json
{
  "message": "Activity generated from template",
  "activity": {
    "id": 789,
    "scenario": 1,
    "batch": 206,
    "activity_type": "VACCINATION",
    "activity_type_display": "Vaccination",
    "due_date": "2024-12-20",
    "status": "PENDING",
    "status_display": "Pending",
    "container": null,
    "container_name": null,
    "notes": "Administer first vaccination at 50g average weight",
    "created_by": 1,
    "created_by_name": "John Doe",
    "created_at": "2024-11-28T19:00:00Z",
    "updated_at": "2024-11-28T19:00:00Z",
    "completed_at": null,
    "completed_by": null,
    "completed_by_name": null,
    "transfer_workflow": null,
    "is_overdue": false
  }
}
```

**Error Responses**:
- `400 Bad Request`: Invalid data (missing required fields)
- `404 Not Found`: Template, scenario, or batch does not exist

---

### Scenario Integration

#### Get Planned Activities for Scenario

**Endpoint**: `GET /api/v1/scenario/scenarios/{id}/planned-activities/`

**Description**: Retrieve all planned activities for a specific scenario. This is a custom action on the `ScenarioViewSet`.

**Path Parameters**:
- `id` (integer): Scenario ID

**Query Parameters**:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `activity_type` | string | Filter by activity type | `?activity_type=VACCINATION` |
| `status` | string | Filter by status | `?status=PENDING` |
| `batch` | integer | Filter by batch ID | `?batch=206` |

**Response**: `200 OK`

```json
[
  {
    "id": 1,
    "scenario": 1,
    "batch": 206,
    "activity_type": "VACCINATION",
    "activity_type_display": "Vaccination",
    "due_date": "2024-12-15",
    "status": "PENDING",
    "status_display": "Pending",
    "container": 977,
    "container_name": "Tank A-01",
    "notes": "First vaccination at 50g average weight",
    "created_by": 1,
    "created_by_name": "John Doe",
    "created_at": "2024-11-01T10:00:00Z",
    "updated_at": "2024-11-01T10:00:00Z",
    "completed_at": null,
    "completed_by": null,
    "completed_by_name": null,
    "transfer_workflow": null,
    "is_overdue": false
  }
]
```

**Error Responses**:
- `404 Not Found`: Scenario does not exist

---

### Batch Integration

#### Get Planned Activities for Batch

**Endpoint**: `GET /api/v1/batch/batches/{id}/planned-activities/`

**Description**: Retrieve all planned activities for a specific batch across all scenarios. This is a custom action on the `BatchViewSet`.

**Path Parameters**:
- `id` (integer): Batch ID

**Query Parameters**:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `scenario` | integer | Filter by scenario ID | `?scenario=1` |
| `status` | string | Filter by status | `?status=PENDING` |

**Response**: `200 OK`

```json
[
  {
    "id": 1,
    "scenario": 1,
    "batch": 206,
    "activity_type": "VACCINATION",
    "activity_type_display": "Vaccination",
    "due_date": "2024-12-15",
    "status": "PENDING",
    "status_display": "Pending",
    "container": 977,
    "container_name": "Tank A-01",
    "notes": "First vaccination at 50g average weight",
    "created_by": 1,
    "created_by_name": "John Doe",
    "created_at": "2024-11-01T10:00:00Z",
    "updated_at": "2024-11-01T10:00:00Z",
    "completed_at": null,
    "completed_by": null,
    "completed_by_name": null,
    "transfer_workflow": null,
    "is_overdue": false
  }
]
```

**Error Responses**:
- `404 Not Found`: Batch does not exist

---

## Error Handling

### Error Response Format

All error responses follow a consistent format:

```json
{
  "error": "Error message describing what went wrong"
}
```

For validation errors (400 Bad Request), the response includes field-specific errors:

```json
{
  "scenario": ["This field is required."],
  "due_date": ["Date has wrong format. Use YYYY-MM-DD."]
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| `200 OK` | Success | GET, PUT, PATCH requests |
| `201 Created` | Resource created | POST requests |
| `204 No Content` | Success, no content | DELETE requests |
| `400 Bad Request` | Invalid data | Validation errors |
| `401 Unauthorized` | Authentication required | Missing or invalid token |
| `403 Forbidden` | Permission denied | User lacks permission |
| `404 Not Found` | Resource not found | Invalid ID |
| `500 Internal Server Error` | Server error | Unexpected errors |

---

## Examples

### Example 1: Create a Vaccination Activity

**Request**:
```http
POST /api/v1/planning/planned-activities/
Authorization: Token abc123xyz
Content-Type: application/json

{
  "scenario": 1,
  "batch": 206,
  "activity_type": "VACCINATION",
  "due_date": "2024-12-15",
  "container": 977,
  "notes": "First vaccination at 50g average weight"
}
```

**Response**:
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": 123,
  "scenario": 1,
  "batch": 206,
  "activity_type": "VACCINATION",
  "activity_type_display": "Vaccination",
  "due_date": "2024-12-15",
  "status": "PENDING",
  "status_display": "Pending",
  "container": 977,
  "container_name": "Tank A-01",
  "notes": "First vaccination at 50g average weight",
  "created_by": 1,
  "created_by_name": "John Doe",
  "created_at": "2024-11-28T14:30:00Z",
  "updated_at": "2024-11-28T14:30:00Z",
  "completed_at": null,
  "completed_by": null,
  "completed_by_name": null,
  "transfer_workflow": null,
  "is_overdue": false
}
```

---

### Example 2: Mark Activity as Completed

**Request**:
```http
POST /api/v1/planning/planned-activities/123/mark-completed/
Authorization: Token abc123xyz
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "message": "Activity marked as completed",
  "activity": {
    "id": 123,
    "scenario": 1,
    "batch": 206,
    "activity_type": "VACCINATION",
    "activity_type_display": "Vaccination",
    "due_date": "2024-12-15",
    "status": "COMPLETED",
    "status_display": "Completed",
    "container": 977,
    "container_name": "Tank A-01",
    "notes": "First vaccination at 50g average weight",
    "created_by": 1,
    "created_by_name": "John Doe",
    "created_at": "2024-11-28T14:30:00Z",
    "updated_at": "2024-12-15T09:00:00Z",
    "completed_at": "2024-12-15T09:00:00Z",
    "completed_by": 2,
    "completed_by_name": "Jane Smith",
    "transfer_workflow": null,
    "is_overdue": false
  }
}
```

---

### Example 3: Spawn Transfer Workflow

**Request**:
```http
POST /api/v1/planning/planned-activities/456/spawn-workflow/
Authorization: Token abc123xyz
Content-Type: application/json

{
  "workflow_type": "LIFECYCLE_TRANSITION",
  "source_lifecycle_stage": 3,
  "dest_lifecycle_stage": 4
}
```

**Response**:
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": 789,
  "batch": 206,
  "workflow_type": "LIFECYCLE_TRANSITION",
  "source_lifecycle_stage": 3,
  "dest_lifecycle_stage": 4,
  "planned_start_date": "2024-12-15",
  "planned_activity": 456,
  "status": "DRAFT",
  "created_by": 1,
  "created_at": "2024-11-28T16:00:00Z"
}
```

---

### Example 4: Get All Overdue Activities

**Request**:
```http
GET /api/v1/planning/planned-activities/?overdue=true&ordering=due_date
Authorization: Token abc123xyz
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 10,
      "scenario": 1,
      "batch": 205,
      "activity_type": "CULL",
      "activity_type_display": "Culling",
      "due_date": "2024-11-20",
      "status": "PENDING",
      "status_display": "Pending",
      "container": 950,
      "container_name": "Tank B-03",
      "notes": "Cull underperforming fish",
      "created_by": 1,
      "created_by_name": "John Doe",
      "created_at": "2024-11-01T10:00:00Z",
      "updated_at": "2024-11-01T10:00:00Z",
      "completed_at": null,
      "completed_by": null,
      "completed_by_name": null,
      "transfer_workflow": null,
      "is_overdue": true
    }
  ]
}
```

---

### Example 5: Generate Activity from Template

**Request**:
```http
POST /api/v1/planning/activity-templates/1/generate-for-batch/
Authorization: Token abc123xyz
Content-Type: application/json

{
  "scenario": 1,
  "batch": 206,
  "override_due_date": "2024-12-20"
}
```

**Response**:
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "message": "Activity generated from template",
  "activity": {
    "id": 999,
    "scenario": 1,
    "batch": 206,
    "activity_type": "VACCINATION",
    "activity_type_display": "Vaccination",
    "due_date": "2024-12-20",
    "status": "PENDING",
    "status_display": "Pending",
    "container": null,
    "container_name": null,
    "notes": "Administer first vaccination at 50g average weight",
    "created_by": 1,
    "created_by_name": "John Doe",
    "created_at": "2024-11-28T19:00:00Z",
    "updated_at": "2024-11-28T19:00:00Z",
    "completed_at": null,
    "completed_by": null,
    "completed_by_name": null,
    "transfer_workflow": null,
    "is_overdue": false
  }
}
```

---

## References

1. Django REST Framework Documentation - https://www.django-rest-framework.org/
2. AquaMind API Standards - `aquamind/docs/quality_assurance/api_standards.md`
3. AquaMind Code Organization Guidelines - `aquamind/docs/quality_assurance/code_organization_guidelines.md`

---

**End of Document**
