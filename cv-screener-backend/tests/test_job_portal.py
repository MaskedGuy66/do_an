"""
Comprehensive test suite for the CV Screener Job Portal API.
Covers: job CRUD, application flow, filters/sort, manual evaluate, admin review, error cases.
"""

import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# ──────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────

SAMPLE_CV_CONTENT = (
    b"Candidate Name: John Doe. Email: john@example.com. Phone: 0987654321. "
    b"Experience: 3 nam kinh nghiem backend Python va FastAPI. "
    b"Skills: Python, FastAPI, Postgres, Docker, Redis. "
    b"Education: Dai hoc Cong nghe thong tin."
)

JOB_PAYLOAD = {
    "title": "Python Developer TEST",
    "department": "Engineering",
    "location": "Hanoi, Vietnam",
    "job_type": "Full-time",
    "description": "Develop high-quality FastAPI applications and REST APIs.",
    "requirements": "Python, FastAPI, SQL, Docker. Minimum 2 years experience.",
    "benefits": "Competitive salary, health insurance, 15 days annual leave.",
    "status": "active",
}


@pytest.fixture(scope="module")
def mock_no_api_key():
    """Patch Gemini API key to be absent, triggering local fallback scoring."""
    with patch("app.services.gemini_service._get_api_key", return_value=None):
        yield


@pytest.fixture(scope="module")
def created_job(mock_no_api_key):
    """Create a job once and return it for tests in this module."""
    res = client.post("/api/v1/jobs", json=JOB_PAYLOAD)
    assert res.status_code == 201
    return res.json()


@pytest.fixture(scope="module")
def submitted_application(created_job, mock_no_api_key):
    """Submit one application against the created_job fixture."""
    job_id = created_job["id"]
    files = {"cv_file": ("cv.txt", SAMPLE_CV_CONTENT, "text/plain")}
    form = {
        "full_name": "John Doe",
        "email": "john@example.com",
        "phone": "0987654321",
        "cover_letter": "I love FastAPI and building scalable systems!",
    }
    res = client.post(f"/api/v1/jobs/{job_id}/apply", data=form, files=files)
    assert res.status_code == 201
    return res.json()


# ──────────────────────────────────────────────
# JOB POSTING TESTS
# ──────────────────────────────────────────────

class TestJobPosting:

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_create_job_all_fields(self, _):
        payload = {**JOB_PAYLOAD, "title": "Full Fields Test Job"}
        res = client.post("/api/v1/jobs", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Full Fields Test Job"
        assert data["department"] == "Engineering"
        assert data["location"] == "Hanoi, Vietnam"
        assert data["benefits"] == "Competitive salary, health insurance, 15 days annual leave."
        assert data["status"] == "active"
        assert "id" in data
        assert "created_at" in data
        # Cleanup
        client.delete(f"/api/v1/jobs/{data['id']}")

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_create_job_minimal(self, _):
        res = client.post("/api/v1/jobs", json={"title": "Minimal Job"})
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Minimal Job"
        assert data["department"] is None
        client.delete(f"/api/v1/jobs/{data['id']}")

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_list_jobs(self, _):
        res = client.get("/api/v1/jobs")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_list_jobs_filter_by_status(self, _):
        # Create a closed job
        closed = client.post("/api/v1/jobs", json={**JOB_PAYLOAD, "title": "Closed Job", "status": "closed"})
        assert closed.status_code == 201
        closed_id = closed.json()["id"]

        res = client.get("/api/v1/jobs?status=closed")
        assert res.status_code == 200
        jobs = res.json()
        assert all(j["status"] == "closed" for j in jobs)
        assert any(j["id"] == closed_id for j in jobs)

        res2 = client.get("/api/v1/jobs?status=active")
        assert res2.status_code == 200
        assert all(j["status"] == "active" for j in res2.json())

        client.delete(f"/api/v1/jobs/{closed_id}")

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_get_job(self, _, created_job):
        res = client.get(f"/api/v1/jobs/{created_job['id']}")
        assert res.status_code == 200
        assert res.json()["id"] == created_job["id"]

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_get_nonexistent_job(self, _):
        res = client.get("/api/v1/jobs/9999999")
        assert res.status_code == 404

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_update_job(self, _, created_job):
        job_id = created_job["id"]
        res = client.put(f"/api/v1/jobs/{job_id}", json={"title": "Updated Title", "status": "draft"})
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "draft"
        # Restore
        client.put(f"/api/v1/jobs/{job_id}", json=JOB_PAYLOAD)

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_delete_job_cascade(self, _):
        # Create job then delete and ensure 404 on re-fetch
        tmp = client.post("/api/v1/jobs", json={**JOB_PAYLOAD, "title": "Tmp Job To Delete"})
        assert tmp.status_code == 201
        jid = tmp.json()["id"]
        del_res = client.delete(f"/api/v1/jobs/{jid}")
        assert del_res.status_code == 200
        get_res = client.get(f"/api/v1/jobs/{jid}")
        assert get_res.status_code == 404


# ──────────────────────────────────────────────
# APPLICATION TESTS
# ──────────────────────────────────────────────

class TestJobApplication:

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_apply_success(self, _, created_job):
        job_id = created_job["id"]
        files = {"cv_file": ("cv.txt", SAMPLE_CV_CONTENT, "text/plain")}
        form = {"full_name": "Jane Smith", "email": "jane@example.com", "phone": "0912345678"}
        res = client.post(f"/api/v1/jobs/{job_id}/apply", data=form, files=files)
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "submitted"
        assert "application_id" in data
        assert "job_id" in data

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_apply_invalid_file_type(self, _, created_job):
        job_id = created_job["id"]
        files = {"cv_file": ("resume.exe", b"binary content", "application/octet-stream")}
        form = {"full_name": "Bad User", "email": "bad@test.com", "phone": "000"}
        res = client.post(f"/api/v1/jobs/{job_id}/apply", data=form, files=files)
        assert res.status_code == 400
        assert "Định dạng" in res.json()["detail"] or "không hỗ trợ" in res.json()["detail"]

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_apply_empty_file(self, _, created_job):
        job_id = created_job["id"]
        files = {"cv_file": ("empty.txt", b"", "text/plain")}
        form = {"full_name": "Empty User", "email": "empty@test.com", "phone": "111"}
        res = client.post(f"/api/v1/jobs/{job_id}/apply", data=form, files=files)
        assert res.status_code == 400
        assert "trống" in res.json()["detail"]

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_apply_to_nonexistent_job(self, _):
        files = {"cv_file": ("cv.txt", SAMPLE_CV_CONTENT, "text/plain")}
        form = {"full_name": "Ghost", "email": "ghost@test.com", "phone": "000"}
        res = client.post("/api/v1/jobs/9999999/apply", data=form, files=files)
        assert res.status_code == 404

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_apply_cv_too_short(self, _, created_job):
        """CV text with fewer than 50 chars after extraction should fail."""
        job_id = created_job["id"]
        files = {"cv_file": ("tiny.txt", b"short", "text/plain")}
        form = {"full_name": "Tiny CV", "email": "tiny@test.com", "phone": "123"}
        res = client.post(f"/api/v1/jobs/{job_id}/apply", data=form, files=files)
        assert res.status_code == 422

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_list_applications(self, _, created_job, submitted_application):
        job_id = created_job["id"]
        res = client.get(f"/api/v1/jobs/{job_id}/applications")
        assert res.status_code == 200
        apps = res.json()
        assert len(apps) >= 1

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_list_applications_filter_status(self, _, created_job, submitted_application):
        job_id = created_job["id"]
        res = client.get(f"/api/v1/jobs/{job_id}/applications?status=submitted")
        assert res.status_code == 200
        for app in res.json():
            assert app["status"] == "submitted"

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_list_applications_filter_review_status(self, _, created_job, submitted_application):
        job_id = created_job["id"]
        res = client.get(f"/api/v1/jobs/{job_id}/applications?review_status=new")
        assert res.status_code == 200
        for app in res.json():
            assert app["review_status"] == "new"

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_list_applications_sort(self, _, created_job):
        job_id = created_job["id"]
        for sort_val in ["created_at|desc", "created_at|asc", "full_name|asc"]:
            sb, order = sort_val.split("|")
            res = client.get(f"/api/v1/jobs/{job_id}/applications?sort_by={sb}&order={order}")
            assert res.status_code == 200

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_get_application_detail(self, _, created_job, submitted_application):
        job_id = created_job["id"]
        app_id = submitted_application["application_id"]
        res = client.get(f"/api/v1/jobs/{job_id}/applications/{app_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == app_id
        assert data["full_name"] == "John Doe"
        assert data["email"] == "john@example.com"
        # Background task should have run in TestClient (sync)
        assert data["status"] == "ai_reviewed"
        assert data["ai_score"] is not None
        assert data["ai_evaluation"] is not None

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_get_nonexistent_application(self, _, created_job):
        job_id = created_job["id"]
        res = client.get(f"/api/v1/jobs/{job_id}/applications/9999999")
        assert res.status_code == 404


# ──────────────────────────────────────────────
# ADMIN REVIEW TESTS
# ──────────────────────────────────────────────

class TestAdminReview:

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_patch_review_status(self, _, created_job, submitted_application):
        job_id = created_job["id"]
        app_id = submitted_application["application_id"]
        for review_status in ["shortlist", "interview", "suitable", "not_suitable", "rejected"]:
            res = client.patch(
                f"/api/v1/jobs/{job_id}/applications/{app_id}",
                json={"review_status": review_status},
            )
            assert res.status_code == 200
            assert res.json()["review_status"] == review_status

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_patch_admin_notes(self, _, created_job, submitted_application):
        job_id = created_job["id"]
        app_id = submitted_application["application_id"]
        notes = "Very strong Python background. Recommend for technical interview."
        res = client.patch(
            f"/api/v1/jobs/{job_id}/applications/{app_id}",
            json={"admin_notes": notes},
        )
        assert res.status_code == 200
        assert res.json()["admin_notes"] == notes

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_patch_both_fields(self, _, created_job, submitted_application):
        job_id = created_job["id"]
        app_id = submitted_application["application_id"]
        res = client.patch(
            f"/api/v1/jobs/{job_id}/applications/{app_id}",
            json={"review_status": "shortlist", "admin_notes": "Top pick for final round."},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["review_status"] == "shortlist"
        assert data["admin_notes"] == "Top pick for final round."

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_patch_nonexistent_application(self, _, created_job):
        job_id = created_job["id"]
        res = client.patch(
            f"/api/v1/jobs/{job_id}/applications/9999999",
            json={"review_status": "shortlist"},
        )
        assert res.status_code == 404


# ──────────────────────────────────────────────
# STATS ENDPOINT TESTS
# ──────────────────────────────────────────────

class TestStats:

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_job_stats(self, _, created_job, submitted_application):
        job_id = created_job["id"]
        res = client.get(f"/api/v1/jobs/{job_id}/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["job_id"] == job_id
        assert data["total_applications"] >= 1
        assert "submitted" in data
        assert "ai_reviewed" in data
        assert "review_new" in data
        assert "review_shortlist" in data

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_stats_nonexistent_job(self, _):
        res = client.get("/api/v1/jobs/9999999/stats")
        assert res.status_code == 404


# ──────────────────────────────────────────────
# MANUAL EVALUATE ENDPOINT TESTS
# ──────────────────────────────────────────────

class TestManualEvaluate:

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_manual_evaluate(self, _, created_job, submitted_application):
        job_id = created_job["id"]
        app_id = submitted_application["application_id"]
        res = client.post(f"/api/v1/jobs/{job_id}/applications/{app_id}/evaluate")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ai_reviewed"
        assert data["ai_score"] is not None
        assert isinstance(data["ai_score"], int)
        assert 0 <= data["ai_score"] <= 100
        assert data["ai_fit_status"] is not None
        assert data["ai_evaluation"] is not None

    @patch("app.services.gemini_service._get_api_key", return_value=None)
    def test_manual_evaluate_nonexistent(self, _, created_job):
        job_id = created_job["id"]
        res = client.post(f"/api/v1/jobs/{job_id}/applications/9999999/evaluate")
        assert res.status_code == 404


# ──────────────────────────────────────────────
# END-TO-END FLOW TEST
# ──────────────────────────────────────────────

@patch("app.services.gemini_service._get_api_key", return_value=None)
def test_full_e2e_flow(mock_key):
    """
    Full flow: create job → candidate applies → verify AI scored →
    admin shortlists → admin adds notes → manual re-evaluate → delete job.
    """
    # 1. Create job
    res = client.post("/api/v1/jobs", json={
        "title": "E2E Test Job",
        "department": "QA",
        "description": "End-to-end test position requiring Python and Docker skills.",
        "requirements": "Python, Docker, 1 year experience.",
        "status": "active",
    })
    assert res.status_code == 201
    job = res.json()
    job_id = job["id"]

    # 2. Candidate applies
    files = {"cv_file": ("e2e_cv.txt", SAMPLE_CV_CONTENT, "text/plain")}
    form  = {"full_name": "E2E Candidate", "email": "e2e@test.com", "phone": "0900000000"}
    res = client.post(f"/api/v1/jobs/{job_id}/apply", data=form, files=files)
    assert res.status_code == 201
    app_id = res.json()["application_id"]

    # 3. Verify application was AI scored (background task runs in separate thread)
    import time
    app_data = {}
    for _ in range(50):
        res = client.get(f"/api/v1/jobs/{job_id}/applications/{app_id}")
        assert res.status_code == 200
        app_data = res.json()
        if app_data["status"] == "ai_reviewed":
            break
        time.sleep(0.1)
        
    assert app_data["status"] == "ai_reviewed"
    assert app_data["ai_score"] is not None
    assert isinstance(app_data["ai_evaluation"], dict)
    assert "total_score" in app_data["ai_evaluation"]
    assert "pros" in app_data["ai_evaluation"]
    assert "cons" in app_data["ai_evaluation"]

    # 4. Admin shortlists candidate
    res = client.patch(f"/api/v1/jobs/{job_id}/applications/{app_id}", json={
        "review_status": "shortlist",
        "admin_notes": "Strong Python profile, proceed to technical round.",
    })
    assert res.status_code == 200
    assert res.json()["review_status"] == "shortlist"

    # 5. Check stats
    res = client.get(f"/api/v1/jobs/{job_id}/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_applications"] == 1
    assert stats["review_shortlist"] == 1

    # 6. Manual AI re-evaluate
    res = client.post(f"/api/v1/jobs/{job_id}/applications/{app_id}/evaluate")
    assert res.status_code == 200
    re_eval = res.json()
    assert re_eval["ai_score"] is not None

    # 7. Delete job (cascades applications)
    res = client.delete(f"/api/v1/jobs/{job_id}")
    assert res.status_code == 200
    assert client.get(f"/api/v1/jobs/{job_id}").status_code == 404
