import os
import pytest
import responses

# Ensure required env vars are set BEFORE importing create_app,
# since the app factory validates them at startup.
os.environ.setdefault('REAL_DEBRID_API_KEY', 'test_rd_key')
os.environ.setdefault('JACKETT_API_KEY', 'test_jackett_key')
os.environ.setdefault('JACKETT_URL', 'http://localhost:9117')

from app import create_app

# Reset the account info cache between tests so mocks fire properly
from app import _account_cache


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "REAL_DEBRID_API_KEY": "test_rd_key",
        "JACKETT_API_KEY": "test_jackett_key",
        "JACKETT_URL": "http://localhost:9117",
        "WTF_CSRF_ENABLED": False,
    })
    # Reset the account info cache so each test starts fresh
    _account_cache["data"] = None
    _account_cache["error"] = None
    _account_cache["expires"] = 0
    yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def mocked_responses():
    """Activate the responses library to mock HTTP requests."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps
