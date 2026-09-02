"""
conftest.py - Cấu hình chung cho toàn bộ test suite.

Cung cấp:
  - DB test riêng biệt (SQLite in-memory giả lập) không ảnh hưởng production
  - Mock Gemini API key -> trigger local fallback scoring
  - Mock require_admin dependency -> bypass Auth
  - fixture client, admin_headers, sample_job
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from app.database import get_db, Base
from app.dependencies import require_admin

# ─── Test Database ─────────────────────────────────────────────────────────────
SQLALCHEMY_TEST_URL = "sqlite:///./test_run.db"
test_engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override get_db globally for all tests
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create tables before all tests, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


# ─── Auth Fixture ──────────────────────────────────────────────────────────────
ADMIN_HEADERS = {"X-Admin-Key": "test-admin-key"}


@pytest.fixture(scope="session", autouse=True)
def mock_admin_auth():
    """Bypass require_admin for all tests."""
    app.dependency_overrides[require_admin] = lambda: None
    yield
    app.dependency_overrides.pop(require_admin, None)


@pytest.fixture(scope="session")
def admin_headers():
    return ADMIN_HEADERS


# ─── Gemini Mock ───────────────────────────────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def mock_no_api_key():
    """Suppress Gemini API calls - use local fallback scoring only."""
    with patch("app.services.gemini_service._get_api_key", return_value=None):
        yield


# ─── Test Client ───────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def client():
    return TestClient(app)


# ─── Background Scoring: Run Synchronously ────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def mock_scoring_sync():
    """
    Patch run_scoring_in_thread to run synchronously inside tests.
    This avoids race conditions where the test checks the DB before
    the background thread finishes scoring.
    Uses TestingSessionLocal so scoring reads/writes to the test DB.
    """
    from app.services import score_service

    def sync_score(application_id: int):
        db = TestingSessionLocal()
        try:
            score_service.run_scoring(application_id, db)
        except Exception:
            pass  # scoring errors are non-fatal in tests
        finally:
            db.close()

    with patch("app.routers.jobs.run_scoring_in_thread", side_effect=sync_score):
        yield


# ─── Shared Fixtures ───────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def sample_job(client, admin_headers):
    """Create a sample job once per module."""
    payload = {
        "title": "Python Developer TEST",
        "department": "Engineering",
        "location": "Hanoi, Vietnam",
        "job_type": "Full-time",
        "description": "Develop high-quality FastAPI applications and REST APIs using Python.",
        "requirements": "Python, FastAPI, SQL, Docker. Minimum 2 years experience.",
        "benefits": "Competitive salary, health insurance.",
        "status": "active",
    }
    res = client.post("/api/v1/jobs", json=payload, headers=admin_headers)
    assert res.status_code == 201, res.text
    return res.json()
