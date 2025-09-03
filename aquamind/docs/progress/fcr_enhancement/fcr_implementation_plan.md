# FCR Trend Calculations Implementation Plan

## Overview

This document outlines the implementation plan for the Feed Conversion Ratio (FCR) Trend Calculations feature as defined in the FCR PRD. The implementation will span multiple Django apps (inventory, batch, operational) and follow established coding standards and architectural principles.

**Key Decisions Based on Feedback:**
- **Confidence Logic**: Start with simple tiered system (<10 days = very high, 10-20 = high, 20-40 = medium, >40 = low) but design for future configurability and percentage-based precision
- **Predicted FCR**: Integrate with existing scenario app at batch level; handle missing scenarios gracefully
- **Caching**: Start with TimescaleDB continuous aggregates only; add Redis/Django cache only if performance profiling shows need
- **Testing**: Focus on critical logic and edge cases rather than blanket 90% coverage
- **API Contract**: Leverage existing CI for frontend regeneration; expect mostly additive changes

## Implementation Phases

### Phase 1: Preparation & Setup
**Goal**: Establish development environment and baseline understanding.

#### Checkpoint 1.1: Feature Branch Setup
- Create branch `feature/fcr-trend-calculations` from `main`
- Push initial commit referencing GitHub issue #19 and FCR PRD
- Set up development environment with TimescaleDB

#### Checkpoint 1.2: Existing Code Audit
- Review `inventory_batchfeedingsummary` model and existing FCR calculations
- Audit `batch_batchcontainerassignment` model structure
- Examine scenario app integration points
- Verify TimescaleDB setup and existing time-series operations

### Phase 2: Data Model Implementation
**Goal**: Implement minimal data model changes with confidence handling.

#### Checkpoint 2.1: Model Changes
- Add `confidence_level` field to `inventory_batchfeedingsummary` (choices: VERY_HIGH, HIGH, MEDIUM, LOW)
- Add `estimation_method` field (choices: MEASURED, INTERPOLATED)
- Add `last_weighing_date` field to `batch_batchcontainerassignment`
- Update model docstrings following PEP 257

#### Checkpoint 2.2: Migration Creation
- Generate Django migrations for new fields
- Since no production data exists, migrations can be straightforward
- Include data migration for backward compatibility if needed

### Phase 3: Core FCR Calculation Logic
**Goal**: Implement server-side FCR calculations with confidence assessment.

#### Checkpoint 3.1: FCR Service (Inventory App)
- Create `inventory/services/fcr_service.py` with `calculate_fcr_summary()` function
- Implement confidence calculation:
  - < 10 days: VERY_HIGH
  - 10-20 days: HIGH
  - 20-40 days: MEDIUM
  - > 40 days: LOW
- Handle estimation methods: MEASURED vs INTERPOLATED
- Account for mortality adjustments from health app

#### Checkpoint 3.2: Batch Service Enhancements
- Update `batch/services/growth_service.py` for growth sample tracking
- Implement Django signals to auto-update `last_weighing_date` on GrowthSample creation
- Add helper methods for growth sample queries used in FCR calculations

#### Checkpoint 3.3: Trends Aggregation Service
- Create `operational/services/fcr_trends_service.py`
- Implement TimescaleDB continuous aggregates for weekly/monthly FCR data
- Add filtering logic for batch, container-assignment, and geography levels
- Integrate predicted FCR from scenario models at batch level
- Handle cases where no scenario is attached (return null for predicted values)

### Phase 4: API Implementation
**Goal**: Create the FCR trends API endpoint following standards.

#### Checkpoint 4.1: API Components
- Create `operational/api/serializers.py` with `FCRTrendsSerializer`
- Implement `operational/api/viewsets.py` with `FCRTrendsViewSet`
- Update `operational/api/routers.py` with explicit kebab-case basename `fcr-trends`
- Register URL pattern: `/api/v1/operational/fcr-trends/`

