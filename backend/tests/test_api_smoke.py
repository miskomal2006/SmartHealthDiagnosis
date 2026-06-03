import importlib
import pathlib
import sys
import types

import pytest


class _DummyCursor:
    def __init__(self):
        self.rowcount = 1
        self.lastrowid = 1

    def execute(self, *_args, **_kwargs):
        return None

    def fetchone(self):
        return (0,)

    def fetchall(self):
        return []

    def close(self):
        return None


class _DummyConnection:
    def cursor(self):
        return _DummyCursor()

    def commit(self):
        return None


class _DummyMySQL:
    def __init__(self, _app):
        self.connection = _DummyConnection()


def _install_backend_test_stubs():
    flask_mysqldb = types.ModuleType("flask_mysqldb")
    flask_mysqldb.MySQL = _DummyMySQL
    sys.modules["flask_mysqldb"] = flask_mysqldb

    model_loader = types.ModuleType("model_loader")
    model_loader.MODELS = {}
    model_loader.load_models = lambda: None
    model_loader.predict = lambda _disease, _features: (0, 0.1)
    sys.modules["model_loader"] = model_loader

    pdf_generator = types.ModuleType("pdf_generator")
    pdf_generator.generate_pdf = lambda _data, _path: None
    sys.modules["pdf_generator"] = pdf_generator

    validators = types.ModuleType("validators")

    class _Schema:
        def load(self, data):
            return data

    validators.RegisterSchema = _Schema
    validators.LoginSchema = _Schema
    validators.DiagnosisSchema = _Schema
    sys.modules["validators"] = validators

    utils = types.ModuleType("utils")
    utils.hash_password = lambda value: value.encode()
    utils.verify_password = lambda _plain, _hashed: True
    utils.generate_token = lambda _uid, _role: "test-token"
    utils.calculate_risk = lambda _prob: "Low"
    utils.extract_features = lambda _data: []
    utils.generate_explanation = lambda _prob, _symptoms: []
    utils.log_action = lambda *_args, **_kwargs: None

    def _role_required(_roles):
        def _decorator(fn):
            return fn

        return _decorator

    utils.role_required = _role_required
    sys.modules["utils"] = utils


@pytest.fixture(scope="module")
def client():
    backend_dir = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_dir))
    _install_backend_test_stubs()
    sys.modules.pop("app", None)
    app_module = importlib.import_module("app")
    app_module.app.config["TESTING"] = True
    yield app_module.app.test_client()
    sys.path.pop(0)


def test_home_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Smart Health Diagnosis API Running Successfully" in response.data


def test_reset_password_requires_email_and_password(client):
    response = client.post("/api/reset-password", json={})
    assert response.status_code == 400
    assert response.get_json()["error"] == "Email and password are required"


def test_reset_password_enforces_min_length(client):
    response = client.post(
        "/api/reset-password",
        json={"email": "user@example.com", "password": "short"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Password must be at least 8 characters"


def test_admin_model_metrics_smoke(client):
    response = client.get("/api/admin/model-metrics")
    assert response.status_code == 200
    assert response.get_json() == {"models": {}}
