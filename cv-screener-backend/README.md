# CV Screener & Evaluator Backend (Job Portal API)

Hệ thống API backend cho ứng dụng Tuyển Dụng Thông Minh (Smart Job Portal) với khả năng tự động trích xuất tiêu chí từ Job Description (JD) và tự động chấm điểm hồ sơ (CV) bằng **Google Gemini AI**.

## 🎯 1. Tổng Quan Dự Án

Dự án này cung cấp nền tảng toàn diện để:
- **Nhà tuyển dụng (Admin):** Quản lý tin tuyển dụng, xem danh sách ứng viên, cấu hình điểm chuẩn tự động, và theo dõi báo cáo phân tích hiệu suất tuyển dụng.
- **Ứng viên (Candidate):** Xem danh sách việc làm, tìm kiếm việc làm phù hợp, và nộp hồ sơ (CV) một cách dễ dàng.
- **AI Core (Gemini):** Tự động số hóa JD, OCR đọc nội dung CV (PDF/DOCX/Ảnh), so sánh đối chiếu đa chiều (Kỹ năng, Kinh nghiệm, Học vấn) và đưa ra gợi ý (Phù hợp/Tiềm năng/Loại).

**Mục tiêu cốt lõi:**
- Giảm 80% thời gian sàng lọc hồ sơ thủ công của HR.
- Xây dựng quy trình tuyển dụng chuẩn hóa, khách quan và minh bạch nhờ sự trợ giúp của AI.

## 🛠️ 2. Công Nghệ Sử Dụng (Tech Stack)

- **Framework:** `FastAPI` (Python 3.12+) — Tốc độ cao, hỗ trợ bất đồng bộ (async).
- **Database:** `SQLite` + `SQLAlchemy 2.0` (ORM) — Lưu trữ dữ liệu an toàn, dễ triển khai.
- **Data Validation:** `Pydantic v2` — Định nghĩa schema mạnh mẽ.
- **AI/LLM:** `google-genai` (Gemini 1.5 Flash) — Lõi trí tuệ nhân tạo.
- **Background Processing:** `Threading` — Xử lý AI ngầm, không gây nghẽn API.
- **Testing:** `pytest`, `TestClient` — Bộ test suite cô lập (35/35 PASSED).

## 🗂️ 3. Kiến Trúc Dữ Liệu (Core Models)

Hệ thống được thiết kế xoay quanh 4 thực thể chính:

1. **JobPosting (Tin Tuyển Dụng):** Tiêu đề, phòng ban, địa điểm, JD chi tiết, requirements, và trạng thái (active/closed).
2. **JobApplication (Hồ Sơ Ứng Tuyển):** Chứa thông tin ứng viên, file CV gốc, điểm số AI (`ai_score`), đánh giá AI (`ai_evaluation`), và trạng thái quy trình review.
3. **JobDescription (Legacy - JD Thô):** Dữ liệu JD được ingest từ ảnh/file, chứa `extracted_criteria` (kỹ năng bắt buộc, kinh nghiệm tối thiểu).
4. **CandidateCV (Legacy - CV Thô):** Dữ liệu text bóc tách từ file CV ứng viên.

## 🚀 4. API Endpoints Chính

Hệ thống chia làm 3 phân hệ router độc lập, bảo mật qua `X-Admin-Key`:

### 🧑‍💼 Job Portal (Dành cho Ứng viên & HR)
- `POST /api/v1/jobs` - Đăng tin tuyển dụng (Admin).
- `GET /api/v1/jobs` - Lọc và tìm kiếm việc làm (Public).
- `POST /api/v1/jobs/{id}/apply` - Nộp CV ứng tuyển (Public).
- `GET /api/v1/jobs/{id}/applications` - Quản lý hồ sơ ứng viên (Admin).
- `PATCH /api/v1/jobs/{id}/applications/{app_id}` - Đánh giá, đổi trạng thái ứng viên (Admin).
- `GET /api/v1/jobs/analytics/summary` - Dashboard thống kê tỷ lệ chuyển đổi, tỷ lệ pass (Admin).

### 🤖 AI Matching & Ingest
- `POST /api/v1/jd/ingest-file` - Upload file JD để trích xuất tiêu chí.
- `POST /api/v1/jd/ingest-image` - Dùng Gemini Vision OCR đọc ảnh chụp JD.
- `POST /api/v1/jobs/{id}/applications/{app_id}/evaluate` - Trigger AI đánh giá lại ứng viên.

## 🏗️ 5. Hướng Dẫn Cài Đặt (Setup Guide)

### 5.1 Yêu Cầu Hệ Thống
- Python >= 3.12
- Trình quản lý package `poetry`
- Google Gemini API Key

### 5.2 Khởi Tạo Dự Án
```powershell
# 1. Clone repository & vào thư mục dự án
cd cv-screener-backend

# 2. Tạo biến môi trường từ template
cp .env.example .env
# Mở file .env và nhập GEMINI_API_KEY, ADMIN_API_KEY

# 3. Cài đặt toàn bộ dependencies (Virtual Environment)
poetry install
```

### 5.3 Chạy Ứng Dụng (Development)
```powershell
poetry run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
- API Docs (Swagger): `http://localhost:8000/docs`
- Candidate Portal: `http://localhost:8000/ui`
- Admin Dashboard: `http://localhost:8000/ui/admin`

### 5.4 Chạy Kiểm Thử (Testing)
Hệ thống sử dụng cơ sở dữ liệu test riêng biệt (`test_run.db`) đảm bảo không ảnh hưởng dữ liệu thật.
```powershell
poetry run pytest -v
```

## 🔒 6. Cấu Hình Bảo Mật (Security)
- Toàn bộ endpoint dành cho nhà tuyển dụng (CRUD Jobs, duyệt CV) được bảo vệ qua Dependency `require_admin`.
- Client (Frontend/Postman) phải gửi Header: `X-Admin-Key: <Giá trị trong .env>`.
- Nếu `.env` không chứa key, hệ thống tự động cảnh báo và chuyển sang "Dev Mode" (Cho phép đi qua).

## 📋 7. Xem Báo Cáo Chất Lượng
Vui lòng tham khảo file `review_report.md` ở thư mục gốc để xem chi tiết về độ phủ test (Coverage), kiến trúc AI, và đánh giá chất lượng mã nguồn cuối cùng của hệ thống.
