# AquaMind API Documentation

## Overview

This document provides comprehensive documentation for the AquaMind API. It covers all endpoints, request/response formats, and authentication requirements.

**Note**: Advanced audit analytics endpoints (previously in Core app) have been removed. Basic audit trail functionality is available through django-simple-history integration in the Django admin interface.

## Mock Generation Information

```json
{
  "api_version": "v1",
  "base_url": "http://api.example.com/api/v1",
  "content_type": "application/json",
  "authentication": "JWT Bearer Token",
  "pagination": {
    "style": "offset-based",
    "parameters": ["page", "page_size"],
    "response_format": {
      "count": "integer",
      "next": "url or null",
      "previous": "url or null",
      "results": "array of objects"
    }
  },
  "error_format": {
    "error": "string",
    "detail": "string"
  },
  "date_format": "ISO-8601 (YYYY-MM-DDThh:mm:ssZ)"
}
```

### Mock Generation Instructions

1. **Base URL**: Use `http://api.example.com/api/v1` as the base URL for all mock endpoints
2. **Authentication**: All endpoints require a valid JWT token in the Authorization header
3. **Content Type**: All requests and responses use JSON format
4. **Status Codes**:
   - 200: Successful GET, PUT, PATCH operations
   - 201: Successful POST operations
   - 204: Successful DELETE operations
   - 400: Bad Request (validation errors)
   - 401: Unauthorized (missing or invalid token)
   - 403: Forbidden (insufficient permissions)
   - 404: Not Found (resource doesn't exist)
   - 500: Internal Server Error
5. **Validation**: Implement validation according to field types and constraints
6. **Relationships**: Maintain referential integrity between related resources
7. **Pagination**: Implement offset-based pagination for list endpoints
8. **Filtering**: Support filtering by query parameters matching field names

## Authentication

All API endpoints require authentication using JWT tokens. To authenticate:

1. Obtain a token by sending a POST request to `/api/token/`
2. Include the token in the Authorization header: `Authorization: Bearer <token>`

## API Endpoints

### Environmental API

#### Environmental Parameters

**Endpoint:** `/api/v1/environmental/parameters/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `name`: String - Name of the environmental parameter
- `unit`: String - Unit of measurement (e.g., "°C", "pH", "mg/L")
- `description`: String - Detailed description of the parameter
- `min_value`: Float - Minimum acceptable value
- `max_value`: Float - Maximum acceptable value
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

**Example Request (POST):**
```json
{
  "name": "Dissolved Oxygen",
  "unit": "mg/L",
  "description": "Amount of oxygen dissolved in water",
  "min_value": 5.0,
  "max_value": 15.0
}
```

**Example Response:**
```json
{
  "id": 1,
  "name": "Dissolved Oxygen",
  "unit": "mg/L",
  "description": "Amount of oxygen dissolved in water",
  "min_value": 5.0,
  "max_value": 15.0,
  "created_at": "2025-06-04T10:15:30Z",
  "updated_at": "2025-06-04T10:15:30Z"
}
```

#### Environmental Readings

**Endpoint:** `/api/v1/environmental/readings/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `parameter`: Integer - Foreign key to Environmental Parameter
- `reading_time`: DateTime - Time when the reading was taken
- `value`: Float - The measured value
- `sensor`: Integer - Foreign key to Sensor (optional)
- `container`: Integer - Foreign key to Container
- `notes`: String - Additional notes (optional)
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

**Example Request (POST):**
```json
{
  "parameter": 1,
  "reading_time": "2025-06-04T12:30:00Z",
  "value": 7.8,
  "sensor": 2,
  "container": 3,
  "notes": "Regular monitoring reading"
}
```

**Example Response:**
```json
{
  "id": 42,
  "parameter": 1,
  "reading_time": "2025-06-04T12:30:00Z",
  "value": 7.8,
  "sensor": 2,
  "container": 3,
  "notes": "Regular monitoring reading",
  "created_at": "2025-06-04T12:31:05Z",
  "updated_at": "2025-06-04T12:31:05Z",
  "parameter_name": "Dissolved Oxygen",
  "parameter_unit": "mg/L",
  "container_name": "Tank A3"
}
```

**Example GET Response (List):**
```json
{
  "count": 120,
  "next": "http://api.example.com/api/v1/environmental/readings/?page=2",
  "previous": null,
  "results": [
    {
      "id": 42,
      "parameter": 1,
      "reading_time": "2025-06-04T12:30:00Z",
      "value": 7.8,
      "sensor": 2,
      "container": 3,
      "notes": "Regular monitoring reading",
      "created_at": "2025-06-04T12:31:05Z",
      "updated_at": "2025-06-04T12:31:05Z",
      "parameter_name": "Dissolved Oxygen",
      "parameter_unit": "mg/L",
      "container_name": "Tank A3"
    },
    // Additional readings...
  ]
}
```

#### Weather Data

**Endpoint:** `/api/v1/environmental/weather/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `timestamp`: DateTime - Time when the weather data was recorded
- `temperature`: Float - Temperature in °C
- `humidity`: Float - Relative humidity percentage
- `pressure`: Float - Atmospheric pressure in hPa
- `wind_speed`: Float - Wind speed in m/s
- `wind_direction`: String - Wind direction
- `precipitation`: Float - Precipitation in mm
- `cloud_cover`: Float - Cloud cover percentage
- `weather_station`: Integer - Foreign key to Weather Station
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

#### Stage Transition Environmental Data

**Endpoint:** `/api/v1/environmental/stage-transitions/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `batch`: Integer - Foreign key to Batch
- `from_stage`: Integer - Foreign key to Stage (source)
- `to_stage`: Integer - Foreign key to Stage (destination)
- `transition_date`: Date - Date of stage transition
- `environmental_parameters`: Object - Environmental parameters during transition
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

### Health API

#### Lab Samples

**Endpoint:** `/api/v1/health/lab-samples/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `batch`: Integer - Foreign key to Batch
- `sample_date`: DateTime - Date and time when sample was taken
- `sample_type`: String - Type of sample
- `lab_id`: String - Laboratory identifier
- `results`: Object - Sample results
- `notes`: String - Additional notes
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

#### Health Assessments

**Endpoint:** `/api/v1/health/assessments/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `batch`: Integer - Foreign key to Batch
- `assessment_date`: DateTime - Date and time of assessment
- `assessor`: String - Person who performed the assessment
- `health_score`: Integer - Overall health score (1-10)
- `observations`: String - Detailed observations
- `recommendations`: String - Recommended actions
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

### Infrastructure API

#### Geographies

**Endpoint:** `/api/v1/infrastructure/geographies/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `name`: String - Name of the geography
- `description`: String - Description of the geography
- `latitude`: Float - Latitude coordinate
- `longitude`: Float - Longitude coordinate
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

#### Areas

**Endpoint:** `/api/v1/infrastructure/areas/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `name`: String - Name of the area
- `description`: String - Description of the area
- `geography`: Integer - Foreign key to Geography
- `latitude`: Float - Latitude coordinate
- `longitude`: Float - Longitude coordinate
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

#### Halls

**Endpoint:** `/api/v1/infrastructure/halls/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `name`: String - Name of the hall
- `description`: String - Description of the hall
- `area`: Integer - Foreign key to Area
- `total_volume_m3`: Float - Total volume in cubic meters
- `length_m`: Float - Length in meters
- `width_m`: Float - Width in meters
- `height_m`: Float - Height in meters
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

#### Container Types

**Endpoint:** `/api/v1/infrastructure/container-types/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `name`: String - Name of the container type
- `description`: String - Description of the container type
- `volume_m3`: Float - Volume in cubic meters
- `length_m`: Float - Length in meters
- `width_m`: Float - Width in meters
- `height_m`: Float - Height in meters
- `shape`: String - Shape of the container
- `material`: String - Material of the container
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

#### Containers

**Endpoint:** `/api/v1/infrastructure/containers/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `name`: String - Name of the container
- `container_type`: Integer - Foreign key to Container Type
- `hall`: Integer - Foreign key to Hall (optional)
- `area`: Integer - Foreign key to Area (optional)
- `is_active`: Boolean - Whether the container is active
- `installation_date`: Date - Date when the container was installed
- `decommission_date`: Date - Date when the container was decommissioned (optional)
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

### Batch API

#### Batches

**Endpoint:** `/api/v1/batch/batches/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `name`: String - Name of the batch
- `species`: Integer - Foreign key to Species
- `start_date`: Date - Start date of the batch
- `end_date`: Date - End date of the batch (optional)
- `initial_count`: Integer - Initial count of organisms
- `initial_biomass_kg`: Float - Initial biomass in kg
- `current_count`: Integer - Current count of organisms
- `current_biomass_kg`: Float - Current biomass in kg
- `container`: Integer - Foreign key to Container
- `stage`: Integer - Foreign key to Stage
- `status`: String - Status of the batch
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

#### Species

**Endpoint:** `/api/v1/batch/species/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `name`: String - Scientific name of the species
- `common_name`: String - Common name of the species
- `description`: String - Description of the species
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

#### Stages

**Endpoint:** `/api/v1/batch/stages/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `name`: String - Name of the stage
- `description`: String - Description of the stage
- `species`: Integer - Foreign key to Species
- `order`: Integer - Order of the stage in lifecycle
- `typical_duration_days`: Integer - Typical duration in days
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

### Inventory API

#### Feed Types

**Endpoint:** `/api/v1/inventory/feed-types/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `name`: String - Name of the feed type
- `description`: String - Description of the feed type
- `manufacturer`: String - Manufacturer of the feed
- `protein_percentage`: Float - Protein percentage
- `fat_percentage`: Float - Fat percentage
- `carbohydrate_percentage`: Float - Carbohydrate percentage
- `fiber_percentage`: Float - Fiber percentage
- `moisture_percentage`: Float - Moisture percentage
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

#### Feed Stock

**Endpoint:** `/api/v1/inventory/feed-stock/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `feed_type`: Integer - Foreign key to Feed Type
- `quantity_kg`: Float - Quantity in kg
- `location`: String - Storage location
- `expiry_date`: Date - Expiry date
- `batch_number`: String - Batch number
- `updated_at`: DateTime (read-only) - Last update timestamp

#### Feeding Events

**Endpoint:** `/api/v1/inventory/feeding-events/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `batch`: Integer - Foreign key to Batch
- `batch_assignment`: Integer - Foreign key to Batch Container Assignment (optional)
- `container`: Integer - Foreign key to Container
- `feed`: Integer - Foreign key to Feed
- `feed_stock`: Integer - Foreign key to Feed Stock (optional)
- `feeding_date`: Date - Date of feeding
- `feeding_time`: Time - Time of feeding
- `amount_kg`: Decimal(10,4) - Amount of feed in kg (supports 0.0001 precision)
- `batch_biomass_kg`: Decimal(10,2) - Batch biomass at feeding time (auto-populated)
- `feeding_percentage`: Decimal(8,6) - Feed as percentage of biomass (auto-calculated)
- `feed_cost`: Decimal(10,2) - Cost of feed consumed (auto-calculated via FIFO)
- `method`: String - Feeding method (MANUAL, AUTOMATIC, BROADCAST)
- `notes`: String - Additional notes
- `recorded_by`: Integer - Foreign key to User
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

**Auto-Calculation Features:**
- **Batch Biomass**: Automatically populated from the latest active batch assignment when not provided
- **Feeding Percentage**: Automatically calculated as `(amount_kg / batch_biomass_kg) * 100`
- **Feed Cost**: Automatically calculated using FIFO inventory service when feed_stock is provided
- **High Precision**: Supports feeding amounts as small as 0.0001 kg for realistic salmon feeding scenarios

**Example Request (POST):**
```json
{
  "batch": 1,
  "feed": 2,
  "amount_kg": "0.0033",
  "feeding_date": "2025-06-10",
  "feeding_time": "08:00:00",
  "method": "MANUAL"
}
```

**Example Response:**
```json
{
  "id": 123,
  "batch": 1,
  "batch_name": "BATCH001",
  "container": 5,
  "feed": 2,
  "feed_name": "Premium Salmon Feed",
  "amount_kg": "0.0033",
  "batch_biomass_kg": "1000.00",
  "feeding_percentage": "0.000330",
  "feed_cost": "0.0165",
  "method": "MANUAL",
  "feeding_date": "2025-06-10",
  "feeding_time": "08:00:00",
  "created_at": "2025-06-10T08:05:00Z",
  "updated_at": "2025-06-10T08:05:00Z"
}
```

#### Feed Container Stock (FIFO Tracking)

**Endpoint:** `/api/v1/inventory/feed-container-stocks/`

**Methods:** GET, POST, PUT, PATCH, DELETE

**Fields:**
- `id`: Integer (read-only) - Unique identifier
- `feed_container`: Integer - Foreign key to Feed Container
- `feed_purchase`: Integer - Foreign key to Feed Purchase
- `quantity_kg`: Decimal(10,3) - Quantity in kg
- `cost_per_kg`: Decimal(10,2) - Cost per kg from purchase
- `purchase_date`: Date - Date of purchase
- `created_at`: DateTime (read-only) - Creation timestamp
- `updated_at`: DateTime (read-only) - Last update timestamp

**FIFO Features:**
- Tracks feed inventory using First-In-First-Out methodology
- Automatically calculates feed costs based on oldest stock first
- Supports mixed feed batches with different costs in same container

## Error Handling

All API endpoints follow standard HTTP status codes:

- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error

Error responses include a JSON object with an "error" key containing a description of the error.

## Filtering and Pagination

Most endpoints support filtering and pagination:

- Filtering: Add query parameters matching field names (e.g., `/api/v1/batch/batches/?status=active`)
- Pagination: Use `page` and `page_size` parameters (e.g., `/api/v1/batch/batches/?page=2&page_size=10`)

## Versioning

The API is versioned in the URL path. The current version is v1.
