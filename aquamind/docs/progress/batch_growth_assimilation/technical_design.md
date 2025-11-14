# Batch Growth Assimilation — Technical Design Document

**Author:** Manus AI**Date:** November 14, 2025**Version:** 1.0

---

## 1. Executive Summary

This technical design document expands on the Batch Growth Assimilation and Scenario Overlay implementation plan, providing detailed specifications for the backend computation engine, data model, API design, and integration with the existing AquaMind system. The document addresses the user's specific questions about inter-app communication and system robustness, and provides recommendations for implementing a scalable, maintainable, and fault-tolerant solution.

The key recommendation is to use an **asynchronous task queue (Celery)** for the computation engine, rather than relying solely on Django signals. This approach ensures that the system is robust against job crashes, provides durability and retry mechanisms, and allows for horizontal scaling as the number of batches and data volume grows.

---

## 2. System Architecture

The Batch Growth Assimilation feature is composed of several interconnected components that work together to calculate, store, and visualize the daily state of batches.

### 2.1. High-Level Architecture

The architecture follows a layered approach, with clear separation of concerns between data ingestion, computation, storage, and presentation.

```
┌─────────────────────────────────────────────────────────────┐
│                Frontend (React+Typescript)                  │
│  - Batch Growth Analysis Page                               │
│  - Data Series Toggles, Granularity Selector                │
│  - Interactive Chart (Recharts)                             │
│  - Variance Analysis, Container Drilldown                   │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ REST API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Django Backend (API Layer)                │
│  - Batch API (GET /api/batches/{id}/growth-analysis)        │
│  - Scenario API (GET /api/scenarios/{id}/projection)        │
│  - ActualDailyState API (GET /api/batches/{id}/daily-state) │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Computation Engine (Celery)                │
│  - recompute_actual_daily_state(assignment_id, date_range)  │
│  - TGC Growth Calculator                                    │
│  - Anchor Detection and Application                         │
│  - Fallback Mechanisms for Missing Data                     │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ Event-Driven Triggers
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Django Apps (Data Sources)                │
│  - batch.GrowthSample (new sample → trigger recompute)      │
│  - batch.BatchTransferWorkflow (transfer → trigger)         │
│  - health.Vaccination (vaccination → trigger)               │
│  - environmental.EnvironmentalReading (temp data → trigger) │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Database (PostgreSQL + TimescaleDB)            │
│  - batch_actualdailyassignmentstate (hypertable)            │
│  - batch_growthsample                                       │
│  - scenario_projectionday                                   │
│  - environmental_reading (hypertable)                       │
└─────────────────────────────────────────────────────────────┘
```

### 2.2. Data Flow

The data flow for the Batch Growth Assimilation feature follows a clear sequence from data ingestion to visualization.

**Data Ingestion:** Growth samples, environmental readings, mortality events, and feed data are entered into the system through various interfaces (mobile app, web forms, automated sensors). These are stored in their respective tables in the database.

**Event Detection:** When a relevant event occurs (e.g., a new growth sample is saved), a Django signal is fired. The signal handler enqueues a Celery task with the necessary information (assignment ID, date range to recompute).

**Computation:** A Celery worker picks up the task and executes the `recompute_actual_daily_state` function. This function retrieves the necessary data from the database, applies the TGC growth model, detects anchors, and calculates the daily state for each day in the specified range.

**Storage:** The computed daily states are inserted or updated in the `batch_actualdailyassignmentstate` hypertable. The provenance (sources) and confidence scores are stored alongside the computed values.

**API Retrieval:** When a user navigates to the Batch Growth Analysis page, the frontend makes API requests to retrieve the batch information, growth samples, scenario projection, and actual daily states. The backend queries the database and returns the data in JSON format.

**Visualization:** The frontend processes the data and renders the interactive chart, variance analysis, and container drilldown panel. The user can interact with the chart to explore the data and understand the provenance and confidence of each data point.

---

## 3. Data Model

The data model for the Batch Growth Assimilation feature extends the existing AquaMind schema with new tables and fields to support the computation and storage of daily states.

### 3.1. New Tables

**batch_actualdailyassignmentstate (TimescaleDB Hypertable)**

