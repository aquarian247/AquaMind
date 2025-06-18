# Scenario Planning User Guide

## Introduction

The Scenario Planning and Simulation module is a powerful tool for projecting growth outcomes in aquaculture operations. It allows you to model different scenarios, test various biological parameters, and analyze potential outcomes before making operational decisions.

This guide will walk you through the key features and best practices for using the Scenario Planning module effectively.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Understanding the Components](#understanding-the-components)
3. [Creating Your First Scenario](#creating-your-first-scenario)
4. [Running Projections](#running-projections)
5. [Analyzing Results](#analyzing-results)
6. [Advanced Features](#advanced-features)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

Before using the Scenario Planning module, ensure you have:

1. **Authentication**: Valid user credentials with access to the Scenario Planning module
2. **Basic Data**: At least one temperature profile for your location
3. **Understanding**: Basic knowledge of aquaculture growth parameters (TGC, FCR, mortality rates)

### Key Concepts

- **TGC (Thermal Growth Coefficient)**: A model that predicts fish growth based on temperature
- **FCR (Feed Conversion Ratio)**: The ratio of feed consumed to weight gained
- **Mortality Model**: Predicts population decline over time
- **Scenario**: A combination of all models with initial conditions
- **Projection**: The calculated daily outcomes based on your scenario

## Understanding the Components

### Temperature Profiles

Temperature profiles are the foundation of growth calculations. They contain daily temperature readings for your farming location.

**Creating a Temperature Profile:**

1. **Manual Entry**: Add individual temperature readings
2. **CSV Upload**: Import a year's worth of temperature data
3. **Date Ranges**: Define temperature ranges for seasons

**Example CSV Format:**
```csv
date,temperature
2024-01-01,8.5
2024-01-02,8.7
2024-01-03,8.6
```

### TGC Models

TGC models calculate daily growth based on:
- Water temperature
- Current fish weight
- Species-specific growth coefficients

**Key Parameters:**
- **TGC Value**: Typically between 2.0-3.0 for salmon
- **Temperature Exponent (n)**: Usually 1.0
- **Weight Exponent (m)**: Usually 0.333 (cube root)

### FCR Models

FCR models determine feed requirements at different lifecycle stages:
- **Fry**: FCR 0.7-0.9
- **Parr**: FCR 0.8-1.0
- **Smolt**: FCR 1.0-1.2
- **Post-Smolt**: FCR 1.1-1.3
- **Harvest**: FCR 1.2-1.5

### Mortality Models

Mortality models predict population decline:
- **Daily Rate**: Typical 0.03-0.05% per day
- **Weekly Rate**: Typical 0.2-0.35% per week
- **Stage-Specific**: Different rates for different lifecycle stages

## Creating Your First Scenario

### Step 1: Set Up Temperature Data

```http
POST /api/v1/scenario/temperature-profiles/
{
  "name": "My Farm 2024",
  "readings": [...]
}
```

Or upload a CSV file with historical temperature data.

### Step 2: Create a TGC Model

```http
POST /api/v1/scenario/tgc-models/
{
  "name": "Spring Release TGC",
  "location": "My Farm",
  "release_period": "April",
  "tgc_value": 2.5,
  "exponent_n": 1.0,
  "exponent_m": 0.333,
  "profile": 1
}
```

### Step 3: Create an FCR Model

```http
POST /api/v1/scenario/fcr-models/
{
  "name": "Standard FCR",
  "stages": [
    {
      "stage": 1,  // Fry
      "fcr_value": 0.8,
      "duration_days": 90
    },
    {
      "stage": 2,  // Parr
      "fcr_value": 1.0,
      "duration_days": 120
    }
  ]
}
```

### Step 4: Create a Mortality Model

```http
POST /api/v1/scenario/mortality-models/
{
  "name": "Low Mortality",
  "frequency": "daily",
  "rate": 0.03
}
```

### Step 5: Create the Scenario

```http
POST /api/v1/scenario/scenarios/
{
  "name": "Spring 2024 Baseline",
  "start_date": "2024-04-01",
  "duration_days": 600,
  "initial_count": 100000,
  "initial_weight": 50.0,
  "genotype": "SalmoBreed",
  "supplier": "AquaGen",
  "tgc_model": 1,
  "fcr_model": 1,
  "mortality_model": 1
}
```

## Running Projections

Once your scenario is created, run the projection:

```http
POST /api/v1/scenario/scenarios/{scenario_id}/run_projection/
```

The projection engine will:
1. Calculate daily growth using TGC model
2. Determine lifecycle stage transitions
3. Apply stage-specific FCR values
4. Calculate daily mortality
5. Track biomass and feed consumption

**Projection Results Include:**
- Daily weight progression
- Population changes
- Biomass accumulation
- Feed requirements
- Temperature data used

## Analyzing Results

### Viewing Projections

Get daily projection data:
```http
GET /api/v1/scenario/scenarios/{scenario_id}/projections/
```

### Chart Visualization

Get data formatted for charts:
```http
GET /api/v1/scenario/scenarios/{scenario_id}/chart_data/?metrics=weight,biomass
```

### Key Metrics to Monitor

1. **Growth Rate**: Daily weight gain percentage
2. **SGR (Specific Growth Rate)**: Logarithmic growth rate
3. **Biomass Density**: kg/m³ in containers
4. **Feed Conversion**: Actual FCR vs. planned
5. **Survival Rate**: Percentage of initial population

### Exporting Results

Export projections as CSV:
```http
GET /api/v1/scenario/scenarios/{scenario_id}/export_projections/
```

## Advanced Features

### Scenario Comparison

Compare multiple scenarios side-by-side:

```http
POST /api/v1/scenario/scenarios/compare/
{
  "scenario_ids": [1, 2, 3],
  "comparison_metrics": ["final_weight", "final_biomass", "fcr_overall"]
}
```

### Sensitivity Analysis

Test how changes in parameters affect outcomes:

```http
POST /api/v1/scenario/scenarios/{scenario_id}/sensitivity_analysis/
{
  "parameter": "tgc",
  "variations": [-10, -5, 0, 5, 10]
}
```

### Model Changes Mid-Scenario

Account for operational changes:

```json
{
  "model_changes": [
    {
      "change_day": 180,
      "new_fcr_model": 2  // Switch to summer FCR model
    }
  ]
}
```

### Biological Constraints

Use predefined constraints to validate scenarios:

```json
{
  "biological_constraints": 1  // "Bakkafrost Standard"
}
```

This ensures:
- Initial weight matches lifecycle stage
- Temperature ranges are appropriate
- Growth targets are realistic

## Best Practices

### 1. Temperature Data Quality

- Use actual historical data when possible
- Fill gaps with interpolation, not assumptions
- Update regularly with current readings

### 2. Conservative Modeling

- Start with conservative TGC values (2.2-2.5)
- Use proven FCR values from operations
- Include realistic mortality rates

### 3. Scenario Planning Strategy

- **Baseline**: Current operational parameters
- **Optimistic**: Best-case with improvements
- **Conservative**: Account for challenges
- **Sensitivity**: Test parameter variations

### 4. Regular Validation

- Compare projections to actual results
- Adjust models based on real data
- Document assumptions and changes

### 5. Lifecycle Considerations

- Different parameters for each stage
- Account for transfer timing
- Consider seasonal variations

## Troubleshooting

### Common Issues

**1. Projection Fails to Run**
- Check temperature profile has data for entire duration
- Ensure all models are properly configured
- Verify initial weight matches a lifecycle stage

**2. Unrealistic Results**
- Review TGC value (typically 2.0-3.0)
- Check FCR values by stage
- Verify temperature data is reasonable

**3. Missing Temperature Data**
- System uses last known temperature
- Add warnings to projection results
- Fill gaps before running projections

### Validation Errors

**Name Already Exists**
- Scenario names must be unique per user
- Add version numbers or dates to names

**Duration Too Long**
- Maximum duration is 1200 days
- Split into multiple scenarios if needed

**Invalid Initial Weight**
- Minimum weight is 0.1g (egg stage)
- Must match biological constraints if set

### Performance Tips

- Run projections during off-peak hours
- Use aggregation for long-term views
- Export large datasets for local analysis

## Appendix

### Typical Parameter Ranges

**TGC Values by Location:**
- Norway: 2.4-2.8
- Scotland: 2.2-2.6
- Faroe Islands: 2.3-2.7
- Chile: 2.5-3.0

**FCR by Stage:**
- Freshwater: 0.7-1.0
- Sea transfer: 1.0-1.2
- Grow-out: 1.1-1.4
- Pre-harvest: 1.2-1.5

**Mortality Rates:**
- Freshwater: 0.02-0.04% daily
- Post-transfer: 0.05-0.10% daily
- Grow-out: 0.03-0.05% daily

### Glossary

- **Biomass**: Total weight of fish population
- **Degree Days**: Cumulative temperature over time
- **FCR**: Feed Conversion Ratio (feed/gain)
- **SGR**: Specific Growth Rate (% per day)
- **TGC**: Thermal Growth Coefficient
- **Smoltification**: Transition to seawater readiness

### Support

For additional support:
- API Documentation: `/docs/api/scenario_planning_api.md`
- Technical Support: support@aquamind.com
- Training Resources: Available on request 