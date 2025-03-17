# WeatherAPI Tests

## Note on Test Expectations

Some of the tests in `test_weather_api.py` have specific expectations about the number of data points returned by the API, which may vary between different environments:

1. In `test_list_weather_data` - Expects 6 entries in CI environment
2. In `test_time_filtering` - Expects 3 entries in CI environment

If these tests fail in your environment, you may need to adjust the expected counts based on your specific setup. The difference in counts can occur due to:

- Different database backends (PostgreSQL vs. SQLite vs. TimescaleDB)
- Different test data initialization
- Different pagination settings

## Testing Strategy

As per our testing strategy document:

1. TimescaleDB-specific features are tested manually
2. Basic API functionality is tested in CI using regular PostgreSQL
3. Some functionality may behave differently with or without TimescaleDB

Refer to the `timescaledb_testing_strategy.md` document for detailed guidance on testing TimescaleDB features.
