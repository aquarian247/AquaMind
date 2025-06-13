# FIFO Feed Inventory API Updates

## Overview
This document summarizes the new API endpoints added for the FIFO (First-In-First-Out) Feed Inventory System and FCR (Feed Conversion Ratio) calculations.

## New API Endpoints

### 1. Feed Purchases (FIFO Tracking)
**Base URL:** `/api/v1/inventory/feed-purchases/`

- `GET /` - List all feed purchases
- `POST /` - Create new feed purchase batch
- `GET /{id}/` - Get specific purchase details
- `PUT /{id}/` - Update purchase
- `PATCH /{id}/` - Partial update purchase
- `DELETE /{id}/` - Delete purchase

**Key Fields:**
- `batch_number` - Unique identifier for the purchase batch
- `cost_per_kg` - Cost per kilogram for FIFO calculations
- `purchase_date` - Used for FIFO ordering
- `expiry_date` - Feed expiration tracking

### 2. Feed Container Stock (FIFO Management)
**Base URL:** `/api/v1/inventory/feed-container-stock/`

#### Standard CRUD Operations:
- `GET /` - List all container stock entries
- `POST /` - Create new stock entry
- `GET /{id}/` - Get specific stock entry
- `PUT /{id}/` - Update stock entry
- `PATCH /{id}/` - Partial update stock entry
- `DELETE /{id}/` - Delete stock entry

#### FIFO-Specific Actions:
- `POST /add_to_container/` - Add feed to container using FIFO service
- `GET /fifo_order/?container_id={id}` - Get stock in FIFO order

**Key Features:**
- Tracks feed batches by purchase date for FIFO ordering
- Links feed containers to specific purchase batches
- Maintains quantity tracking for each batch in each container

### 3. Enhanced Feeding Events
**Base URL:** `/api/v1/inventory/feeding-events/`

**New Field:**
- `feed_cost` - Automatically calculated using FIFO methodology

**FIFO Cost Calculation:**
- When creating a feeding event, the system automatically:
  1. Identifies the oldest feed batches in the container (FIFO order)
  2. Calculates the cost based on the original purchase prices
  3. Updates the `feed_cost` field with the calculated amount
  4. Deducts the consumed quantity from container stock

### 4. Batch Feeding Summaries (FCR Enhanced)
**Base URL:** `/api/v1/inventory/batch-feeding-summaries/`

**New Fields:**
- `total_feed_consumed_kg` - Total feed consumed in the period
- `total_biomass_gain_kg` - Total biomass gain in the period
- `fcr` - Calculated Feed Conversion Ratio

**Custom Action:**
- `POST /generate/` - Generate summary with FCR calculation

## Updated Data Models

### FeedingEvent Model Updates
```json
{
  "batch": 1,
  "container": 1,
  "feed": 1,
  "feeding_date": "2025-06-10",
  "feeding_time": "08:00:00",
  "amount_kg": 25.5,
  "batch_biomass_kg": 1200.0,
  "feed_cost": 63.75,  // NEW: Auto-calculated via FIFO
  "method": "MANUAL",
  "notes": "Morning feeding",
  "recorded_by": 1
}
```

### FeedContainerStock Model (NEW)
```json
{
  "id": 1,
  "feed_container": 1,
  "feed_container_name": "Silo A1",
  "feed_purchase": 1,
  "feed_purchase_batch": "AF-2025-001",
  "feed_type": "Premium Salmon Feed",
  "quantity_kg": 250.0,
  "entry_date": "2025-06-10T14:30:00Z",
  "cost_per_kg": 2.50,
  "total_value": 625.00,
  "created_at": "2025-06-10T14:30:00Z",
  "updated_at": "2025-06-10T14:30:00Z"
}
```

### BatchFeedingSummary Model Updates
```json
{
  "id": 1,
  "batch": 1,
  "period_start": "2025-06-01",
  "period_end": "2025-06-30",
  "total_feed_kg": 750.0,
  "total_feed_consumed_kg": 750.0,  // NEW
  "total_biomass_gain_kg": 500.0,   // NEW
  "fcr": 1.50,                      // NEW: Calculated FCR
  "average_feeding_percentage": 2.1,
  "feeding_events_count": 60,
  "created_at": "2025-06-30T23:59:59Z"
}
```

## FIFO Workflow Example

### 1. Create Feed Purchase
```http
POST /api/v1/inventory/feed-purchases/
{
  "feed": 1,
  "supplier": "AquaFeed Suppliers Ltd",
  "batch_number": "AF-2025-001",
  "quantity_kg": 1000.0,
  "cost_per_kg": 2.50,
  "purchase_date": "2025-06-01",
  "expiry_date": "2026-06-01"
}
```

### 2. Add Feed to Container
```http
POST /api/v1/inventory/feed-container-stock/add_to_container/
{
  "feed_container": 1,
  "feed_purchase": 1,
  "quantity_kg": 500.0,
  "entry_date": "2025-06-10T10:00:00Z"
}
```

### 3. Record Feeding Event (Auto-calculates cost)
```http
POST /api/v1/inventory/feeding-events/
{
  "batch": 1,
  "container": 1,
  "feed": 1,
  "feeding_date": "2025-06-10",
  "feeding_time": "08:00:00",
  "amount_kg": 25.5,
  "batch_biomass_kg": 1200.0,
  "method": "MANUAL"
}
```

### 4. Check FIFO Order
```http
GET /api/v1/inventory/feed-container-stock/fifo_order/?container_id=1
```

## Frontend Integration Notes

### For Replit Development:
1. **Authentication**: Use the JWT token from `/api/token/` for all requests
2. **FIFO Tracking**: Use the new container stock endpoints for real-time inventory
3. **Cost Calculations**: Feed costs are automatically calculated - no manual input needed
4. **FCR Monitoring**: Use batch feeding summaries for performance metrics

### Key Variables in Postman Collection:
- `{{base_url}}` - http://localhost:8000 (update for your environment)
- `{{token}}` - JWT authentication token
- `{{purchase_id}}` - Sample purchase ID for testing
- `{{stock_id}}` - Sample stock entry ID
- `{{feeding_event_id}}` - Sample feeding event ID
- `{{summary_id}}` - Sample summary ID

## Migration Status
- ✅ Database schema updated with new models
- ✅ FIFO service implementation complete
- ✅ FCR calculation service complete
- ✅ API endpoints implemented and tested
- ✅ Postman collection updated
- 🔄 Frontend integration (in progress in Replit)

## Next Steps for Frontend
1. Import the updated Postman collection
2. Test authentication flow
3. Implement feed purchase creation
4. Build FIFO container stock management UI
5. Create feeding event forms with auto-cost calculation
6. Develop FCR monitoring dashboards 