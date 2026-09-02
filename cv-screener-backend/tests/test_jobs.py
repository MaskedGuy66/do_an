"""test_jobs.py - Tests cho JobPosting CRUD APIs."""


def test_create_job_success(client, admin_headers):
    payload = {
        "title": "Data Engineer",
        "department": "Data",
        "location": "HCMC",
        "job_type": "Full-time",
        "description": "Build data pipelines.",
        "requirements": "Python, SQL",
        "status": "active",
    }
    res = client.post("/api/v1/jobs", json=payload, headers=admin_headers)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["title"] == payload["title"]
    assert data["department"] == payload["department"]
    assert "id" in data
    assert "created_at" in data


def test_list_jobs_returns_list(client, sample_job):
    res = client.get("/api/v1/jobs")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(job["id"] == sample_job["id"] for job in data)


def test_get_job_detail(client, sample_job):
    res = client.get(f"/api/v1/jobs/{sample_job['id']}")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == sample_job["title"]
    assert data["id"] == sample_job["id"]


def test_get_job_not_found(client):
    res = client.get("/api/v1/jobs/999999")
    assert res.status_code == 404


def test_update_job(client, sample_job, admin_headers):
    payload = {"status": "closed"}
    res = client.put(f"/api/v1/jobs/{sample_job['id']}", json=payload, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "closed"


def test_increment_job_view(client, sample_job):
    # Get current view count
    initial_res = client.get(f"/api/v1/jobs/{sample_job['id']}")
    initial_views = initial_res.json().get("views_count", 0) or 0

    view_res = client.post(f"/api/v1/jobs/{sample_job['id']}/view")
    assert view_res.status_code == 200
    assert view_res.json()["views_count"] == initial_views + 1


def test_delete_job(client, admin_headers):
    # Create a temporary job to delete
    create_res = client.post(
        "/api/v1/jobs",
        json={"title": "To Be Deleted", "description": "Temp"},
        headers=admin_headers,
    )
    assert create_res.status_code == 201
    job_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/jobs/{job_id}", headers=admin_headers)
    assert del_res.status_code == 200

    get_res = client.get(f"/api/v1/jobs/{job_id}")
    assert get_res.status_code == 404
