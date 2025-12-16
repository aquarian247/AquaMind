# Live Forward Projection: Operational Forecasting Guide

**Version**: 1.0  
**Last Updated**: December 16, 2025  
**Owner**: Engineering  
**Target Repository**: `aquarian247/AquaMind/aquamind/docs/user_guides/`  

---

## Overview

Live Forward Projection is the bridge between **what has happened** (Batch Growth Assimilation) and **what will happen** (Scenario Projections). While scenarios model theoretical growth under ideal conditions, Live Forward Projection answers the critical question: *"Given where we actually are today, when will this batch really be ready for harvest or transfer?"*

This feature powers the Executive Dashboard's tiered harvest forecast, enabling leadership to make decisions based on current operational reality rather than static plans created months ago.

### Why It Matters

Atlantic salmon typically spend 700-900 days from smolt to harvest. Over this period, reality diverges from plan due to:

- **Temperature variations**: Actual water temperatures differ from profile assumptions
- **Feeding disruptions**: Weather events, equipment failures, supply issues
- **Health events**: Disease treatments that pause feeding or affect growth
- **Stocking adjustments**: Mortality events, culling decisions

The original `ScenarioProjection` becomes increasingly stale. Live Forward Projection recalculates the trajectory **nightly**, starting from the latest `ActualDailyAssignmentState` (computed by Batch Growth Assimilation), ensuring forecasts reflect ground truth.

### The Three-Tier Forecast Architecture

Live Forward Projection enables a tiered decision framework for the Executive Dashboard:

| Tier | Name | Meaning | Action Required |
|------|------|---------|-----------------|
| **1** | PLANNED | A `PlannedActivity` (HARVEST or TRANSFER) exists for this container | Execute as scheduled |
| **2** | PROJECTED | Live Forward says harvest/transfer threshold will be reached, but no plan exists yet | Create a plan when appropriate |
| **3** | NEEDS_ATTENTION | Approaching threshold within 30 days, still no plan | Urgent planning needed |

This tiering ensures executives can focus on what needs action rather than reviewing every batch.

---

## How It Works

### The Computation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        NIGHTLY CELERY TASK                              │
│                  compute_all_live_forward_projections                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  For each active BatchContainerAssignment:                              │
│                                                                         │
│  1. Fetch latest ActualDailyAssignmentState (today's truth)             │
│  2. Load pinned scenario's TGC, Mortality, TemperatureProfile models    │
│  3. Calculate temperature bias from recent sensor vs. profile delta     │
│  4. Project forward day-by-day until scenario end:                      │
│     • Future temp = TemperatureProfile[day] + bias                      │
│     • New weight = TGC formula (current weight, temp, tgc_value)        │
│     • New population = current × (1 - daily_mortality_rate)             │
│     • New biomass = weight × population / 1000                          │
│  5. Store projections in LiveForwardProjection (TimescaleDB hypertable) │
│  6. Update ContainerForecastSummary with threshold crossings            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Starting Point: Today's Truth

The engine begins with the **latest `ActualDailyAssignmentState`** for each assignment. This state is computed by the Batch Growth Assimilation engine and represents the best estimate of:

- Current average weight (grams)
- Current population count
- Current biomass (kg)
- Day number in batch lifecycle

This is the "anchor" from which all projections extend.

### Temperature Bias Policy

A critical insight: future temperatures won't match the idealized `TemperatureProfile` exactly. To correct for this, we compute a **temperature bias**:

```
bias = mean(actual_temp - profile_temp) over last N days
```

Where:
- `actual_temp` comes from sensor-derived temperatures in `ActualDailyAssignmentState`
- `profile_temp` is the `TemperatureProfile` value for that day
- `N` is configurable (default: 14 days)
- Bias is clamped to prevent unrealistic adjustments (default: ±2°C)

**Example**: If sensors show water consistently 0.8°C warmer than the profile predicted over the last 14 days, all future projections add +0.8°C to profile temperatures.

### Growth Calculation

Growth follows the **Thermal Growth Coefficient (TGC)** model, the same formula used throughout AquaMind:

```python
new_weight = (current_weight^(1/3) + (TGC / 1000) × temperature)^3
```

This biologically-grounded model captures the non-linear relationship between temperature and fish growth, with warmer water accelerating growth (up to species-specific limits).

### Mortality Model

Daily population decay uses the scenario's `MortalityModel`, which provides stage-appropriate mortality rates. The projection applies:

```python
new_population = current_population × (1 - daily_mortality_rate)
```

### Projection Horizon

Projections run from the current day until the **scenario's last day** (`scenario.duration_days`), subject to a safety cap (`LIVE_FORWARD_MAX_HORIZON_DAYS`, default: 1000 days). This ensures projections cover the full batch lifecycle.

---

## Data Models

### LiveForwardProjection (TimescaleDB Hypertable)

Stores the daily projection points for each assignment. Partitioned by `computed_date` for efficient retention and compression.

| Field | Type | Description |
|-------|------|-------------|
| `computed_date` | DATE | When this projection was computed (partition key) |
| `assignment` | FK | The BatchContainerAssignment being projected |
| `batch` | FK | Batch (denormalized for queries) |
| `container` | FK | Container (denormalized for queries) |
| `projection_date` | DATE | The future date being projected |
| `day_number` | INT | Day in batch lifecycle (1-based from start_date) |
| `projected_weight_g` | DECIMAL | Projected average weight |
| `projected_population` | INT | Projected population count |
| `projected_biomass_kg` | DECIMAL | Projected biomass |
| `temperature_used_c` | DECIMAL | Temperature used (profile + bias) |
| `tgc_value_used` | DECIMAL | TGC coefficient applied |
| `temp_profile_name` | VARCHAR | Name of baseline TemperatureProfile |
| `temp_bias_c` | DECIMAL | Bias applied to temperatures |
| `temp_bias_window_days` | INT | Days used to compute bias |

**TimescaleDB Configuration**:
- **Retention**: 90 days (older projections auto-deleted)
- **Compression**: After 7 days (reduces storage ~90%)
- **Partitioning**: By `computed_date` for efficient pruning

### ContainerForecastSummary (Regular Table)

A denormalized summary for fast dashboard queries. One row per `BatchContainerAssignment`.

| Field | Type | Description |
|-------|------|-------------|
| `assignment` | PK/FK | The assignment (one-to-one) |
| `current_weight_g` | DECIMAL | Latest actual weight |
| `current_population` | INT | Latest actual population |
| `current_biomass_kg` | DECIMAL | Latest actual biomass |
| `state_date` | DATE | Date of the actual state used |
| `state_confidence` | DECIMAL | Confidence score (0-1) from actual state |
| `projected_harvest_date` | DATE | First date weight crosses harvest threshold |
| `days_to_harvest` | INT | Days from state_date to projected harvest |
| `harvest_threshold_g` | DECIMAL | Harvest weight threshold from scenario |
| `projected_transfer_date` | DATE | First date weight crosses transfer threshold |
| `days_to_transfer` | INT | Days from state_date to projected transfer |
| `transfer_threshold_g` | DECIMAL | Transfer weight threshold from scenario |
| `original_harvest_date` | DATE | Original scenario-projected harvest date |
| `harvest_variance_days` | INT | Days behind (+) or ahead (-) of original plan |
| `has_planned_harvest` | BOOL | True if PlannedActivity(HARVEST) exists |
| `has_planned_transfer` | BOOL | True if PlannedActivity(TRANSFER) exists |
| `needs_planning_attention` | BOOL | True if approaching threshold without a plan |
| `temp_bias_c` | DECIMAL | Temperature bias applied |
| `last_computed` | DATETIME | When this summary was last updated |

---

## Executive Dashboard Integration

### Tiered Harvest Forecast

The Executive Dashboard's Strategic tab displays forecasts grouped by tier:

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 Tiered Harvest Forecast                                     │
├─────────────────────────────────────────────────────────────────┤
│  Total: 47 assignments                                          │
│  🟢 Planned: 12  |  🔵 Projected: 28  |  🟠 Needs Attention: 7  │
├─────────────────────────────────────────────────────────────────┤
│  Batch      Container   Species   Harvest Date   Days   Tier    │
│  ─────────────────────────────────────────────────────────────  │
│  B-2024-001 Tank-A1     Salmon    2025-03-15     89    PLANNED  │
│  B-2024-003 Pen-12      Salmon    2025-04-02     107   PROJECTED│
│  B-2024-007 Pen-08      Salmon    2025-01-20     24    ⚠️ NEEDS │
└─────────────────────────────────────────────────────────────────┘
```

**Tier Badges**:
- 🟢 **PLANNED** (green): Execution scheduled, on track
- 🔵 **PROJECTED** (blue): Forecast exists, plan not yet created
- 🟠 **NEEDS_ATTENTION** (amber): Within 30 days of threshold, urgent

### Growth Analysis Chart

The batch-level Growth Analysis chart now includes a **4th line** for Live Forward Projection:

| Line | Color | Style | Description |
|------|-------|-------|-------------|
| Growth Samples | Blue | Dots | Actual measured weights |
| Scenario Projection | Green | Solid | Original plan from ScenarioProjection |
| Actual Daily States | Orange | Solid | Assimilated daily weights |
| **Live Forward** | **Purple** | **Dashed** | **Projection from today forward** |

The purple dashed line visually shows how the current trajectory differs from the original green scenario line.

---

## TimescaleDB Configuration

### Why TimescaleDB?

Live Forward Projection generates significant time-series data:
- 50-60 active batches × ~300 projection days = 15,000-18,000 rows per nightly run
- 90 days retention × 18,000 rows = 1.6M+ rows in steady state

TimescaleDB provides:
- **Automatic partitioning**: Data chunked by `computed_date` for efficient queries
- **Compression**: ~10x storage reduction for older data
- **Retention policies**: Automatic deletion of data older than 90 days
- **Query performance**: Optimized for time-range queries common in forecasting

### Local Development with Docker

For local development with full TimescaleDB support:

```bash
# Start TimescaleDB and Redis in Docker
cd /path/to/AquaMind
docker compose up -d timescale-db redis

# Configure environment
export DB_HOST=localhost
export DB_NAME=aquamind_db
export DB_USER=postgres
export DB_PASSWORD=adminpass1234
export DB_PORT=5432
export TIMESCALE_ENABLED=true

# Run migrations (creates hypertables)
python manage.py migrate

# Verify hypertables exist
docker compose exec timescale-db psql -U postgres -d aquamind_db -c \
  "SELECT hypertable_name FROM timescaledb_information.hypertables;"
```

### CI Strategy

CI tests run with SQLite for speed. TimescaleDB operations are gracefully skipped via the `migrations_helpers.py` utilities:

```python
# From apps/environmental/migrations_helpers.py
def is_timescaledb_available():
    if connection.vendor != 'postgresql':
        return False  # SQLite in CI
    # ... additional checks
```

This ensures:
- **CI**: Fast SQLite tests, no TimescaleDB dependency
- **UAT/Staging**: Full TimescaleDB via `docker-compose.test.yml`
- **Production**: Full TimescaleDB with retention/compression

---

## API Reference

### Get Live Forward Projection for Assignment

**GET** `/api/v1/batch/assignments/{id}/live-forward-projection/`

Returns the complete projection series for a specific assignment.

**Response**:
```json
{
  "assignment_id": 123,
  "batch_id": 45,
  "container_id": 67,
  "start_date": "2025-01-15",
  "end_date": "2025-09-30",
  "provenance": {
    "computed_date": "2025-01-15",
    "temp_profile_name": "Scotland Coastal Summer",
    "temp_bias_c": 0.42,
    "temp_bias_window_days": 14,
    "tgc_value_used": 2.15
  },
  "projections": [
    {
      "date": "2025-01-16",
      "day_number": 181,
      "projected_weight_g": 2450.50,
      "projected_population": 48200,
      "projected_biomass_kg": 118114.10,
      "temperature_used_c": 8.42
    },
    // ... more days
  ]
}
```

### Get Tiered Harvest Forecast

**GET** `/api/v1/batch/forecast/tiered-harvest/`

Returns aggregated forecast data for the Executive Dashboard.

**Query Parameters**:
- `geography_id` (optional): Filter by geography
- `species_id` (optional): Filter by species
- `from_date` (optional): Filter projections from this date
- `to_date` (optional): Filter projections until this date

**Response**:
```json
{
  "summary": {
    "total_assignments": 47,
    "planned_count": 12,
    "projected_count": 28,
    "needs_attention_count": 7,
    "total_projected_biomass_tonnes": 4250.5
  },
  "forecasts": [
    {
      "assignment_id": 123,
      "batch_number": "B-2024-001",
      "container_name": "Pen-12",
      "species": "Atlantic Salmon",
      "facility": "Loch Ness Site A",
      "current_weight_g": 2100.00,
      "projected_harvest_date": "2025-03-15",
      "days_to_harvest": 89,
      "projected_biomass_kg": 118114.10,
      "tier": "PLANNED",
      "has_planned_harvest": true,
      "has_planned_transfer": false,
      "needs_planning_attention": false,
      "temp_bias_c": 0.42,
      "state_confidence": 0.85
    },
    // ... more forecasts
  ],
  "by_quarter": {
    "Q1-2025": { "count": 8, "biomass_tonnes": 950.2 },
    "Q2-2025": { "count": 15, "biomass_tonnes": 1820.5 },
    "Q3-2025": { "count": 24, "biomass_tonnes": 1479.8 }
  }
}
```

---

## Configuration

### Django Settings

All Live Forward Projection settings are configurable via environment variables:

| Setting | Default | Description |
|---------|---------|-------------|
| `LIVE_FORWARD_PROJECTION_RETENTION_DAYS` | 90 | Days to retain projection data |
| `LIVE_FORWARD_PROJECTION_COMPRESS_AFTER_DAYS` | 7 | Days before compression kicks in |
| `LIVE_FORWARD_TEMP_BIAS_WINDOW_DAYS` | 14 | Days to average for bias calculation |
| `LIVE_FORWARD_TEMP_BIAS_CLAMP_MIN_C` | -2.00 | Minimum bias (prevents wild corrections) |
| `LIVE_FORWARD_TEMP_BIAS_CLAMP_MAX_C` | 2.00 | Maximum bias |
| `LIVE_FORWARD_MAX_HORIZON_DAYS` | 1000 | Safety cap on projection horizon |
| `LIVE_FORWARD_ATTENTION_THRESHOLD_DAYS` | 30 | Days to threshold for "needs attention" |

### Celery Beat Schedule

The nightly projection task is configured in `settings.py`:

```python
CELERY_BEAT_SCHEDULE = {
    'compute-live-forward-projections-daily': {
        'task': 'apps.batch.tasks.compute_all_live_forward_projections',
        'schedule': crontab(hour=3, minute=0),  # 03:00 UTC daily
        'args': (),
        'options': {'queue': 'long_running'},
    },
}
```

This runs after the daily assimilation tasks complete, ensuring projections start from fresh actuals.

---

## Troubleshooting

### No Projections Appearing

1. **Check for ActualDailyAssignmentState**: Projections require at least one actual state.
   ```sql
   SELECT COUNT(*) FROM batch_actualdailyassignmentstate 
   WHERE assignment_id = <id>;
   ```

2. **Check for pinned scenario**: The batch needs a scenario with TGC, Mortality, and TemperatureProfile.
   ```sql
   SELECT pr.id, s.name FROM scenario_projectionrun pr
   JOIN scenario_scenario s ON pr.scenario_id = s.id
   WHERE pr.batch_id = <batch_id> AND pr.is_pinned = true;
   ```

3. **Check Celery logs**: Look for errors in the nightly task.

### Temperature Bias Seems Wrong

1. **Check sensor data availability**: Bias requires sensor-derived temperatures in recent states.
   ```sql
   SELECT date, temp_c, sources->>'temp' as temp_source
   FROM batch_actualdailyassignmentstate
   WHERE assignment_id = <id>
   ORDER BY date DESC LIMIT 14;
   ```

2. **Check bias window**: If fewer days have sensor data, bias calculation uses available data only.

### Projections Don't Match Scenario

This is expected! Live Forward Projection intentionally diverges from `ScenarioProjection` because:
- It starts from **actual** current state, not theoretical Day 1
- It applies temperature bias from real sensor data
- It reflects mortality and feeding events that occurred

The variance is informative—it shows how reality has shifted from the original plan.

---

## Integration with Other Features

### Relationship to Batch Growth Assimilation

Live Forward Projection **depends on** Batch Growth Assimilation:
- Assimilation computes `ActualDailyAssignmentState` (past → present)
- Live Forward projects from that state (present → future)

The nightly schedule runs assimilation first (02:00 UTC), then projections (03:00 UTC).

### Relationship to Production Planner

Live Forward Projection **informs** the Production Planner:
- Projected dates suggest when to create `PlannedActivity`
- Tier 3 (NEEDS_ATTENTION) flags batches requiring urgent planning
- Variance tracking compares planned dates to projected dates

### Relationship to Transfer Workflows

When a `PlannedActivity` of type TRANSFER is created:
- The assignment moves to Tier 1 (PLANNED)
- Live Forward continues projecting the destination assignment
- Post-transfer, assimilation anchors the new state, and projections update

---

## Glossary

| Term | Definition |
|------|------------|
| **Actual Daily State** | Computed daily state from Batch Growth Assimilation, representing truth |
| **Anchor** | A measurement or event that provides ground-truth data for assimilation |
| **Hypertable** | TimescaleDB's partitioned table optimized for time-series data |
| **Pinned Scenario** | The scenario designated as baseline for a batch's projections |
| **Temperature Bias** | Correction applied to profile temperatures based on sensor observations |
| **TGC** | Thermal Growth Coefficient—the biological growth model used |
| **Tier** | Classification of forecast urgency (PLANNED, PROJECTED, NEEDS_ATTENTION) |

---

## References

- **PRD Section 3.2**: Operational Planning requirements
- **Planning & Workflows Primer**: `docs/user_guides/planning_and_workflows_primer.md`
- **Batch Growth Assimilation Plan**: `docs/progress/batch_growth_assimilation/batch-growth-assimilation-plan.md`
- **Executive Forecast Dashboard Plan**: `docs/progress/executive_forecast_dashboard/live_forward_projection_plan.md`
- **TimescaleDB Testing Strategy**: `docs/quality_assurance/timescaledb_testing_strategy.md`

---

**End of Document**

