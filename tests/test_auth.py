import pytest
from app import app, init_db

@pytest.fixture(autouse=True)
def setup_db():
    # Initialize DB (creates instance/enrollment.db under project instance path)
    with app.app_context():
        init_db()
    yield

def test_login_success():
    client = app.test_client()
    rv = client.post('/api/login', json={'username': 'admin', 'password': 'admin'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get('success') is True
    assert data.get('user', {}).get('username') == 'admin'

def test_login_failure_wrong_password():
    client = app.test_client()
    rv = client.post('/api/login', json={'username': 'admin', 'password': 'wrong'})
    assert rv.status_code == 401
    data = rv.get_json()
    assert data.get('success') is False

def test_login_failure_unknown_user():
    client = app.test_client()
    rv = client.post('/api/login', json={'username': 'nosuch', 'password': 'x'})
    assert rv.status_code == 401
    data = rv.get_json()
    assert data.get('success') is False
