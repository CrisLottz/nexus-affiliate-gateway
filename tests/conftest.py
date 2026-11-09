import pytest

from nexus import create_app


@pytest.fixture
def app():
    return create_app({"nexus_env": "test", "secret_key": "test-secret-key-0123456789"})


@pytest.fixture
def client(app):
    return app.test_client()
