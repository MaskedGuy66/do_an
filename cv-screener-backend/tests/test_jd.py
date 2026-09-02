"""test_jd.py - Tests cho Job Description management APIs.

JDIngestRequest schema: {"title": str, "raw_text": str}
GET /api/v1/jd/  -> trả về {"total": int, "data": [...]}
"""


def _ingest_jd(client, title="Test JD", raw_text="Python developer needed. FastAPI, SQL required."):
    return client.post(
        "/api/v1/jd/ingest",
        json={"title": title, "raw_text": raw_text},
    )


def test_ingest_jd_text_success(client):
    res = _ingest_jd(client, title="Backend Engineer", raw_text="Need Python developer with 3 years FastAPI experience.")
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["message"] == "Xử lý và lưu Job Description thành công!"
    assert "jd_id" in data
    assert data["title"] == "Backend Engineer"


def test_ingest_jd_empty_title(client):
    res = client.post("/api/v1/jd/ingest", json={"title": "", "raw_text": "Some job description"})
    assert res.status_code == 400
    assert "trống" in res.json()["detail"]


def test_ingest_jd_empty_raw_text(client):
    res = client.post("/api/v1/jd/ingest", json={"title": "Valid Title", "raw_text": ""})
    assert res.status_code == 400
    assert "trống" in res.json()["detail"]


def test_ingest_jd_missing_fields(client):
    # Missing raw_text entirely -> Pydantic validation
    res = client.post("/api/v1/jd/ingest", json={"title": "No raw text"})
    assert res.status_code == 422


def test_list_jds(client):
    # Ensure at least 1 JD exists
    _ingest_jd(client, title="List Test JD")
    
    res = client.get("/api/v1/jd/")
    assert res.status_code == 200
    data = res.json()
    # API returns paginated dict
    assert "data" in data
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["data"]) >= 1
    assert "id" in data["data"][0]
    assert "title" in data["data"][0]


def test_get_jd_detail(client):
    create_res = _ingest_jd(client, title="Detail JD")
    jd_id = create_res.json()["jd_id"]
    
    res = client.get(f"/api/v1/jd/{jd_id}")
    assert res.status_code == 200
    assert res.json()["title"] == "Detail JD"
    assert res.json()["id"] == jd_id


def test_get_jd_detail_not_found(client):
    res = client.get("/api/v1/jd/999999")
    assert res.status_code == 404


def test_delete_jd(client):
    create_res = _ingest_jd(client, title="Delete Me JD")
    jd_id = create_res.json()["jd_id"]
    
    del_res = client.delete(f"/api/v1/jd/{jd_id}")
    assert del_res.status_code == 200
    
    get_res = client.get(f"/api/v1/jd/{jd_id}")
    assert get_res.status_code == 404
