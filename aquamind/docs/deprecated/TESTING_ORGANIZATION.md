# AquaMind Testing Organization

This document explains the organization of testing files and how to run tests in the AquaMind project.

## 📁 File Organization

### Tests Location
```
tests/                                      # Project root - pytest standard location
└── test_django_admin_playwright.py        # Main Playwright test suite
```

### Quality Assurance Documentation & Tools
```
aquamind/docs/quality_assurance/
├── README_PLAYWRIGHT_TESTING.md           # Comprehensive Playwright testing guide
├── playwright.config.py                   # Playwright configuration
├── run_admin_tests.py                     # Test runner script
├── TESTING_ORGANIZATION.md               # This file
├── testing_strategy.md                   # Overall testing strategy
├── timescaledb_testing_strategy.md       # TimescaleDB specific testing
├── api_documentation_standards.md        # API testing standards
├── code_organization_guidelines.md       # Code organization guidelines
└── test-results/                         # Generated when tests run
    ├── report.html                       # HTML test report
    ├── screenshots/                      # Failure screenshots
    └── videos/                          # Test execution videos
```

## 🎯 Why This Organization?

### Best Practices Followed
- **`tests/` in project root**: Industry standard, expected by pytest, CI/CD tools, and IDEs
- **Documentation in quality_assurance/**: Keeps all QA materials organized together
- **Configuration co-located**: Test configs near documentation for easy maintenance

### Benefits
- ✅ **Tool Compatibility**: pytest, coverage tools, and IDEs find tests automatically
- ✅ **CI/CD Ready**: Standard location for automated testing pipelines
- ✅ **Documentation Organization**: All QA materials in one logical location
- ✅ **Maintainability**: Clear separation between test code and test documentation

## 🚀 Quick Start

### Running Tests

**From project root:**
```bash
# Simple run
python aquamind/docs/quality_assurance/run_admin_tests.py

# With options
python aquamind/docs/quality_assurance/run_admin_tests.py --type smoke --browser firefox --headless

# Direct pytest
pytest tests/test_django_admin_playwright.py -v --browser firefox
```

### Prerequisites
1. Django server running: `python manage.py runserver 8000`
2. Dependencies installed: `pip install pytest playwright pytest-playwright`
3. Browser binaries: `npx playwright install firefox`

## 📊 Test Results

After running tests, find results in:
- **HTML Report**: `aquamind/docs/quality_assurance/test-results/report.html`
- **Screenshots**: `aquamind/docs/quality_assurance/test-results/screenshots/`
- **Videos**: `aquamind/docs/quality_assurance/test-results/videos/`

## 🔧 Configuration

- **Playwright Config**: `aquamind/docs/quality_assurance/playwright.config.py`
- **Test Runner**: `aquamind/docs/quality_assurance/run_admin_tests.py`
- **Documentation**: `aquamind/docs/quality_assurance/README_PLAYWRIGHT_TESTING.md`

## 📝 Adding New Tests

1. **Add test methods** to `tests/test_django_admin_playwright.py`
2. **Update documentation** in `aquamind/docs/quality_assurance/README_PLAYWRIGHT_TESTING.md`
3. **Run tests** to verify functionality

## 🤝 Team Guidelines

- **Tests**: Always add to `tests/` directory
- **Documentation**: Update QA docs when adding new test categories
- **Configuration**: Modify configs in `quality_assurance/` folder
- **Results**: Check HTML reports for detailed test analysis

---

This organization balances industry best practices with project-specific documentation needs, ensuring both tool compatibility and team productivity. 