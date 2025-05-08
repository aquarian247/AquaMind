# AquaMind Testing Strategy

This document outlines the testing approach for the AquaMind project, including testing practices, conventions, and when and how tests should be run.

## 1. Testing Philosophy

AquaMind follows a comprehensive testing approach to ensure high-quality code and reliable functionality. Our testing philosophy is built on these principles:

- **Test-First Mindset**: Write tests before or alongside feature development, not after
- **Comprehensive Coverage**: Aim for high test coverage of critical business logic
- **Automated Testing**: Integrate testing into our development workflow and CI/CD pipeline
- **Maintainable Tests**: Tests should be as maintainable as application code

## 2. Types of Tests

### 2.1 Unit Tests

Unit tests verify individual components in isolation, typically at the function or class level.

**Example**: Testing a model's validation logic or a utility function.

```python
class AreaModelTest(TestCase):
    def test_area_latitude_validation(self):
        invalid_area = Area(
            name="Invalid Area",
            geography=self.geography,
            latitude=100,  # Invalid: > 90
            longitude=20,
            max_biomass=1000
        )
        with self.assertRaises(ValidationError):
            invalid_area.full_clean()
```

### 2.2 Integration Tests

Integration tests verify that different components work together correctly.

**Example**: Testing API endpoints with the database.

```python
class EnvironmentalReadingAPITest(APITestCase):
    def test_create_reading(self):
        # Test that a reading can be created through the API
        response = self.client.post(
            '/api/environmental/readings/',
            data={...},
            format='json'
        )
        self.assertEqual(response.status_code, 201)
```

### 2.3 End-to-End Tests

End-to-end tests verify entire workflows from start to finish.

**Example**: Testing a batch creation process through the UI.

## 3. Testing Structure

### 3.1 Directory Structure

Tests are organized within each Django app in a `tests` directory with specific test files:

```
apps/
├── environmental/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_views.py
│   │   ├── test_api.py
│   │   └── test_timescaledb.py
├── infrastructure/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   └── test_views.py
```

### 3.2 Test Naming Conventions

- Test classes should be named `{Feature}Test`
- Test methods should be named `test_{action}_{condition}` to clearly describe what they test
- Test files should be named `test_{module}.py`

### 3.3 Test Organization

Tests should be organized by features and functionality:

```python
class ContainerModelTest(TestCase):
    # Setup common test fixtures
    def setUp(self):
        # Create prerequisites for container tests
        
    # Group related tests together
    def test_container_creation(self):
        # Test basic creation functionality
        
    def test_container_validation(self):
        # Test validation rules
```

## 4. Testing Best Practices

### 4.1 Test Independence

- Each test should be independent and not rely on the state from other tests
- Use `setUp()` and `tearDown()` methods for proper test isolation
- Create all required test data within the test itself or in `setUp()`

### 4.2 Testing TimescaleDB Features

When testing TimescaleDB-specific functionality:

- Create hypertable test fixtures with realistic time-series data
- Test time-based partitioning and chunk creation
- Verify query performance with large datasets

```python
def test_time_range_queries(self):
    # Create readings across multiple time chunks
    # Query data using time-based filters
    # Verify results
```

### 4.3 Django-Specific Testing Practices

- Use Django's `TestCase` for tests requiring database access
- Use `TransactionTestCase` for tests that need transaction testing
- Use `SimpleTestCase` for tests not requiring database access
- Use `Client` for testing views and APIs
- Use management commands for test data generation when needed

## 5. When to Run Tests

### 5.1 Local Development

- **During Development**: Run relevant test modules during feature development
  ```bash
  python manage.py test apps.app_name.tests.test_file
  ```

- **Before Committing**: Run all tests for the app you modified
  ```bash
  python manage.py test apps.app_name
  ```

- **Before Pull Requests**: Run the complete test suite
  ```bash
  python manage.py test
  ```

### 5.2 Continuous Integration

Tests are automatically run:
- On every push to any branch
- When a pull request is created or updated
- Before deployment to staging/production

## 6. Test Coverage

- Aim for 80%+ test coverage for critical business logic
- Generate coverage reports with:
  ```bash
  coverage run --source='.' manage.py test
  coverage report
  ```

- Review coverage reports regularly and identify areas needing better test coverage

## 7. Test Performance

- Keep individual tests focused and fast
- Use Django's test database features for speed
- Group slow tests (e.g., TimescaleDB operations) to run separately when needed

```bash
python manage.py test --tag=slow
```

## 8. Continuous Integration Setup

AquaMind uses GitHub Actions for CI/CD. The primary testing workflow (defined in `.github/workflows/django-tests.yml`) involves the following:

1.  **Testing Environment**: 
    *   Tests are executed against a **PostgreSQL** database service (using a `timescale/timescaledb` Docker image).
    *   The Django settings file `scripts/testing/test_settings.py` is used, which configures the connection to this PostgreSQL service.
    *   Within these settings, `TIMESCALE_ENABLED = False` is typically set to run tests against a standard PostgreSQL setup without relying on active TimescaleDB-specific database features during most automated tests.
2.  **Test Execution**: The test suite is run on every push and pull request to the `main` and `develop` branches.
3.  **Linting**: Code style is checked using flake8.
4.  **Security Scanning**: Dependencies are scanned for vulnerabilities (if configured).
5.  **Deployment**: Code is deployed to staging or production environments after tests pass.

For detailed CI configuration, refer to the workflow files in the `.github/workflows` directory.

**Note on Local Testing vs. CI**: While the CI pipeline uses PostgreSQL, faster local testing can be performed using SQLite. This can be achieved by:
*   Using the `run_tests.sh` script (which utilizes `aquamind/test_settings.py` configured for a file-based SQLite database).
*   Directly invoking `python manage.py test --settings=aquamind.settings_ci.py` (which uses `aquamind/settings_ci.py` configured for an in-memory SQLite database).

It's important to ensure that code (especially migrations) is compatible with both PostgreSQL (for CI and production) and SQLite (for local testing flexibility).

## 9. Test Troubleshooting

### Common Issues

- **Database Constraint Errors**: Ensure proper test data setup
- **Invalid Test Assertions**: Check expected vs actual values
- **Transaction Rollback Issues**: Use TransactionTestCase when needed

## 10. Future Testing Strategy

As the project evolves:

- Implement browser-based testing for Vue.js frontend
- Add performance profiling to TimescaleDB hypertable tests
- Set up integration tests with external APIs

## 11. Testing Resources

- [Django Testing Documentation](https://docs.djangoproject.com/en/4.2/topics/testing/)
- [TimescaleDB Testing Best Practices](https://docs.timescale.com/latest/tutorials/best-practices/)
- [Python Testing Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
