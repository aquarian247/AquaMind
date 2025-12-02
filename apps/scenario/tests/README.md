# Scenario Planning Test Suite

## Overview
This directory contains comprehensive tests for the Scenario Planning module,
covering unit tests, API tests, and integration tests.

## Test Structure

### 1. Unit Tests (`models/` and `services/`)

#### test_calculations.py
- **TGCCalculatorTests**: Tests for Thermal Growth Coefficient calculations
- **FCRCalculatorTests**: Tests for Feed Conversion Ratio calculations  
- **MortalityCalculatorTests**: Tests for mortality rate calculations
- **EdgeCaseTests**: Tests for edge cases and error conditions

#### test_model_validation.py
- **TGCModelValidationTests**: Validates TGC model field constraints
- **FCRModelValidationTests**: Validates FCR model and stage constraints
- **MortalityModelValidationTests**: Validates mortality model constraints
- **ScenarioValidationTests**: Validates scenario configuration rules
- **BiologicalConstraintsValidationTests**: Validates biological constraint rules
- **ScenarioModelChangeValidationTests**: Validates mid-scenario model changes

### 2. API Tests (`api/`)

#### test_endpoints.py
- **TGCModelAPITests**: Tests TGC model CRUD and validation
- **FCRModelAPITests**: Tests FCR model endpoints and templates
- **MortalityModelAPITests**: Tests mortality model validation
- **ScenarioAPITests**: Tests scenario creation, duplication, comparison
- **BiologicalConstraintsAPITests**: Tests constraint management
- **DataEntryAPITests**: Tests CSV upload and data validation
- **ProjectionChartAPITests**: Tests chart data formatting
- **TemperatureProfileAPITests**: Tests temperature data management
- **SummaryStatsAPITests**: Tests aggregation endpoints

#### test_integration.py
- **ScenarioWorkflowTests**: End-to-end scenario workflows
  - Comparing multiple scenarios
  - Exporting projection data
  - Chart data generation
  - Temperature profile uploads
  - Biological constraint enforcement

## Running Tests

### Run all scenario tests:
```bash
python manage.py test apps.scenario.tests
```

### Run specific test module:
```bash
python manage.py test apps.scenario.tests.models.test_calculations
python manage.py test apps.scenario.tests.api.test_endpoints
python manage.py test apps.scenario.tests.api.test_integration
```

### Run with verbose output:
```bash
python manage.py test apps.scenario.tests -v 2
```

## Test Coverage Goals

- Unit test coverage: 80%+ for calculation engines
- API test coverage: 100% of endpoints
- Integration test coverage: All major workflows 