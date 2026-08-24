# CV Screener & Evaluator Backend

Backend API cho hệ thống tự động lọc, trích xuất tiêu chí từ Job Description và chấm điểm CV bằng Gemini AI.

## 1. Tổng quan dự án

Dự án này là một backend FastAPI dùng để:

- nhận JD từ text hoặc file ảnh
- trích xuất tiêu chí tuyển dụng bằng Gemini
- nhận CV từ PDF / DOCX / TXT / ảnh
- trích xuất nội dung CV và làm sạch văn bản
- so sánh CV với JD theo tiêu chí kỹ năng, kinh nghiệm, học vấn và trách nhiệm
- trả về điểm số và trạng thái phù hợp: Phù hợp / Tiềm năng / Loại
- lưu dữ liệu vào SQLite để tiếp tục đánh giá hoặc dùng trong dashboard sau này

Mục tiêu kinh doanh:

- giảm thời gian lọc CV thủ công
- đánh giá ứng viên theo một tiêu chí chuẩn hóa
- giúp recruiter xem trước ranking ứng viên theo độ phù hợp với vị trí

## 2. Công nghệ sử dụng

- FastAPI
- SQLAlchemy + SQLite
- Pydantic v2
- Google Gemini API via `google-genai`
- pypdf để đọc PDF
- python-multipart cho upload file
- FPDF để tạo file test CV

## 3. Kiến trúc hệ thống

### 3.1 Mô hình product flow

1. HR upload hoặc nhập JD
2. Gemini trích xuất cấu trúc JD thành JSON schema
3. HR upload CV (PDF / DOCX / TXT / ảnh)
4. Hệ thống trích xuất text từ file
5. Gemini đánh giá CV so với JD
6. Lưu score và review vào database
7. Có thể gọi API ranking toàn bộ CV theo một JD nhất định

### 3.2 Cấu trúc thư mục chính

- `main.py` - khởi tạo ứng dụng FastAPI và đăng ký router
- `app/database.py` - engine và Base SQLAlchemy
- `app/models.py` - model `CandidateCV`, `JobDescription`, `JobPosting`, `JobApplication`
- `app/schemas.py` - schema request/response Pydantic cho cả CV Screener và Job Portal
- `app/routers/cv.py` - CRUD CV và đánh giá CV đơn lẻ
- `app/routers/jd.py` - ingest JD từ text/file/ảnh
- `app/routers/jobs.py` - quản lý tin tuyển dụng và nộp hồ sơ ứng viên (Job Portal)
- `app/services/gemini_service.py` - AI extraction + evaluation logic
- `app/services/pdf_service.py` - đọc PDF/DOCX/TXT
- `frontend/index.html` - Dashboard ứng tuyển và tuyển dụng (Candidate & Recruiter Views)
- `uploads/` - thư mục lưu file upload
- `cv_screener.db` - database SQLite

## 4. Dữ liệu chính trong hệ thống

### 4.1 Model `JobDescription`
Lưu thông tin mô tả công việc tuyển dụng thô:
- `id`
- `title`
- `raw_text`
- `image_path`
- `extracted_criteria` (JSON)

### 4.2 Model `CandidateCV`
Lưu hồ sơ ứng viên dạng thô:
- `id`, `candidate_name`, `email`, `phone`, `file_path`, `status`, `cleaned_text`, `total_score`, `evaluation_details` (JSON), `is_anonymous`

### 4.3 Model `JobPosting` (Mới)
Lưu thông tin các tin tuyển dụng chính thức trên Portal:
- `id`: Khóa chính
- `title`: Tiêu đề vị trí (ví dụ: Python Developer)
- `department`: Phòng ban (ví dụ: Technology)
- `location`: Địa điểm làm việc
- `job_type`: Hình thức làm việc (Full-time, Part-time,...)
- `description`: Mô tả chi tiết
- `requirements`: Yêu cầu công việc
- `benefits`: Chế độ đãi ngộ
- `status`: Trạng thái (`active`, `closed`)
- `deadline`: Hạn nộp hồ sơ
- `created_at`, `updated_at`

