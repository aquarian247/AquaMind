# Scenario Planning Test Suite

## Overview
This directory contains comprehensive tests for the Scenario Planning module, covering unit tests, API tests, integration tests, and performance tests.

## Test Structure

### 1. Unit Tests

#### test_calculations.py
- **TGCCalculatorTests**: Tests for Thermal Growth Coefficient calculations
- **FCRCalculatorTests**: Tests for Feed Conversion Ratio calculations  
- **MortalityCalculatorTests**: Tests for mortality rate calculations
- **EdgeCaseTests**: Tests for edge cases and error conditions

**Status**: Created but needs fixes for:
- Calculator instantiation (requires model instances instead of no-arg constructor)
- LifeCycleStage model usage (requires Species instance)

#### test_model_validation.py
- **TGCModelValidationTests**: Validates TGC model field constraints
- **FCRModelValidationTests**: Validates FCR model and stage constraints
- **MortalityModelValidationTests**: Validates mortality model constraints
- **ScenarioValidationTests**: Validates scenario configuration rules
- **BiologicalConstraintsValidationTests**: Validates biological constraint rules
- **ScenarioModelChangeValidationTests**: Validates mid-scenario model changes

**Status**: Partially created, needs completion

### 2. API Tests

#### test_api_endpoints.py
- **TGCModelAPITests**: Tests TGC model CRUD and validation
- **FCRModelAPITests**: Tests FCR model endpoints and templates
- **MortalityModelAPITests**: Tests mortality model validation
- **ScenarioAPITests**: Tests scenario creation, duplication, comparison
- **BiologicalConstraintsAPITests**: Tests constraint management
- **DataEntryAPITests**: Tests CSV upload and data validation
- **ProjectionChartAPITests**: Tests chart data formatting
- **TemperatureProfileAPITests**: Tests temperature data management
- **SummaryStatsAPITests**: Tests aggregation endpoints

**Status**: Created but needs import fixes (Location -> Geography)

### 3. Integration Tests

#### test_integration.py
- **ScenarioWorkflowTests**: End-to-end scenario workflows
  - Creating scenarios from scratch
  - Creating scenarios from existing batches
  - Running projections
  - Comparing multiple scenarios
  - Sensitivity analysis
  - Exporting data
  - Chart data generation
  - Model changes mid-scenario
  - Temperature profile uploads
  - Biological constraint enforcement
  
- **PerformanceTests**: Performance testing
  - 900+ day projections
  - Large population scenarios
  - Concurrent scenario processing

**Status**: Created but needs infrastructure setup fixes

## Known Issues to Fix

### 1. Calculator Instantiation
The calculation services require model instances:
```python
# Current (incorrect):
calculator = TGCCalculator()

# Should be:
calculator = TGCCalculator(tgc_model)
```

### 2. LifeCycleStage Model
The actual model requires a Species:
```python
# Current (incorrect):
stage = LifeCycleStage.objects.create(
    name='fry',
    display_name='Fry',
    typical_min_weight_g=1.0,
    typical_max_weight_g=5.0
)

# Should be:
species = Species.objects.create(
    name='Atlantic Salmon',
    scientific_name='Salmo salar'
)
stage = LifeCycleStage.objects.create(
    name='fry',
    species=species,
    order=3,
    expected_weight_min_g=1.0,
    expected_weight_max_g=5.0
)
```

### 3. Import Issues
- Change `Location` to `Geography` in test_api_endpoints.py
- Update field names for StageConstraint (constraint_set, lifecycle_stage)

### 4. Test Data Setup
Need to create proper test fixtures that include:
- Species instances for LifeCycleStage
- Complete infrastructure hierarchy (Geography -> Area -> Site -> Facility -> Container)
- Proper biological constraint sets

## Running Tests

### Run all scenario tests:
```bash
python manage.py test apps.scenario.tests
```

### Run specific test module:
```bash
python manage.py test apps.scenario.tests.test_calculations
python manage.py test apps.scenario.tests.test_api_endpoints
python manage.py test apps.scenario.tests.test_integration
```

### Run with verbose output:
```bash
python manage.py test apps.scenario.tests -v 2
```

## Next Steps

1. Fix calculator instantiation in test_calculations.py
2. Create proper test fixtures with Species
3. Fix imports in test_api_endpoints.py
4. Complete test_model_validation.py
5. Add database query performance tests
6. Add test coverage reporting

## Test Coverage Goals

- Unit test coverage: 80%+ for calculation engines
- API test coverage: 100% of endpoints
- Integration test coverage: All major workflows
- Performance benchmarks: <30s for 900-day projections 