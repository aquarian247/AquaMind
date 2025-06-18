# Scenario Planning API Documentation

## Overview

The Scenario Planning and Simulation module provides comprehensive APIs for creating and managing growth projections for aquaculture operations. This module enables users to model different scenarios, run projections, and analyze outcomes based on configurable biological parameters.

**Base URL**: `/api/v1/scenario/`

**Authentication**: All endpoints require authentication via JWT token in the Authorization header:
```
Authorization: Bearer <token>
```

## Table of Contents

1. [Temperature Profiles](#temperature-profiles)
2. [TGC Models](#tgc-models)
3. [FCR Models](#fcr-models)
4. [Mortality Models](#mortality-models)
5. [Scenarios](#scenarios)
6. [Biological Constraints](#biological-constraints)
7. [Data Entry](#data-entry)
8. [Error Responses](#error-responses)

---

## Temperature Profiles

Temperature profiles store temperature data patterns used in TGC (Thermal Growth Coefficient) calculations.

### List Temperature Profiles

```http
GET /api/v1/scenario/temperature-profiles/
```

**Query Parameters:**
- `search` (string): Search by profile name
- `ordering` (string): Order by fields (name, created_at, -created_at)
- `page` (integer): Page number for pagination
- `page_size` (integer): Number of results per page (default: 20)

**Response:**
```json
{
  "count": 15,
  "next": "http://api.example.com/api/v1/scenario/temperature-profiles/?page=2",
  "previous": null,
  "results": [
    {
      "profile_id": 1,
      "name": "Faroe Islands Winter",
      "statistics": {
        "min": 4.5,
        "max": 12.8,
        "avg": 8.2,
        "std_dev": 2.1,
        "count": 365
      },
      "date_range": {
        "start": "2024-01-01",
        "end": "2024-12-31"
      },
      "reading_count": 365,
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

### Create Temperature Profile

```http
POST /api/v1/scenario/temperature-profiles/
```

**Request Body:**
```json
{
  "name": "Scotland Summer Profile",
  "readings": [
    {
      "reading_date": "2024-06-01",
      "temperature": 14.5
    },
    {
      "reading_date": "2024-06-02",
      "temperature": 14.8
    }
  ]
}
```

**Response:** 201 Created
```json
{
  "profile_id": 2,
  "name": "Scotland Summer Profile",
  "statistics": {
    "min": 14.5,
    "max": 14.8,
    "avg": 14.65,
    "std_dev": 0.15,
    "count": 2
  },
  "date_range": {
    "start": "2024-06-01",
    "end": "2024-06-02"
  },
  "reading_count": 2,
  "created_at": "2024-01-20T14:30:00Z",
  "updated_at": "2024-01-20T14:30:00Z"
}
```

### Upload CSV Temperature Data

```http
POST /api/v1/scenario/temperature-profiles/upload_csv/
Content-Type: multipart/form-data
```

**Request Body:**
- `file`: CSV file with columns: date, temperature
- `profile_name`: Name for the temperature profile

**CSV Format Example:**
```csv
date,temperature
2024-01-01,8.5
2024-01-02,8.7
2024-01-03,8.6
```

**Response:** 201 Created
```json
{
  "profile_id": 3,
  "name": "Uploaded Profile",
  "message": "Successfully imported 90 temperature readings",
  "statistics": {
    "min": 7.2,
    "max": 15.3,
    "avg": 10.8,
    "std_dev": 2.3,
    "count": 90
  }
}
```

### Bulk Date Ranges

Create temperature profiles using date ranges with constant or interpolated values.

```http
POST /api/v1/scenario/temperature-profiles/bulk_date_ranges/
```

**Request Body:**
```json
{
  "profile_name": "Seasonal Profile",
  "ranges": [
    {
      "start_date": "2024-01-01",
      "end_date": "2024-03-31",
      "value": 6.5
    },
    {
      "start_date": "2024-04-01",
      "end_date": "2024-06-30",
      "value": 10.5
    }
  ],
  "merge_adjacent": true,
  "fill_gaps": true,
  "interpolation_method": "linear"
}
```

**Response:** 201 Created

### Get Temperature Profile Statistics

```http
GET /api/v1/scenario/temperature-profiles/{profile_id}/statistics/
```

**Response:**
```json
{
  "profile_id": 1,
  "name": "Faroe Islands Winter",
  "statistics": {
    "min": 4.5,
    "max": 12.8,
    "avg": 8.2,
    "std_dev": 2.1,
    "median": 8.1,
    "count": 365,
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  },
  "monthly_averages": [
    {"month": "January", "avg_temp": 5.2},
    {"month": "February", "avg_temp": 5.5},
    {"month": "March", "avg_temp": 6.8}
  ]
}
```

---

## TGC Models

TGC (Thermal Growth Coefficient) models calculate daily growth based on temperature and fish weight.

### List TGC Models

```http
GET /api/v1/scenario/tgc-models/
```

**Query Parameters:**
- `location` (string): Filter by location
- `release_period` (string): Filter by release period
- `search` (string): Search by name or location
- `ordering` (string): Order by fields (name, location, created_at)

**Response:**
```json
{
  "count": 8,
  "results": [
    {
      "model_id": 1,
      "name": "Scotland April TGC",
      "location": "Scotland Site 1",
      "release_period": "April",
      "tgc_value": 2.5,
      "exponent_n": 1.0,
      "exponent_m": 0.333,
      "profile": {
        "profile_id": 1,
        "name": "Scotland Spring Profile"
      },
      "stage_overrides": [
        {
          "lifecycle_stage": "fry",
          "tgc_value": 2.8,
          "temperature_exponent": 1.1,
          "weight_exponent": 0.35
        }
      ],
      "created_at": "2024-01-10T09:00:00Z",
      "updated_at": "2024-01-10T09:00:00Z"
    }
  ]
}
```

### Create TGC Model

```http
POST /api/v1/scenario/tgc-models/
```

**Request Body:**
```json
{
  "name": "Norway Summer TGC",
  "location": "Norway Fjord Site",
  "release_period": "June",
  "tgc_value": 2.8,
  "exponent_n": 1.0,
  "exponent_m": 0.333,
  "profile": 1,
  "stage_overrides": [
    {
      "lifecycle_stage": "smolt",
      "tgc_value": 3.0,
      "temperature_exponent": 1.0,
      "weight_exponent": 0.333
    }
  ]
}
```

**Validation Rules:**
- `tgc_value` must be between 0 and 10
- `exponent_n` and `exponent_m` must be between 0 and 2
- Temperature profile must exist

**Response:** 201 Created

### Get TGC Model Templates

```http
GET /api/v1/scenario/tgc-models/templates/
```

**Response:**
```json
[
  {
    "name": "Conservative Growth",
    "location": "General",
    "release_period": "Spring",
    "tgc_value": 2.2,
    "exponent_n": 1.0,
    "exponent_m": 0.333,
    "description": "Conservative growth model for standard conditions"
  },
  {
    "name": "Optimized Growth",
    "location": "General",
    "release_period": "Spring",
    "tgc_value": 2.8,
    "exponent_n": 1.0,
    "exponent_m": 0.333,
    "description": "Optimized growth model for ideal conditions"
  }
]
```

### Duplicate TGC Model

```http
POST /api/v1/scenario/tgc-models/{model_id}/duplicate/
```

**Request Body:**
```json
{
  "new_name": "Norway Summer TGC - Copy"
}
```

**Response:** 201 Created

---

## FCR Models

FCR (Feed Conversion Ratio) models define feed efficiency per lifecycle stage.

### List FCR Models

```http
GET /api/v1/scenario/fcr-models/
```

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "model_id": 1,
      "name": "Standard FCR Model",
      "stages": [
        {
          "stage": {
            "id": 1,
            "name": "fry",
            "description": "Fry stage"
          },
          "fcr_value": 0.8,
          "duration_days": 90,
          "overrides": [
            {
              "min_weight_g": 0.1,
              "max_weight_g": 5.0,
              "fcr_value": 0.7
            }
          ]
        }
      ],
      "stage_coverage": {
        "total_stages": 7,
        "configured_stages": 5,
        "coverage_percent": 71.4,
        "missing_stages": ["egg", "harvest"]
      },
      "created_at": "2024-01-05T10:00:00Z",
      "updated_at": "2024-01-05T10:00:00Z"
    }
  ]
}
```

### Create FCR Model

```http
POST /api/v1/scenario/fcr-models/
```

**Request Body:**
```json
{
  "name": "Optimized FCR Model",
  "stages": [
    {
      "stage": 1,
      "fcr_value": 0.8,
      "duration_days": 90,
      "overrides": [
        {
          "min_weight_g": 0.1,
          "max_weight_g": 2.0,
          "fcr_value": 0.7
        }
      ]
    }
  ]
}
```

**Validation Rules:**
- FCR values must be between 0.5 and 3.0
- Stage durations must be positive
- Weight ranges in overrides must not overlap

**Response:** 201 Created

### Get FCR Model Stage Summary

```http
GET /api/v1/scenario/fcr-models/{model_id}/stage_summary/
```

**Response:**
```json
{
  "model_id": 1,
  "model_name": "Standard FCR Model",
  "total_stages": 5,
  "total_duration": 600,
  "average_fcr": 1.15,
  "stages": [
    {
      "stage_name": "fry",
      "fcr_value": 0.8,
      "duration_days": 90,
      "weight_range": {
        "min": 0.1,
        "max": 50.0
      },
      "override_count": 2
    }
  ]
}
```

---

## Mortality Models

Mortality models define population decline rates over time.

### List Mortality Models

```http
GET /api/v1/scenario/mortality-models/
```

**Query Parameters:**
- `frequency` (string): Filter by frequency (daily, weekly)

**Response:**
```json
{
  "count": 4,
  "results": [
    {
      "model_id": 1,
      "name": "Standard Mortality",
      "frequency": "daily",
      "rate": 0.05,
      "effective_annual_rate": 16.8,
      "stage_overrides": [
        {
          "lifecycle_stage": "fry",
          "daily_rate_percent": 0.08,
          "weekly_rate_percent": 0.56
        }
      ],
      "created_at": "2024-01-03T08:00:00Z",
      "updated_at": "2024-01-03T08:00:00Z"
    }
  ]
}
```

### Create Mortality Model

```http
POST /api/v1/scenario/mortality-models/
```

**Request Body:**
```json
{
  "name": "Low Mortality Model",
  "frequency": "daily",
  "rate": 0.03,
  "stage_overrides": [
    {
      "lifecycle_stage": "smolt",
      "daily_rate_percent": 0.02
    }
  ]
}
```

**Validation Rules:**
- Rate must be between 0 and 100
- Daily rates above 1% trigger a warning
- Weekly rates above 7% trigger a warning

**Response:** 201 Created

---

## Scenarios

Scenarios combine all models with initial conditions to run projections.

### List Scenarios

```http
GET /api/v1/scenario/scenarios/
```

**Query Parameters:**
- `all` (boolean): Show all scenarios (not just user's own)
- `start_date` (date): Filter by start date
- `tgc_model__location` (string): Filter by TGC model location
- `search` (string): Search by name, genotype, or supplier
- `ordering` (string): Order by fields (name, start_date, duration_days, created_at)

**Response:**
```json
{
  "count": 12,
  "results": [
    {
      "scenario_id": 1,
      "name": "Spring 2024 Baseline",
      "start_date": "2024-04-01",
      "duration_days": 600,
      "initial_count": 100000,
      "initial_weight": 50.0,
      "initial_stage": {
        "stage": "parr",
        "name": "Parr",
        "weight_range": {
          "min": 5.0,
          "max": 50.0
        }
      },
      "genotype": "SalmoBreed",
      "supplier": "AquaGen",
      "tgc_model": {
        "model_id": 1,
        "name": "Scotland April TGC"
      },
      "fcr_model": {
        "model_id": 1,
        "name": "Standard FCR"
      },
      "mortality_model": {
        "model_id": 1,
        "name": "Standard Mortality"
      },
      "batch": null,
      "biological_constraints": {
        "id": 1,
        "name": "Bakkafrost Standard"
      },
      "model_changes": [
        {
          "change_id": 1,
          "change_day": 180,
          "new_tgc_model": 2,
          "new_fcr_model": null,
          "new_mortality_model": null
        }
      ],
      "created_by": {
        "id": 1,
        "username": "john.doe"
      },
      "created_at": "2024-01-20T10:00:00Z",
      "updated_at": "2024-01-20T10:00:00Z"
    }
  ]
}
```

### Create Scenario

```http
POST /api/v1/scenario/scenarios/
```

**Request Body:**
```json
{
  "name": "Summer 2024 Optimistic",
  "start_date": "2024-06-01",
  "duration_days": 540,
  "initial_count": 120000,
  "initial_weight": 45.0,
  "genotype": "StofnFiskur",
  "supplier": "Benchmark Genetics",
  "tgc_model": 2,
  "fcr_model": 1,
  "mortality_model": 2,
  "biological_constraints": 1,
  "model_changes": [
    {
      "change_day": 150,
      "new_fcr_model": 2
    }
  ]
}
```

**Validation Rules:**
- Name must be unique per user
- Duration must be between 1 and 1200 days
- Initial count must be positive
- Initial weight must be at least 0.1g
- Initial weight must match a lifecycle stage if biological constraints are set

**Response:** 201 Created

### Duplicate Scenario

```http
POST /api/v1/scenario/scenarios/{scenario_id}/duplicate/
```

**Request Body:**
```json
{
  "new_name": "Summer 2024 Optimistic - Copy",
  "include_projections": false,
  "include_model_changes": true
}
```

**Response:** 201 Created

### Create Scenario from Batch

```http
POST /api/v1/scenario/scenarios/from_batch/
```

**Request Body:**
```json
{
  "batch_id": 123,
  "scenario_name": "Batch 123 Projection",
  "duration_days": 600,
  "use_current_models": true
}
```

**Response:** 201 Created

### Run Projection

```http
POST /api/v1/scenario/scenarios/{scenario_id}/run_projection/
```

**Response:**
```json
{
  "success": true,
  "summary": {
    "total_days": 600,
    "final_weight": 5234.5,
    "final_population": 94532,
    "final_biomass": 494823.5,
    "total_feed_consumed": 587234.2,
    "overall_fcr": 1.19,
    "survival_rate": 94.5,
    "stages_reached": ["parr", "smolt", "post_smolt", "harvest"]
  },
  "warnings": [
    "Temperature data missing for days 580-600, using last known value"
  ],
  "message": "Projection completed successfully. 600 days calculated."
}
```

### Get Scenario Projections

```http
GET /api/v1/scenario/scenarios/{scenario_id}/projections/
```

**Query Parameters:**
- `start_date` (date): Filter projections from this date
- `end_date` (date): Filter projections until this date
- `aggregation` (string): Aggregation level (daily, weekly, monthly)

**Response:**
```json
{
  "count": 600,
  "results": [
    {
      "projection_id": 1,
      "projection_date": "2024-04-01",
      "day_number": 0,
      "average_weight": 50.0,
      "population": 100000.0,
      "biomass": 5000.0,
      "daily_feed": 60.0,
      "cumulative_feed": 60.0,
      "temperature": 8.5,
      "current_stage": {
        "id": 3,
        "name": "parr"
      }
    }
  ]
}
```

### Get Chart Data

```http
GET /api/v1/scenario/scenarios/{scenario_id}/chart_data/
```

**Query Parameters:**
- `metrics` (array): Metrics to include (weight, population, biomass, feed, temperature)
- `chart_type` (string): Chart type (line, area, bar)
- `aggregation` (string): Data aggregation (daily, weekly, monthly)

**Response:**
```json
{
  "labels": ["2024-04-01", "2024-04-02", "2024-04-03"],
  "datasets": [
    {
      "label": "Average Weight (g)",
      "data": [50.0, 50.8, 51.6],
      "borderColor": "rgb(75, 192, 192)",
      "backgroundColor": "rgba(75, 192, 192, 0.2)",
      "yAxisID": "y-weight"
    },
    {
      "label": "Biomass (kg)",
      "data": [5000.0, 5075.2, 5151.3],
      "borderColor": "rgb(255, 99, 132)",
      "backgroundColor": "rgba(255, 99, 132, 0.2)",
      "yAxisID": "y-biomass"
    }
  ],
  "options": {
    "responsive": true,
    "interaction": {
      "mode": "index",
      "intersect": false
    },
    "scales": {
      "y-weight": {
        "type": "linear",
        "display": true,
        "position": "left",
        "title": {
          "display": true,
          "text": "Weight (g)"
        }
      },
      "y-biomass": {
        "type": "linear",
        "display": true,
        "position": "right",
        "title": {
          "display": true,
          "text": "Biomass (kg)"
        }
      }
    }
  }
}
```

### Export Projections

```http
GET /api/v1/scenario/scenarios/{scenario_id}/export_projections/
```

**Response:** CSV file download
```csv
Day,Date,Weight (g),Population,Biomass (kg),Daily Feed (kg),Cumulative Feed (kg),Temperature (°C),Stage,Growth Rate (%),FCR Actual
0,2024-04-01,50.00,100000,5000.00,60.00,60.00,8.5,parr,0.00,0.00
1,2024-04-02,50.80,99995,5079.75,61.20,121.20,8.7,parr,1.60,1.20
```

### Compare Scenarios

```http
POST /api/v1/scenario/scenarios/compare/
```

**Request Body:**
```json
{
  "scenario_ids": [1, 2, 3],
  "comparison_metrics": ["final_weight", "final_biomass", "fcr_overall", "survival_rate"]
}
```

**Response:**
```json
{
  "scenarios": [
    {
      "scenario_id": 1,
      "name": "Spring 2024 Baseline",
      "duration_days": 600,
      "metrics": {
        "final_weight": 5234.5,
        "final_biomass": 494823.5,
        "fcr_overall": 1.19,
        "survival_rate": 94.5
      }
    }
  ],
  "metrics": {
    "final_weight": {
      "min": 4987.3,
      "max": 5456.2,
      "avg": 5234.5,
      "best_scenario": 3
    },
    "final_biomass": {
      "min": 456234.1,
      "max": 512345.8,
      "avg": 487654.2,
      "best_scenario": 3
    }
  },
  "rankings": {
    "final_weight": [3, 1, 2],
    "final_biomass": [3, 2, 1],
    "fcr_overall": [2, 3, 1],
    "survival_rate": [1, 3, 2]
  }
}
```

### Sensitivity Analysis

```http
POST /api/v1/scenario/scenarios/{scenario_id}/sensitivity_analysis/
```

**Request Body:**
```json
{
  "parameter": "tgc",
  "variations": [-10, -5, 0, 5, 10]
}
```

**Response:**
```json
{
  "parameter": "tgc",
  "base_value": 2.5,
  "results": [
    {
      "variation": -10,
      "value": 2.25,
      "final_weight": 4711.1,
      "final_biomass": 445234.5,
      "percent_change_weight": -10.0,
      "percent_change_biomass": -10.0
    }
  ],
  "summary": {
    "most_sensitive_metric": "final_weight",
    "elasticity": 1.0,
    "breakeven_variation": null
  }
}
```

### Get Summary Statistics

```http
GET /api/v1/scenario/scenarios/summary_stats/
```

**Response:**
```json
{
  "total_scenarios": 15,
  "scenarios_with_projections": 12,
  "average_duration": 587.3,
  "location_distribution": [
    {
      "tgc_model__location": "Scotland Site 1",
      "count": 8
    },
    {
      "tgc_model__location": "Norway Fjord",
      "count": 5
    }
  ],
  "recent_scenarios": [
    {
      "scenario_id": 15,
      "name": "Latest Test",
      "created_at": "2024-01-25T14:00:00Z"
    }
  ]
}
```

---

## Biological Constraints

Biological constraints define acceptable ranges for lifecycle stages.

### List Biological Constraints

```http
GET /api/v1/scenario/biological-constraints/
```

**Query Parameters:**
- `is_active` (boolean): Filter by active status
- `search` (string): Search by name or description

**Response:**
```json
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "name": "Bakkafrost Standard",
      "description": "Standard biological constraints based on Bakkafrost operations",
      "is_active": true,
      "stage_constraints": [
        {
          "lifecycle_stage": "fry",
          "weight_range": {
            "min": 0.1,
            "max": 5.0
          },
          "temperature_range": {
            "min": 6.0,
            "max": 16.0
          },
          "typical_duration_days": 90,
          "freshwater_limit": 5.0
        }
      ],
      "created_at": "2024-01-01T08:00:00Z",
      "updated_at": "2024-01-01T08:00:00Z",
      "created_by": {
        "id": 1,
        "username": "admin"
      }
    }
  ]
}
```

### Get Active Constraints

```http
GET /api/v1/scenario/biological-constraints/active/
```

**Response:** List of active constraint sets only

---

## Data Entry

Data entry endpoints provide various methods for importing data.

### Validate CSV

```http
POST /api/v1/scenario/data-entry/validate_csv/
Content-Type: multipart/form-data
```

**Request Body:**
- `file`: CSV file to validate
- `data_type`: Type of data (temperature, fcr, mortality)
- `profile_name` or `model_name`: Name for the imported data

**Response:**
```json
{
  "success": true,
  "preview_data": [
    {
      "row": 1,
      "date": "2024-01-01",
      "temperature": 8.5,
      "status": "valid"
    }
  ],
  "errors": [],
  "warnings": [
    "Row 45: Temperature 25.5°C is unusually high for salmon farming"
  ],
  "summary": {
    "total_rows": 90,
    "valid_rows": 89,
    "error_rows": 0,
    "warning_rows": 1
  }
}
```

### Download CSV Template

```http
GET /api/v1/scenario/data-entry/csv_template/?data_type=temperature
```

**Query Parameters:**
- `data_type` (required): Type of template (temperature, fcr, mortality)
- `include_sample_data` (boolean): Include example data rows

**Response:** CSV file download

---

## Error Responses

All endpoints follow a consistent error response format:

### Validation Error (400)
```json
{
  "field_name": [
    "Error message for this field"
  ],
  "non_field_errors": [
    "General error message"
  ]
}
```

### Authentication Error (401)
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### Permission Error (403)
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### Not Found Error (404)
```json
{
  "detail": "Not found."
}
```

### Server Error (500)
```json
{
  "detail": "Internal server error. Please try again later."
}
```

---

## Rate Limiting

API endpoints are rate-limited to ensure fair usage:

- Authenticated users: 1000 requests per hour
- Projection runs: 10 per hour per user
- Bulk imports: 20 per hour per user

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets

---

## Pagination

List endpoints support pagination with the following structure:

```json
{
  "count": 150,
  "next": "http://api.example.com/api/v1/scenario/scenarios/?page=2",
  "previous": null,
  "results": [...]
}
```

Default page size is 20. Maximum page size is 100.

---

## Webhooks

The Scenario Planning module supports webhooks for the following events:

- `scenario.created`: New scenario created
- `scenario.projection_completed`: Projection calculation completed
- `scenario.projection_failed`: Projection calculation failed

Webhook payload example:
```json
{
  "event": "scenario.projection_completed",
  "timestamp": "2024-01-25T15:30:00Z",
  "data": {
    "scenario_id": 15,
    "scenario_name": "Spring 2024 Baseline",
    "duration_days": 600,
    "projections_created": 600,
    "summary": {
      "final_weight": 5234.5,
      "final_biomass": 494823.5
    }
  }
}
``` 