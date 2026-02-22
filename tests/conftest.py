import pytest
from app import create_app
import responses

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
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as rsps:
        yield rsps
