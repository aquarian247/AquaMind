# AquaMind Django Admin Playwright Testing

This document describes the comprehensive Playwright testing setup for the AquaMind Django admin interface.

## 🎯 Overview

The Playwright testing framework provides automated browser testing for the AquaMind Django admin interface, covering:

- **Authentication & Navigation** - Login, logout, and navigation testing
- **CRUD Operations** - Create, Read, Update, Delete operations for all models
- **Data Validation** - Form validation and data integrity checks
- **UI/UX Testing** - Responsive design, theme switching, accessibility
- **Performance Testing** - Page load times and large dataset handling
- **Integration Testing** - End-to-end workflows across multiple modules

## 🚀 Quick Start

### Prerequisites

1. **Django Server Running**:
   ```bash
   python manage.py runserver 8000
   ```

2. **Install Dependencies**:
   ```bash
   pip install pytest playwright pytest-playwright pytest-html
   npx playwright install firefox  # Install browser binaries
   ```

### Running Tests

**From project root:**
```bash
python aquamind/docs/quality_assurance/run_admin_tests.py
```

**With options:**
```bash
python aquamind/docs/quality_assurance/run_admin_tests.py --type smoke --browser firefox --headless
```

**Direct pytest (from project root):**
```bash
pytest tests/test_django_admin_playwright.py -v --browser firefox
```

## 📁 File Structure

```
├── tests/
│   └── test_django_admin_playwright.py    # Main test suite (project root)
├── aquamind/docs/quality_assurance/
│   ├── README_PLAYWRIGHT_TESTING.md       # This documentation
│   ├── playwright.config.py               # Playwright configuration
│   ├── run_admin_tests.py                 # Test runner script
│   └── test-results/                      # Generated test artifacts
│       ├── report.html                    # HTML test report
│       ├── screenshots/                   # Failure screenshots
│       └── videos/                        # Test execution videos
```

**Note:** Tests are kept in the project root `tests/` folder following pytest best practices, while documentation and configuration are organized in the quality assurance folder.

## 🧪 Test Categories

### 1. Authentication Tests
- Login page validation
- Successful/failed login attempts
- Session management
- Logout functionality

### 2. Batch Management Tests
- Batch list view and filtering
- Batch detail/edit forms
- Batch creation and validation
- Search functionality
- Calculated field verification

### 3. Infrastructure Tests
- Container management
- Geography and location data
- Sensor monitoring
- Area and hall management

### 4. Health Monitoring Tests
- Lab sample management
- Mortality record tracking
- Health journal entries
- Treatment logging

### 5. Inventory Tests
- Feed management
- Purchase tracking
- Stock level monitoring
- Feeding event logging

### 6. Data Validation Tests
- Required field validation
- Unique constraint testing
- Date format validation
- Numeric field validation

### 7. UI/UX Tests
- Responsive design testing
- Theme toggle functionality
- Breadcrumb navigation
- Sidebar navigation

### 8. Performance Tests
- Page load time measurement
- Large dataset handling
- Pagination testing

## 🎛️ Configuration

### Browser Selection
```bash
# Test with different browsers
python aquamind/docs/quality_assurance/run_admin_tests.py --browser chromium
python aquamind/docs/quality_assurance/run_admin_tests.py --browser firefox
python aquamind/docs/quality_assurance/run_admin_tests.py --browser webkit
```

### Test Filtering
```bash
# Run only smoke tests
python aquamind/docs/quality_assurance/run_admin_tests.py --type smoke

# Run only UI tests
python aquamind/docs/quality_assurance/run_admin_tests.py --type ui

# Run fast tests (exclude slow tests)
python aquamind/docs/quality_assurance/run_admin_tests.py --type fast

# Run integration tests
python aquamind/docs/quality_assurance/run_admin_tests.py --type integration
```

### Headless Mode
```bash
# Run without opening browser window
python aquamind/docs/quality_assurance/run_admin_tests.py --headless
```

## 📊 Test Reports

After running tests, you'll find:

1. **HTML Report**: `aquamind/docs/quality_assurance/test-results/report.html`
   - Detailed test results with pass/fail status
   - Execution times and error details
   - Screenshots of failures

2. **Screenshots**: `aquamind/docs/quality_assurance/test-results/screenshots/`
   - Automatic screenshots on test failures
   - Manual screenshots for debugging

3. **Videos**: `aquamind/docs/quality_assurance/test-results/videos/`
   - Full test execution recordings
   - Useful for debugging complex interactions

## 🔧 Advanced Usage

### Custom Test Configuration

Edit `aquamind/docs/quality_assurance/playwright.config.py` to customize:
- Browser settings
- Timeouts
- Video recording options
- Screenshot settings

### Adding New Tests

1. **Create test class** in `tests/test_django_admin_playwright.py`:
```python
class TestNewFeature:
    def test_new_functionality(self, page: Page):
        page.goto("http://localhost:8000/admin/new-feature/")
        # Test implementation
```

2. **Add markers** for test categorization:
```python
@pytest.mark.smoke
def test_critical_feature(self, page: Page):
    # Critical functionality test
```

### Debugging Tests

1. **Run single test** (from project root):
```bash
pytest tests/test_django_admin_playwright.py::TestBatchManagement::test_batch_list_view -v
```

2. **Enable debug mode**:
```python
# In test file, add:
page.pause()  # Opens browser inspector
```

3. **Slow motion**:
```python
# In playwright.config.py:
"slow_mo": 1000  # 1 second delay between actions
```

## 🎯 Test Scenarios Covered

### Batch Management
- ✅ List view with pagination
- ✅ Filtering by lifecycle stage and status
- ✅ Search functionality
- ✅ Batch detail view with calculated fields
- ✅ Form validation for new batches
- ✅ Unique batch number validation

### Infrastructure Management
- ✅ Container list with 100+ records
- ✅ Container type filtering
- ✅ Volume and biomass calculations
- ✅ Location-based organization
- ✅ Active/inactive status management

### Health Monitoring
- ✅ Lab sample tracking
- ✅ Mortality record management
- ✅ Health parameter monitoring
- ✅ Treatment logging
- ✅ Sample type management

### Feed & Inventory
- ✅ Feed type management
- ✅ Purchase order tracking
- ✅ Stock level monitoring
- ✅ FIFO inventory validation
- ✅ Feeding event logging

## 🚨 Common Issues & Solutions

### Browser Installation Issues
```bash
# Reinstall browser binaries
npx playwright install --force firefox
```

### Permission Issues on Windows
```bash
# Run as administrator or install to user directory
npx playwright install firefox --user
```

### Django Server Not Running
```bash
# Ensure server is running on correct port
python manage.py runserver 8000
```

### Test Timeouts
- Increase timeouts in `aquamind/docs/quality_assurance/playwright.config.py`
- Check network connectivity
- Verify Django server performance

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
name: Django Admin Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          npx playwright install firefox
      - name: Run Django server
        run: python manage.py runserver 8000 &
      - name: Run tests
        run: python aquamind/docs/quality_assurance/run_admin_tests.py --headless --type smoke
```

## 📈 Best Practices

1. **Test Data Management**
   - Use fixtures for consistent test data
   - Clean up test data after tests
   - Use unique identifiers for test records

2. **Page Object Pattern**
   - Create reusable page objects for complex forms
   - Encapsulate element selectors
   - Improve test maintainability

3. **Assertions**
   - Use specific assertions for better error messages
   - Test both positive and negative scenarios
   - Verify calculated fields and relationships

4. **Performance**
   - Run tests in parallel when possible
   - Use headless mode for CI/CD
   - Optimize test data setup

## 🤝 Contributing

When adding new tests:

1. Follow existing naming conventions
2. Add appropriate test markers
3. Include docstrings for test methods
4. Update this README if adding new test categories
5. Ensure tests are independent and can run in any order

## 📞 Support

For issues with the testing setup:

1. Check the test output and HTML report
2. Review browser console logs
3. Verify Django admin functionality manually
4. Check Playwright documentation for advanced features

---

**Happy Testing! 🎭** 