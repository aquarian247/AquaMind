"""
Playwright Configuration for AquaMind Django Admin Testing

This configuration file sets up Playwright for testing the Django admin interface
with appropriate browser settings, timeouts, and reporting options.
"""

from playwright.sync_api import Playwright
import pytest


# Playwright configuration
def pytest_configure(config):
    """Configure pytest for Playwright testing"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for all tests"""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
        "record_video_dir": "test-results/videos/",
        "record_video_size": {"width": 1920, "height": 1080},
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Configure browser launch arguments"""
    return {
        **browser_type_launch_args,
        "headless": False,  # Set to True for CI/CD
        "slow_mo": 100,     # Slow down actions for debugging
        "args": [
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
        ]
    }


# Test configuration
class PlaywrightConfig:
    """Playwright test configuration"""
    
    # Base URL for the Django application
    BASE_URL = "http://localhost:8000"
    
    # Admin credentials (should be environment variables in production)
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "admin"  # Update with actual password
    
    # Timeouts
    DEFAULT_TIMEOUT = 30000  # 30 seconds
    NAVIGATION_TIMEOUT = 60000  # 60 seconds
    
    # Test data
    TEST_BATCH_PREFIX = "PLAYWRIGHT_TEST"
    
    # Screenshots and videos
    SCREENSHOT_ON_FAILURE = True
    RECORD_VIDEO = True
    
    # Browser settings
    BROWSERS = ["chromium", "firefox", "webkit"]  # Test on multiple browsers
    HEADLESS = False  # Set to True for CI/CD
    
    # Parallel execution
    MAX_WORKERS = 4


# Utility functions for tests
class TestUtils:
    """Utility functions for Playwright tests"""
    
    @staticmethod
    def generate_unique_id():
        """Generate a unique ID for test data"""
        import time
        return str(int(time.time() * 1000))
    
    @staticmethod
    def wait_for_admin_page_load(page):
        """Wait for Django admin page to fully load"""
        page.wait_for_selector('h1:has-text("Django administration")', timeout=10000)
    
    @staticmethod
    def login_admin(page, username=None, password=None):
        """Login to Django admin"""
        username = username or PlaywrightConfig.ADMIN_USERNAME
        password = password or PlaywrightConfig.ADMIN_PASSWORD
        
        page.goto(f"{PlaywrightConfig.BASE_URL}/admin/")
        
        if "login" in page.url:
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)
            page.click('input[type="submit"]')
            
        # Wait for successful login
        page.wait_for_selector('text=Welcome,', timeout=10000)
    
    @staticmethod
    def take_screenshot(page, name):
        """Take a screenshot with a specific name"""
        page.screenshot(path=f"test-results/screenshots/{name}.png")
    
    @staticmethod
    def cleanup_test_data(page):
        """Clean up test data created during tests"""
        # This would implement cleanup logic for test batches, etc.
        pass


# Pytest fixtures
@pytest.fixture
def config():
    """Provide configuration to tests"""
    return PlaywrightConfig


@pytest.fixture
def utils():
    """Provide utility functions to tests"""
    return TestUtils


@pytest.fixture(autouse=True)
def setup_test_environment(page):
    """Set up test environment before each test"""
    # Set default timeout
    page.set_default_timeout(PlaywrightConfig.DEFAULT_TIMEOUT)
    
    # Set navigation timeout
    page.set_default_navigation_timeout(PlaywrightConfig.NAVIGATION_TIMEOUT)
    
    yield
    
    # Cleanup after test if needed
    # TestUtils.cleanup_test_data(page)


# Custom markers for different test types
pytest_plugins = ["playwright.sync_api"]


def pytest_collection_modifyitems(config, items):
    """Add custom markers to tests based on their names"""
    for item in items:
        # Mark slow tests
        if "performance" in item.name or "large_dataset" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # Mark integration tests
        if "integration" in item.name:
            item.add_marker(pytest.mark.integration)
        
        # Mark UI tests
        if any(keyword in item.name for keyword in ["ui", "theme", "responsive"]):
            item.add_marker(pytest.mark.ui)


# Test reporting configuration
def pytest_html_report_title(report):
    """Customize HTML report title"""
    report.title = "AquaMind Django Admin Playwright Test Report"


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "ui: marks tests as UI/UX tests"
    )
    config.addinivalue_line(
        "markers", "smoke: marks tests as smoke tests"
    ) 