This is the core table that stores the computed daily state for each batch-container assignment. It is configured as a TimescaleDB hypertable partitioned on the `date` column for efficient time-series queries.

| Column | Type | Description |
| --- | --- | --- |
| `id` | BigInt (PK) | Primary key |
| `assignment_id` | BigInt (FK) | Foreign key to `batch_batchcontainerassignment` |
| `date` | Date (Partition Key) | The date for this daily state |
| `day_number` | Integer | Day number relative to batch start (1, 2, 3, ...) |
| `avg_weight_g` | Decimal(10,2) | Computed average weight in grams |
| `population` | Integer | Computed population count |
| `biomass_kg` | Decimal(10,2) | Computed biomass in kilograms |
| `anchor_type` | Varchar(50) | Type of anchor ('growth_sample', 'transfer', 'vaccination', 'manual', NULL) |
| `sources` | JSONB | Data sources for each component (temp, mortality, feed, weight) |
| `confidence_scores` | JSONB | Confidence scores (0-1) for each component |
| `created_at` | Timestamp | When this record was created |
| `updated_at` | Timestamp | When this record was last updated |

**Indexes:**

- Primary key on `(id, date)` (required for TimescaleDB hypertable)

- Index on `(assignment_id, date)` for efficient queries by assignment

- Index on `(date)` for time-based queries

**Continuous Aggregates (Future):**

- `batch_weeklystaterollup`: Weekly aggregates of the daily states for faster queries

### 3.2. Modified Tables

**batch_batchcontainerassignment**

No schema changes are required, but this table is the anchor for the daily state calculations. Each assignment has multiple daily states associated with it.

**batch_growthsample**

No schema changes are required. Growth samples serve as anchors for the daily state calculations.

**scenario_projectionday**

No schema changes are required. Scenario projections are used for comparison against the actual daily states.

---

## 4. Computation Engine

The computation engine is the heart of the Batch Growth Assimilation feature. It is responsible for calculating the daily state for each batch-container assignment based on the available data and the configured models.

### 4.1. Algorithm Overview

The computation algorithm follows the pseudocode provided in the implementation plan, with the following key steps:

1. **Identify Anchors:** Scan the date range to identify all anchor points (growth samples, transfers, vaccinations, manual entries).

1. **Segment by Anchors:** Divide the date range into segments, where each segment starts at an anchor and ends at the next anchor (or the end of the range).

1. **For Each Segment:**
  - Initialize the weight at the anchor value.
    - For each day in the segment:
      - Retrieve temperature data (measured > interpolated > profile).
      - Retrieve mortality data (actual > model).
      - Retrieve feed data (actual > none).
      - Calculate weight growth using TGC model.
      - Calculate population (subtract mortality).
      - Calculate biomass (population × weight).
      - Store sources and confidence scores.

1. **Write to Database:** Insert or update the daily states in the `batch_actualdailyassignmentstate` table.

### 4.2. TGC Growth Model

The TGC (Thermal Growth Coefficient) model is used to calculate the daily weight gain based on the current weight and temperature.

**Formula:**

```
ΔW = TGC × T^n × W^m
```

Where:

- `ΔW` = Daily weight gain (grams)