### 4.4 Model `JobApplication` (Mới)
Lưu trữ hồ sơ ứng viên nộp cho tin tuyển dụng cụ thể:
- `id`: Khóa chính
- `job_id`: Khóa ngoại liên kết tới `JobPosting`
- `full_name`: Họ tên ứng viên
- `email`, `phone`: Thông tin liên hệ
- `cv_file_path`: Đường dẫn tới file CV được upload ở `uploads/`
- `cover_letter`: Thư giới thiệu (tùy chọn)
- `status`: Trạng thái hệ thống (`submitted`, `ai_reviewed`)
- `ai_score`: Điểm AI đánh giá độ khớp CV với JD (0-100)
- `ai_fit_status`: Phân loại của AI (`Phù hợp`, `Tiềm năng`, `Loại`)
- `ai_evaluation`: Kết quả phân tích chi tiết dạng JSON (pros, cons, skills_match, experience_match)
- `admin_notes`: Ghi chú nội bộ của nhà tuyển dụng
- `review_status`: Trạng thái tuyển dụng thủ công (`new`, `shortlist`, `interview`, `suitable`, `not suitable`, `rejected`)
- `created_at`, `updated_at`

---

## 5. Schema Pydantic quan trọng

### 5.1 Job Portal Schemas
- `JobPostingCreate` / `JobPostingUpdate` / `JobPostingResponse`: Quản lý dữ liệu tin tuyển dụng.
- `JobApplicationResponse`: Dữ liệu trả về thông tin ứng tuyển chi tiết.
- `JobApplicationAdminUpdate`: Dùng để Admin cập nhật ghi chú (`admin_notes`) và trạng thái tuyển dụng (`review_status`).

---

## 6. Luồng Xử Lý Job Portal
1. **Ứng tuyển**: Ứng viên truy cập Portal -> Chọn job -> Điền thông tin cá nhân và upload file CV -> API lưu file và tạo record ở trạng thái `submitted`.
2. **Đánh giá tự động**: Hệ thống trích xuất văn bản từ CV -> Gộp description và requirements của JD để Gemini trích xuất tiêu chí -> Chạy Gemini đánh giá CV theo JD -> Lưu điểm số, trạng thái match, danh sách ưu nhược điểm -> Cập nhật trạng thái application sang `ai_reviewed`.
3. **Tuyển dụng thủ công**: Nhà tuyển dụng vào Admin Portal -> Xem danh sách ứng viên theo tin tuyển dụng (không có ranking tự động, lọc thủ công theo trạng thái và thời gian nộp) -> Xem chi tiết phân tích AI, CV gốc -> Cập nhật trạng thái và ghi chú thủ công.

---

## 7. API Endpoints mới (Job Portal)

### 7.1 Tin tuyển dụng (Job Postings)
- `POST /api/v1/jobs` - Tạo mới tin tuyển dụng
- `GET /api/v1/jobs` - Lấy danh sách tin tuyển dụng
- `GET /api/v1/jobs/{id}` - Chi tiết tin tuyển dụng
- `PUT /api/v1/jobs/{id}` - Cập nhật tin tuyển dụng
- `DELETE /api/v1/jobs/{id}` - Xóa tin tuyển dụng

### 7.2 Hồ sơ ứng tuyển (Job Applications)
- `POST /api/v1/jobs/{job_id}/apply` - Nộp hồ sơ ứng tuyển (multipart form-data gồm thông tin cá nhân + file CV)
- `GET /api/v1/jobs/{job_id}/applications` - Xem danh sách hồ sơ ứng tuyển theo Job
- `GET /api/v1/jobs/{job_id}/applications/{application_id}` - Chi tiết hồ sơ ứng tuyển của ứng viên
- `PATCH /api/v1/jobs/{job_id}/applications/{application_id}` - Nhà tuyển dụng cập nhật trạng thái tuyển dụng & ghi chú
- `POST /api/v1/jobs/{job_id}/applications/{application_id}/evaluate` - Kích hoạt AI đánh giá lại thủ công

---

## 8. Giao diện Website (Frontend Dashboard)
Hệ thống cung cấp một trang giao diện trực quan và cao cấp tại `/ui/` với 2 phân hệ:
1. **Portal Ứng viên (Candidate View)**:
   - Hiển thị danh sách các job đang tuyển dụng kèm theo hình thức, hạn nộp, và phòng ban.
   - Form nộp CV kèm kéo thả file nhanh chóng, tiện lợi.
2. **Portal Tuyển dụng (Recruiter View)**:
   - Đăng tin tuyển dụng mới.
   - Quản lý danh sách ứng tuyển cho từng bài tuyển dụng cụ thể.
   - Giao diện hai cột xem thông tin ứng viên, xem file CV gốc, hiển thị vòng tròn điểm AI, chi tiết ưu điểm, nhược điểm, bảng đối chiếu kỹ năng (Skills Match), và form cập nhật trạng thái/notes nhanh.

