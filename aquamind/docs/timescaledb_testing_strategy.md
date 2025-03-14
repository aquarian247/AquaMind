# TimescaleDB Testing Strategy

## Overview

This document outlines the strategy for testing TimescaleDB features in the AquaMind project. Due to the complexity of setting up TimescaleDB properly in test environments and the challenges with Django's test database creation process, we've adopted a specialized approach to testing TimescaleDB-specific functionality.

## Testing Approach

### Automated Testing

For automated testing and CI/CD pipelines, we take the following approach:

1. **Skip TimescaleDB-Specific Tests**
   - All tests that verify TimescaleDB-specific features (hypertables, compression, retention policies) are marked with `@unittest.skip` to prevent them from running in automated testing environments.
   - This ensures that CI/CD pipelines and regular test runs can proceed without requiring a fully configured TimescaleDB setup.

2. **SQLite for Regular Tests**
   - We use SQLite as the database backend for automated tests to simplify the testing process.
   - This is configured in the `aquamind/test_settings.py` file.

3. **Conditional SQL Operations**
   - We've created a helper module (`apps.environmental.migrations_helpers`) that provides utilities to conditionally execute TimescaleDB-specific SQL operations.
   - These helpers check the database type and environment settings before attempting TimescaleDB operations.

### Manual Testing

For TimescaleDB feature verification, we use a manual testing approach:

1. **Dedicated Test Script**
   - We've created a script (`run_timescaledb_tests.sh`) to run TimescaleDB-specific tests manually.
   - This script uses a specialized test settings file (`aquamind/timescaledb_test_settings.py`) that maintains PostgreSQL with TimescaleDB as the database backend.

2. **Environment Variable Control**
   - Tests use the `USE_TIMESCALEDB_TESTING` environment variable to determine whether TimescaleDB operations should be executed.
   - This variable is set to "true" when running manual TimescaleDB tests.

3. **Custom Test Runner**
   - A custom test runner (`TimescaleDBTestRunner`) is used to handle database setup and cleanup properly.

## Manual Testing Instructions

To manually test TimescaleDB features:

1. Ensure PostgreSQL with TimescaleDB is properly configured on your development environment.
2. Run the manual test script:
   ```bash
   ./run_timescaledb_tests.sh
   ```
3. Review the test output to verify that TimescaleDB features are working correctly.

## Best Practices

1. **Always Test in Production-Like Environment**
   - Before deploying, ensure that TimescaleDB features are manually tested in an environment that closely mirrors production.

2. **Document TimescaleDB Results**
   - When manually testing TimescaleDB features, document the results and any issues encountered.

3. **Separate TimescaleDB Tests**
   - Keep TimescaleDB-specific tests separate from regular application tests to maintain clean test separation.

## Future Improvements

In the future, we may explore:

1. Docker-based automated testing that fully configures TimescaleDB for testing
2. Integration with a more robust testing framework for time-series databases
3. Improved mocking strategies for TimescaleDB features to allow for more comprehensive automated testing