- `TGC` = Thermal Growth Coefficient (from the scenario's TGC model)

- `T` = Temperature (°C)

- `n` = Temperature exponent (typically 0.33)

- `W` = Current weight (grams)

- `m` = Weight exponent (typically 0.66)

**Implementation:**

```python
def calculate_tgc_growth(current_weight, temperature, tgc_value=0.025, n=0.33, m=0.66):
    """Calculate daily weight gain using TGC model."""
    delta_weight = tgc_value * (temperature ** n) * (current_weight ** m)
    return delta_weight
```

### 4.3. Anchor Detection

Anchors are detected by querying the relevant tables for events that occurred on the date being processed.

**Growth Sample Anchor:**

```python
sample = GrowthSample.objects.filter(
    batch_container_assignment=assignment,
    sample_date=current_date
).first()

if sample:
    anchor_type = 'growth_sample'
    anchor_weight = sample.avg_weight_g
```

**Transfer Anchor:**

```python
transfer_action = TransferAction.objects.filter(
    source_assignment=assignment,
    execution_date=current_date
).first()

if transfer_action:
    anchor_type = 'transfer'
    anchor_weight = transfer_action.avg_weight_g
```

**Vaccination Anchor:**

```python
vaccination = Vaccination.objects.filter(
    batch_container_assignment=assignment,
    vaccination_date=current_date
).first()

if vaccination and vaccination.avg_weight_g:
    anchor_type = 'vaccination'
    anchor_weight = vaccination.avg_weight_g
```

### 4.4. Fallback Mechanisms

The computation engine uses a hierarchical fallback approach for each data component to ensure robustness even when data is incomplete.

**Temperature:**

1. **Measured:** Query `EnvironmentalReading` for actual temperature measurements.

1. **Interpolated:** If no measurement exists, interpolate between the nearest measurements.

1. **Profile:** If no measurements are available, use the temperature profile from the scenario's TGC model.

**Mortality:**

1. **Actual:** Query `MortalityEvent` for actual mortality counts.

1. **Model:** If no actual data exists, use the mortality model from the scenario.

**Feed:**

1. **Actual:** Query `FeedingEvent` for actual feed amounts.

1. **None:** If no feed data exists, assume no feed was provided (confidence score = 0).

**Weight:**

1. **Measured:** Use the anchor weight if the current date is an anchor point.

1. **TGC Computed:** Use the TGC model to calculate the weight based on the previous day's weight and the current temperature.

### 4.5. Confidence Score Calculation

Confidence scores are calculated based on the data source and the time elapsed since the last anchor.

**Temperature Confidence:**

- Measured: 1.0

- Interpolated: 0.7

- Profile: 0.5

**Mortality Confidence:**

- Actual: 1.0

- Model: 0.4

**Feed Confidence:**

- Actual: 1.0

- None: 0.0

**Weight Confidence:**

- Measured (anchor): 1.0

- TGC Computed: `max(0.4, 1.0 - (days_since_anchor / 100))`

The weight confidence decreases linearly as the time since the last anchor increases, reflecting the accumulating uncertainty in the TGC-based interpolation.

---

## 5. Inter-App Communication and Robustness

The user specifically asked about the best method for communication between Django apps and how to make the system robust against job crashes. This section addresses these questions in detail.

### 5.1. Django Signals vs. Asynchronous Task Queue

**Django Signals** are a good choice for **intra-app** communication and for triggering simple, fast actions within a single process. However, for the Batch Growth Assimilation feature, which involves long-running computations and inter-app dependencies, signals have significant limitations:

| Limitation | Impact |
| --- | --- |
| **Synchronous Execution** | The recomputation task could take several seconds for large batches, blocking the user's request and degrading the user experience. |
| **Lack of Durability** | If the server crashes during signal execution, the task is lost. There is no built-in retry mechanism. |
| **No Monitoring** | It is difficult to monitor the status of signal handlers or debug failures. |
| **Tight Coupling** | Signal handlers create tight coupling between apps, making the system harder to maintain and test. |

**Asynchronous Task Queue (Celery)** addresses all of these limitations and is the recommended approach for this feature.

| Advantage | Benefit |
| --- | --- |
| **Asynchronous Execution** | Tasks are executed in the background by worker processes, so the user's request is not blocked. |
| **Durability** | Tasks are stored in a message broker (Redis or RabbitMQ). If a worker crashes, the task can be retried by another worker. |
| **Retry Mechanisms** | Celery supports automatic retries with exponential backoff, ensuring that transient failures do not result in data loss. |
| **Monitoring** | Celery provides tools (Flower, Celery Inspect) for monitoring task status, debugging failures, and tracking performance. |
| **Scalability** | You can add more Celery workers to handle a higher volume of tasks, making the system horizontally scalable. |
| **Loose Coupling** | Tasks are decoupled from the apps that trigger them, making the system more modular and testable. |

### 5.2. Recommended Architecture: Signals + Celery

The recommended architecture combines the simplicity of Django signals for event detection with the robustness of Celery for task execution.

**Step 1: Signal Handler (Lightweight)**

When a relevant event occurs (e.g., a `GrowthSample` is saved), a Django signal is fired. The signal handler's **only** responsibility is to enqueue a Celery task with the necessary information.

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.batch.models import GrowthSample
from apps.batch.tasks import recompute_actual_daily_state

@receiver(post_save, sender=GrowthSample)
def on_growth_sample_saved(sender, instance, created, **kwargs):
    """Enqueue a Celery task to recompute the daily state when a growth sample is saved."""
    if created:
        # Enqueue a task to recompute the daily state for the affected assignment
        assignment_id = instance.batch_container_assignment.assignment_id
        start_date = instance.sample_date
        end_date = None  # Recompute from sample date to the end of the batch
        
        recompute_actual_daily_state.delay(assignment_id, start_date, end_date)
```

**Step 2: Celery Task (Heavy Lifting)**

A Celery worker picks up the task and executes the `recompute_actual_daily_state` function. This function performs the actual computation and writes the results to the database.

```python
from celery import shared_task
from apps.batch.models import BatchContainerAssignment
from apps.batch.services.daily_state_calculator import DailyStateCalculator

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def recompute_actual_daily_state(self, assignment_id, start_date, end_date):
    """Recompute the actual daily state for a batch-container assignment."""
    try:
        assignment = BatchContainerAssignment.objects.get(assignment_id=assignment_id)
        calculator = DailyStateCalculator(assignment)
        calculator.compute_range(start_date, end_date)
    except Exception as exc:
        # Retry the task if it fails
        raise self.retry(exc=exc)
```

**Step 3: Monitoring and Alerting**

Use Celery monitoring tools (Flower, Celery Inspect) to track the status of tasks and set up alerts for failures. This ensures that any issues are detected and resolved quickly.

### 5.3. Handling Job Crashes

Celery provides built-in mechanisms to handle job crashes and ensure that tasks are not lost.

**Task Acknowledgment:** By default, Celery acknowledges a task only after it has been successfully executed. If a worker crashes before acknowledging the task, the task is returned to the queue and can be picked up by another worker.

**Retry Mechanisms:** Tasks can be configured to automatically retry on failure, with exponential backoff to avoid overwhelming the system. The `max_retries` and `default_retry_delay` parameters control this behavior.

**Dead Letter Queue:** Tasks that fail repeatedly can be moved to a dead letter queue for manual inspection and debugging. This prevents failed tasks from blocking the queue indefinitely.

**Idempotency:** The `recompute_actual_daily_state` function should be idempotent, meaning it can be safely executed multiple times without causing unintended side effects. This is achieved by using `INSERT ... ON CONFLICT UPDATE` (upsert) when writing to the database, so that re-running the computation simply updates the existing records.

---

## 6. API Design

The API provides endpoints for the frontend to retrieve the data needed for the Batch Growth Analysis page.

### 6.1. Batch Growth Analysis Endpoint

**GET /api/batches/{batch_id}/growth-analysis**

Returns all the data needed to render the Batch Growth Analysis page for a specific batch.

**Response:**

```json
{
  "batch": {
    "id": 1,
    "batch_number": "BTH-2023-001",
    "species": "Atlantic Salmon",
    "lifecycle_stage": "Smolt",
    "start_date": "2023-01-15",
    "status": "ACTIVE"
  },
  "scenario": {
    "scenario_id": 1,
    "name": "Baseline Projection - Faroe Islands",
    "start_date": "2023-01-15",
    "duration_days": 900,
    "initial_count": 10000,
    "initial_weight": 50
  },
  "growth_samples": [...],
  "scenario_projection": [...],
  "actual_daily_states": [...],
  "container_assignments": [...]
}
```

### 6.2. Scenario Projection Endpoint

**GET /api/scenarios/{scenario_id}/projection**

Returns the scenario projection for a specific scenario.

**Query Parameters:**

- `granularity`: "daily" or "weekly" (default: "daily")

**Response:**

```json
{
  "scenario_id": 1,
  "projection": [
    {
      "day_number": 1,
      "date": "2023-01-15",
      "avg_weight_g": 50.0,
      "population": 10000,
      "biomass_kg": 500.0
    },
    ...
  ]
}
```

### 6.3. Actual Daily State Endpoint

**GET /api/batches/{batch_id}/daily-state**

Returns the actual daily states for a specific batch.

**Query Parameters:**

- `assignment_id`: Filter by container assignment (optional)

- `start_date`: Start date for the range (optional)

- `end_date`: End date for the range (optional)

- `granularity`: "daily" or "weekly" (default: "daily")

**Response:**

```json
{
  "batch_id": 1,
  "daily_states": [
    {
      "date": "2023-01-15",
      "day_number": 1,
      "avg_weight_g": 50.0,
      "population": 10000,
      "biomass_kg": 500.0,
      "anchor_type": null,
      "sources": {
        "temp": "measured",
        "mortality": "actual",
        "feed": "actual",
        "weight": "tgc_computed"
      },
      "confidence_scores": {
        "temp": 1.0,
        "mortality": 1.0,
        "feed": 1.0,
        "weight": 0.9
      }
    },
    ...
  ]
}
```

---

## 7. Testing Strategy

A comprehensive testing strategy is essential to ensure the correctness and robustness of the Batch Growth Assimilation feature.

### 7.1. Unit Tests

**Computation Engine:** Test the TGC growth model, anchor detection, fallback mechanisms, and confidence score calculations in isolation. Use mock data to verify that the algorithm produces the expected results.

**API Endpoints:** Test the API endpoints to ensure they return the correct data in the expected format. Use Django's test client to simulate API requests.

**Signal Handlers:** Test that signal handlers correctly enqueue Celery tasks when events occur.

### 7.2. Integration Tests

**End-to-End Computation:** Test the full computation pipeline, from event detection to data storage. Verify that the daily states are correctly calculated and stored in the database.

**API Integration:** Test the integration between the frontend and backend by making real API requests and verifying that the data is correctly displayed in the UI.

### 7.3. Performance Tests

**Large Batches:** Test the computation engine with large batches (e.g., 900+ days) to ensure it completes in a reasonable time and does not consume excessive memory.

**Concurrent Tasks:** Test the Celery workers with multiple concurrent tasks to ensure they can handle the load without crashing or slowing down.

### 7.4. Regression Tests

**Data Consistency:** Verify that the computed daily states are consistent with the input data and that changes to the input data (e.g., adding a new growth sample) correctly trigger recomputation.

**Backward Compatibility:** Ensure that changes to the computation algorithm do not break existing data or API contracts.

---

## 8. Deployment and Operations

The deployment and operations strategy ensures that the Batch Growth Assimilation feature is reliable, scalable, and maintainable in production.

### 8.1. Infrastructure

**Celery Workers:** Deploy Celery workers as separate processes or containers that can be scaled horizontally. Use a process manager (e.g., Supervisor, systemd) to ensure workers are automatically restarted if they crash.

**Message Broker:** Use Redis or RabbitMQ as the message broker for Celery. Ensure the broker is highly available (e.g., using Redis Sentinel or RabbitMQ clustering).

**Database:** Use PostgreSQL with the TimescaleDB extension for the hypertable. Ensure the database is properly indexed and tuned for time-series queries.

### 8.2. Monitoring

**Celery Monitoring:** Use Flower to monitor the status of Celery tasks, track performance metrics, and debug failures.

**Application Monitoring:** Use APM tools (e.g., New Relic, Datadog) to monitor the performance of the API endpoints and identify bottlenecks.

**Database Monitoring:** Use TimescaleDB's built-in monitoring tools to track query performance and hypertable health.

### 8.3. Alerting

**Task Failures:** Set up alerts for Celery task failures, so that the operations team is notified immediately when a task fails repeatedly.

**API Errors:** Set up alerts for API errors (e.g., 500 errors) to detect issues with the backend.

**Database Performance:** Set up alerts for slow queries or high database load to prevent performance degradation.

---

## 9. Conclusion

The Batch Growth Assimilation feature is a complex, data-intensive system that requires careful design and implementation to ensure correctness, robustness, and scalability. By using an asynchronous task queue (Celery) for the computation engine, the system can handle long-running tasks without blocking user requests, provide durability and retry mechanisms, and scale horizontally as the data volume grows.

The detailed specifications provided in this document, including the data model, computation algorithm, API design, and testing strategy, provide a solid foundation for the implementation team to build a production-ready feature that meets the needs of farm managers and operators. By following the recommended architecture and best practices, the AquaMind platform can deliver a powerful, transparent, and reliable tool for batch growth analysis and scenario-based planning.

