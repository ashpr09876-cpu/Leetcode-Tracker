import os

os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only-0123456789"
for k in ("AI_PROVIDER", "OLLAMA_BASE_URL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
    os.environ[k] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import Base, get_engine  # noqa: E402
from app import models  # noqa: E402,F401
from app.main import app  # noqa: E402

H = {"X-Requested-With": "codetrack"}


@pytest.fixture(autouse=True)
def _db():
    eng = get_engine()
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def register(client, email="a@example.com", password="password123"):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password, "name": "A"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def auth(client):
    return register(client)


@pytest.fixture()
def topic_id(client, auth):
    return client.get("/api/v1/topics", headers=auth).json()[0]["id"]


def make_problem(client, auth, **kw):
    body = {"title": "Two Sum", "difficulty": "easy", "status": "solved", **kw}
    r = client.post("/api/v1/problems", json=body, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()