#### Checkpoint 4.2: Query Parameters & Response
- Implement parameters: `start_date`, `end_date`, `interval` (DAILY/WEEKLY/MONTHLY)
- Add optional filters: `batch_id`, `assignment_id`, `geography_id`
- Response structure: `interval`, `unit`, `series` array with `actual_fcr`, `confidence`, `predicted_fcr`, `deviation`
- Include authentication and permission checks

### Phase 5: Testing & Quality Assurance
**Goal**: Comprehensive testing focusing on critical functionality.

#### Checkpoint 5.1: Unit Tests
- Test FCR calculation accuracy (±0.02 tolerance)
- Test confidence level assignment logic
- Test estimation method selection
- Cover edge cases: zero growth, missing growth samples, mortality impacts

#### Checkpoint 5.2: Integration Tests
- Test full API workflow with authentication
- Test cross-app integration (inventory + batch + operational + scenario)
- Test database transactions and error handling

#### Checkpoint 5.3: Contract Tests
- Validate router registration and URL patterns
- Ensure OpenAPI schema generation
- Test API standards compliance

### Phase 6: Performance Optimization
**Goal**: Optimize for the required <250ms p95 latency.

#### Checkpoint 6.1: TimescaleDB Optimization
- Implement continuous aggregates: `fcr_weekly`, `fcr_monthly`
- Add composite indexes on critical fields
- Profile query performance using Django Debug Toolbar

#### Checkpoint 6.2: Caching Evaluation
- If profiling shows bottlenecks (>250ms p95), implement caching
- Start with Django's built-in cache framework
- Consider Redis only if distributed caching is needed
- Cache keys: `(batch_id/assignment_id/geography_id, interval, date_range)`

### Phase 7: Documentation & Integration
**Goal**: Prepare for frontend consumption.

#### Checkpoint 7.1: API Documentation
- Update OpenAPI spec with endpoint documentation
- Document all query parameters and response formats
- Include authentication requirements and error responses

#### Checkpoint 7.2: Frontend Integration Guide
- Create guide for Batch Management Analytics page
- Document API usage patterns and data structures
- Provide example requests/responses for different aggregation levels

#### Checkpoint 7.3: Developer Documentation
- Update data_model.md with new fields
- Document FCR calculation logic and confidence system
- Create README for future maintenance

### Phase 8: Final Review & Deployment
**Goal**: Ensure production readiness.

#### Checkpoint 8.1: Code Review
- Validate compliance with code_organization_guidelines.md
- Review API standards adherence
- Confirm security and performance requirements

#### Checkpoint 8.2: Integration Testing
- End-to-end testing with frontend regeneration CI
- Validate OpenAPI schema updates trigger frontend client regeneration
- Test with sample data across all aggregation levels

#### Checkpoint 8.3: Merge Preparation
- Create pull request with comprehensive description
- Update implementation progress tracking
- Obtain approval for merge to main

## Quality Gates

Each phase includes quality gates to ensure implementation quality:

1. **Code Quality**: Follows PEP 8, PEP 257, and established patterns
2. **API Standards**: Complies with api_standards.md (kebab-case, explicit basenames)
3. **Testing**: Critical logic tested, edge cases covered
4. **Performance**: Meets <250ms requirement for typical queries
5. **Documentation**: API and developer docs complete
6. **Integration**: Frontend can consume the API without breaking changes

## Risk Mitigation

- **Incremental Development**: Each phase is self-contained with validation checkpoints
- **Backward Compatibility**: All changes are additive; existing APIs unchanged
- **Flexible Confidence System**: Designed for future enhancements (percentage-based, configurable)
- **Graceful Degradation**: Handle missing scenarios and data gaps elegantly
- **Performance Monitoring**: Start simple with TimescaleDB, add caching only when proven necessary

## Success Criteria

- ✅ FCR calculations accurate to ±0.02 FCR points
- ✅ API response time <250ms p95 for typical queries
- ✅ Confidence levels reflect data reliability appropriately
- ✅ Predicted FCR integrates seamlessly with scenario models
- ✅ Frontend regeneration CI handles API changes automatically
- ✅ All quality gates pass
- ✅ Comprehensive documentation for maintenance

This plan provides a structured approach to implementing the FCR trends feature while accommodating future enhancements and maintaining code quality standards.
