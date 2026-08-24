import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_analytics_and_job_views():
    # 1. Create a new test job
    job_payload = {
        "title": "Test Analytics Engineer",
        "department": "Data",
        "location": "Hà Nội",
        "job_type": "Full-time",
        "description": "Cần tuyển lập trình viên dữ liệu làm việc với Python và SQL.",
        "requirements": "Yêu cầu từ 2 năm kinh nghiệm.",
        "status": "active"
    }
    create_res = client.post("/api/v1/jobs", json=job_payload)
    assert create_res.status_code == 201, create_res.text
    job_data = create_res.json()
    job_id = job_data["id"]

    # 2. Record 5 views for this job link
    for _ in range(5):
        view_res = client.post(f"/api/v1/jobs/{job_id}/view")
        assert view_res.status_code == 200

    # Verify view count on job details
    get_job_res = client.get(f"/api/v1/jobs/{job_id}")
    assert get_job_res.status_code == 200
    assert get_job_res.json()["views_count"] >= 5

    # 3. Submit 2 applications
    dummy_cv = ("cv.txt", b"Test CV content with python developer background and 3 years experience.", "text/plain")
    
    app1_res = client.post(
        f"/api/v1/jobs/{job_id}/apply",
        data={"full_name": "Ứng viên Pass", "email": "pass@test.com", "phone": "0988888888"},
        files={"cv_file": dummy_cv}
    )
    assert app1_res.status_code == 201, app1_res.text
    app1_id = app1_res.json()["application_id"]

    app2_res = client.post(
        f"/api/v1/jobs/{job_id}/apply",
        data={"full_name": "Ứng viên Fail", "email": "fail@test.com", "phone": "0977777777"},
        files={"cv_file": dummy_cv}
    )
    assert app2_res.status_code == 201, app2_res.text
    app2_id = app2_res.json()["application_id"]

    # 4. Review applications: Mark app1 as shortlist (Pass) and app2 as rejected (Failed)
    rev1 = client.patch(
        f"/api/v1/jobs/{job_id}/applications/{app1_id}",
        json={"review_status": "shortlist", "admin_notes": "Đạt yêu cầu sơ tuyển"}
    )
    assert rev1.status_code == 200

    rev2 = client.patch(
        f"/api/v1/jobs/{job_id}/applications/{app2_id}",
        json={"review_status": "rejected", "admin_notes": "Chưa đủ kinh nghiệm"}
    )
    assert rev2.status_code == 200

    # 5. Call Job Stats API
    stats_res = client.get(f"/api/v1/jobs/{job_id}/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_applications"] >= 2
    assert stats["pass_count"] >= 1
    assert stats["failed_count"] >= 1
    assert stats["views_count"] >= 5

    # 6. Call Overall Analytics Summary API
    analytics_res = client.get("/api/v1/jobs/analytics/summary")
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()

    assert analytics["total_views"] >= 5
    assert analytics["total_applications"] >= 2
    assert analytics["total_pass"] >= 1
    assert analytics["total_failed"] >= 1
    assert analytics["overall_conversion_rate"] >= 0
    assert len(analytics["jobs"]) >= 1

    print("\n✅ [SUCCESS] Tất cả test analytics & job direct views đã PASS thành công!")

if __name__ == "__main__":
    test_analytics_and_job_views()