---

## 9. Cài đặt và Chạy thử

### Cài đặt Dependency
```powershell
poetry install
```

### Thiết lập API Key
```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

### Chạy hệ thống
```powershell
poetry run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Truy cập giao diện Web Portal tại: **`http://127.0.0.1:8000/ui/`**

### Chạy Test Suite
Hệ thống tích hợp bộ kiểm thử tự động toàn diện:
```powershell
poetry run pytest
```

## 10. Môi trường và setup

### Yêu cầu

- Python >= 3.12
- Poetry
- Internet để gọi Gemini

### Cài đặt dependency

```powershell
poetry install
```

### Thiết lập API key

```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

Hoặc:

```powershell
$env:GOOGLE_API_KEY="your_api_key_here"
```

### Chạy backend

```powershell
poetry run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Truy cập:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

## 11. Test và validation

### Test tự động

```powershell
poetry run pytest -q
```

### Test thủ công

```powershell
poetry run python create_test_cv.py
poetry run uvicorn main:app --reload
```

## 12. Lưu ý vận hành

- File upload được lưu trong `uploads/`
- Database SQLite được lưu tại `cv_screener.db`
- Nếu thiếu Gemini API key, hệ thống có fallback cho text JD nhưng không đủ chính xác đối với ảnh/vision
- Nếu file là ảnh scan không rõ nét, OCR có thể không trả về đủ text
- Hệ thống đang là phiên bản backend foundation, chưa có dashboard UI hoàn chỉnh

## 13. Hướng phát triển tiếp theo

- ChromaDB vector search cho CV chunks
- Đánh giá theo pipeline multi-stage: sơ lọt → ranking → shortlist
- Dashboard recruiter UI
- Lưu lịch sử đánh giá theo từng job opening
- Nâng cấp OCR cho PDF scan và hình ảnh chất lượng thấp
- Thêm Alembic migration

## 14. Prompt context để đưa cho chatbot khác

Nếu cần hỏi lại chatbot khác, bạn có thể paste đoạn dưới đây:

```text
Tôi đang làm project backend CV Screener & Evaluator với FastAPI. Hệ thống có các chức năng:
- nhận JD từ text hoặc file/ảnh
- trích xuất tiêu chí tuyển dụng bằng Gemini
- nhận CV từ PDF/DOCX/TXT/ảnh
- trích xuất text từ CV và đối chiếu với JD
- chấm điểm CV theo thang 100
- trả về status: Phù hợp / Tiềm năng / Loại
- lưu dữ liệu vào SQLite

Stack: FastAPI, SQLAlchemy, SQLite, Pydantic v2, google-genai, pypdf.

Main files:
- main.py
- app/models.py
- app/schemas.py
- app/routers/jd.py
- app/routers/cv.py
- app/services/gemini_service.py
- app/services/pdf_service.py

Core schema:
- JobDescription { id, title, raw_text, image_path, extracted_criteria }
- CandidateCV { id, candidate_name, email, phone, file_path, status, cleaned_text, total_score, evaluation_details, is_anonymous }
- JDCriteriaSchema { required_skills, preferred_skills, min_years_experience, education_requirement, key_responsibilities }
- CVEvaluationSchema { total_score, skills_match, experience_match, pros, cons, fit_status }

API endpoints:
- POST /api/v1/jd/ingest
- POST /api/v1/jd/ingest-file
- POST /api/v1/jd/ingest-image
- GET /api/v1/jd/
- GET /api/v1/jd/{jd_id}
- POST /api/v1/cv/upload
- GET /api/v1/cv/
- GET /api/v1/cv/{cv_id}
- POST /api/v1/cv/{cv_id}/evaluate/{jd_id}
- POST /api/v1/cv/match/{jd_id}

Goal: build recruiter-facing candidate matching pipeline using AI.

Important: when asking for improvement, keep in mind the current implementation uses Gemini structured output for JD extraction and evaluation, but still has no full dashboard/UI yet.
```

## 15. Tóm tắt gọn cho handoff

Project hiện tại là một backend matching CV-JD bằng AI, có thể chạy local, lưu database SQLite và xử lý cả JD/CV từ text và file/ảnh. Về mặt kỹ thuật, hệ thống đã có phần cốt lõi hoàn chỉnh để tiếp tục phát triển thêm UI, vector search, dashboard và pipeline tuyển dụng hoàn chỉnh.

