import pytest
from app import create_app
import responses

# Reset the account info cache between tests so mocks fire properly
from app import _account_cache, _CACHE_TTL

@pytest.fixture
def app():
    # Setup our flask test app
    app = create_app()
    app.config.update({
        "TESTING": True,
        "REAL_DEBRID_API_KEY": "test_rd_key",
        "JACKETT_API_KEY": "test_jackett_key",
        "JACKETT_URL": "http://localhost:9117",
        "WTF_CSRF_ENABLED": False
    })
    # Reset the account info cache so each test starts fresh
    _account_cache["data"] = None
    _account_cache["error"] = None
    _account_cache["expires"] = 0
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def mocked_responses():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps
