"""
test_applications.py - Tests cho Job Application flow và Analytics.

Lưu ý:
  - run_scoring_in_thread được patch chạy đồng bộ (sync) trong conftest.py
    -> Đảm bảo AI scoring hoàn tất TRƯỚC KHI test kiểm tra kết quả.
  - Dùng SAMPLE_CV_CONTENT đủ dài (>50 chars) để vượt min-text validation.
"""

SAMPLE_CV_CONTENT = (
    "Nguyen Van A - Software Engineer. "
    "5 years of experience with Python, FastAPI, Django, PostgreSQL, Docker, Redis. "
    "Bachelor of Computer Science. Hanoi University of Technology."
).encode("utf-8")

SHORT_CV_CONTENT = b"Too short."


def _submit_application(client, job_id, name="Test Candidate", content=None):
    """Helper to submit a job application."""
    if content is None:
        content = SAMPLE_CV_CONTENT
    files = {"cv_file": ("cv.txt", content, "text/plain")}
    form = {
        "full_name": name,
        "email": f"{name.replace(' ', '.')}@test.com",
        "phone": "0123456789",
        "cover_letter": "I am very interested in this position.",
    }
    return client.post(f"/api/v1/jobs/{job_id}/apply", data=form, files=files)


# ─── Apply Tests ───────────────────────────────────────────────────────────────

def test_apply_job_success(client, sample_job):
    res = _submit_application(client, sample_job["id"])
    assert res.status_code == 201, res.text
    data = res.json()
    assert "application_id" in data
    assert data["status"] == "submitted"
    assert "AI" in data["message"]


def test_apply_invalid_extension(client, sample_job):
    files = {"cv_file": ("malware.exe", b"bad content", "application/octet-stream")}
    form = {
        "full_name": "Hacker",
        "email": "hack@example.com",
        "phone": "0000000000",
    }
    res = client.post(f"/api/v1/jobs/{sample_job['id']}/apply", data=form, files=files)
    assert res.status_code == 400
    assert "Định dạng file CV không hỗ trợ" in res.json()["detail"]


def test_apply_cv_too_short(client, sample_job):
    res = _submit_application(client, sample_job["id"], content=SHORT_CV_CONTENT)
    assert res.status_code == 422


def test_apply_job_not_found(client):
    res = _submit_application(client, 999999)
    assert res.status_code == 404


# ─── List / Detail Tests ───────────────────────────────────────────────────────

def test_list_applications(client, sample_job, admin_headers):
    # Ensure at least 1 application exists
    _submit_application(client, sample_job["id"], name="List Test Candidate")
    
    res = client.get(f"/api/v1/jobs/{sample_job['id']}/applications", headers=admin_headers)
    assert res.status_code == 200
    apps = res.json()
    assert isinstance(apps, list)
    assert len(apps) >= 1
    # Validate structure
    first = apps[0]
    assert "id" in first
    assert "full_name" in first
    assert "status" in first


def test_get_application_detail(client, sample_job, admin_headers):
    submit_res = _submit_application(client, sample_job["id"], name="Detail Candidate")
    assert submit_res.status_code == 201
    app_id = submit_res.json()["application_id"]

    res = client.get(f"/api/v1/jobs/{sample_job['id']}/applications/{app_id}", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == app_id
    assert data["full_name"] == "Detail Candidate"
    # With sync scoring mock, status should be ai_reviewed
    assert data["status"] == "ai_reviewed"
    assert data["ai_score"] is not None


def test_get_application_not_found(client, sample_job, admin_headers):
    res = client.get(f"/api/v1/jobs/{sample_job['id']}/applications/999999", headers=admin_headers)
    assert res.status_code == 404


# ─── Admin Review Tests ────────────────────────────────────────────────────────

def test_review_application_shortlist(client, sample_job, admin_headers):
    submit_res = _submit_application(client, sample_job["id"], name="Shortlist Candidate")
    app_id = submit_res.json()["application_id"]

    patch_res = client.patch(
        f"/api/v1/jobs/{sample_job['id']}/applications/{app_id}",
        json={"review_status": "shortlist", "admin_notes": "Strong Python background"},
        headers=admin_headers,
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["review_status"] == "shortlist"
    assert data["admin_notes"] == "Strong Python background"


def test_review_application_rejected(client, sample_job, admin_headers):
    submit_res = _submit_application(client, sample_job["id"], name="Rejected Candidate")
    app_id = submit_res.json()["application_id"]

    patch_res = client.patch(
        f"/api/v1/jobs/{sample_job['id']}/applications/{app_id}",
        json={"review_status": "rejected", "admin_notes": "Not enough experience"},
        headers=admin_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["review_status"] == "rejected"


def test_manual_evaluate(client, sample_job, admin_headers):
    # Submit and get application that has been scored already
    submit_res = _submit_application(client, sample_job["id"], name="Manual Eval Candidate")
    app_id = submit_res.json()["application_id"]

    eval_res = client.post(
        f"/api/v1/jobs/{sample_job['id']}/applications/{app_id}/evaluate",
        headers=admin_headers,
    )
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert "message" in data


# ─── Analytics Tests ───────────────────────────────────────────────────────────

def test_job_stats(client, sample_job, admin_headers):
    res = client.get(f"/api/v1/jobs/{sample_job['id']}/stats", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_applications" in data
    assert "pass_count" in data
    assert "failed_count" in data
    assert "views_count" in data
    assert data["total_applications"] >= 1


def test_analytics_summary(client, admin_headers):
    res = client.get("/api/v1/jobs/analytics/summary", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_views" in data
    assert "total_applications" in data
    assert "total_pass" in data
    assert "total_failed" in data
    assert "jobs" in data
    assert isinstance(data["jobs"], list)
