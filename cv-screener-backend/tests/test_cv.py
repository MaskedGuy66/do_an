"""
test_cv.py - Tests cho Legacy CV Screener APIs.

Endpoints:
  POST /api/v1/cv/upload          field: "file"
  GET  /api/v1/cv/               -> {"total": int, "skip": int, "limit": int, "data": [...]}
  GET  /api/v1/cv/{cv_id}
  DELETE /api/v1/cv/{cv_id}
  POST /api/v1/cv/{cv_id}/evaluate/{jd_id}  -> {"score": int, ...}
"""

LONG_CV_TEXT = (
    "Le Thi B - Senior Python Developer. "
    "Over 5 years of hands-on experience with Python, FastAPI, Django, PostgreSQL, Redis, Docker. "
    "Strong background in REST API design, microservices, and CI/CD pipelines. "
    "Bachelor in Computer Science, Hanoi University of Technology."
).encode("utf-8")


def test_upload_cv_success(client):
    files = {"file": ("cv_test.txt", LONG_CV_TEXT, "text/plain")}
    res = client.post("/api/v1/cv/upload", files=files)
    assert res.status_code == 201, res.text
    data = res.json()
    assert "cv_id" in data
    assert data["status"] == "PENDING"


def test_upload_cv_invalid_extension(client):
    files = {"file": ("bad.exe", LONG_CV_TEXT, "application/octet-stream")}
    res = client.post("/api/v1/cv/upload", files=files)
    assert res.status_code == 400


def test_upload_cv_empty_file(client):
    files = {"file": ("empty.txt", b"", "text/plain")}
    res = client.post("/api/v1/cv/upload", files=files)
    assert res.status_code == 400


def test_list_cvs(client):
    # Ensure at least 1 CV exists
    client.post("/api/v1/cv/upload", files={"file": ("list_test.txt", LONG_CV_TEXT, "text/plain")})
    
    res = client.get("/api/v1/cv/")
    assert res.status_code == 200
    data = res.json()
    # API returns paginated dict
    assert "total" in data
    assert "data" in data
    assert data["total"] >= 1
    assert len(data["data"]) >= 1


def test_get_cv_detail(client):
    upload_res = client.post("/api/v1/cv/upload", files={"file": ("cv_detail.txt", LONG_CV_TEXT, "text/plain")})
    assert upload_res.status_code == 201
    cv_id = upload_res.json()["cv_id"]
    
    res = client.get(f"/api/v1/cv/{cv_id}")
    assert res.status_code == 200
    assert res.json()["id"] == cv_id


def test_get_cv_detail_not_found(client):
    res = client.get("/api/v1/cv/999999")
    assert res.status_code == 404


def test_delete_cv(client):
    upload_res = client.post("/api/v1/cv/upload", files={"file": ("cv_delete.txt", LONG_CV_TEXT, "text/plain")})
    cv_id = upload_res.json()["cv_id"]
    
    del_res = client.delete(f"/api/v1/cv/{cv_id}")
    assert del_res.status_code == 200
    
    get_res = client.get(f"/api/v1/cv/{cv_id}")
    assert get_res.status_code == 404


def test_evaluate_cv(client):
    # 1. Upload CV
    upload_res = client.post("/api/v1/cv/upload", files={"file": ("cv_eval.txt", LONG_CV_TEXT, "text/plain")})
    assert upload_res.status_code == 201
    cv_id = upload_res.json()["cv_id"]
    
    # 2. Ingest JD
    jd_res = client.post(
        "/api/v1/jd/ingest",
        json={"title": "Python Dev", "raw_text": "Need Python developer with FastAPI and PostgreSQL experience."},
    )
    assert jd_res.status_code == 201
    jd_id = jd_res.json()["jd_id"]
    
    # 3. Evaluate
    eval_res = client.post(f"/api/v1/cv/{cv_id}/evaluate/{jd_id}")
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert "score" in data
    assert "fit_status" in data
    assert isinstance(data["score"], int)
