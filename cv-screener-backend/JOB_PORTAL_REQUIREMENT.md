# JOB PORTAL

## 1. Mục tiêu dự án

Xây dựng hệ thống website tuyển dụng cho phép:

- Quản trị viên đăng tin tuyển dụng và mô tả công việc (JD).
- Người nộp đơn gửi hồ sơ qua form gồm: Họ tên, email, số điện thoại, file CV và cover letter (nếu có).
- Hệ thống trích xuất nội dung CV, so khớp với JD và chấm điểm mức độ phù hợp.
- Không xếp hạng hay hiển thị leaderboard cho ứng viên.
- Admin review hồ sơ một cách độc lập, tự lọc, sắp xếp và quyết định shortlist / interview / rejected theo đánh giá cá nhân.

---

## 2. Vai trò người dùng

### 2.1 Admin / Recruiter

- Tạo và quản lý bài tuyển dụng.
- Nhập tiêu đề vị trí, mô tả công việc, yêu cầu kỹ năng, địa điểm, loại hình tuyển dụng, hạn nộp.
- Xem danh sách ứng viên đã nộp cho từng vị trí.
- Xem chi tiết hồ sơ, file CV, điểm AI và đánh giá chi tiết.
- Lọc, sắp xếp hồ sơ theo trạng thái và thời gian nộp.
- Ghi chú admin và cập nhật quyết định cuối cùng.

### 2.2 Candidate / Người nộp đơn

- Chọn bài tuyển dụng.
- Điền thông tin cá nhân: Họ tên, email, số điện thoại.
- Tải lên file CV (PDF, DOCX, TXT, JPG/PNG).
- Gửi đơn ứng tuyển.
- Chờ admin xem xét và phản hồi.

---

## 3. Luồng nghiệp vụ chính

### 3.1 Giai đoạn 1: Người dùng tải file lên và lưu trữ dữ liệu

- Người nộp đơn truy cập trang chi tiết tin tuyển dụng.
- Điền form:
  - Họ tên
  - Email
  - Số điện thoại
  - File CV
  - Cover letter (tùy chọn)
- Hệ thống lưu file thực tế ở thư mục `uploads/` trên server.
- Dữ liệu ứng viên được lưu trong bảng `job_applications` bao gồm:
  - `full_name`
  - `email`
  - `phone`
  - `cv_file_path`
  - `cover_letter`
  - `status = submitted`

### 3.2 Giai đoạn 2: Đánh giá tự động bằng AI

Ngay sau khi submit thành công, hệ thống kích hoạt quy trình:

1. Trích xuất văn bản từ file CV.
2. Đọc và làm sạch dữ liệu hồ sơ.
3. So sánh CV với JD của bài tuyển dụng.
4. Chấm điểm trên thang 0–100.
5. Tạo JSON đánh giá chứa:
   - `total_score` / `ai_score`
   - `fit_status` như `Phù hợp`, `Tiềm năng`, `Loại`
   - `skills_match`
   - `experience_match`
   - `pros`
   - `cons`
   - `notes`
6. Lưu kết quả vào database và cập nhật trạng thái `ai_reviewed`.

### Tỷ trọng chấm điểm đề xuất

- Skills match: 40%
- Experience match: 25%
- Education / qualification: 15%
- Responsibilities fit: 20%

### Ví dụ kết quả AI

```json
{
  "total_score": 82,
  "fit_status": "Phù hợp",
  "skills_match": [
    { "skill": "Python", "detail": "Có kinh nghiệm xây dựng API bằng FastAPI" },
    { "skill": "SQL", "detail": "Có làm việc với PostgreSQL" }
  ],
  "experience_match": "Có hơn 3 năm kinh nghiệm backend và từng làm dự án doanh nghiệp.",
  "pros": ["Backend mạnh", "Có hiểu biết về API"],
  "cons": ["Thiếu một số kỹ năng cloud"],
  "notes": "Cần kiểm tra thêm trong vòng phỏng vấn"
}
```

### 3.3 Giai đoạn 3: Admin kiểm tra độc lập

Trang Admin cho phép:

- Xem danh sách hồ sơ theo từng bài tuyển dụng.
- Lọc hồ sơ ở trạng thái mới nộp (`submitted`) hoặc đã AI review (`ai_reviewed`).
- Sắp xếp và lọc theo ngày nộp, tênứng viên, trạng thái.
- Mở chi tiết từng ứng viên bằng dropdown/accordion.
- Xem file CV gốc và dữ liệu đánh giá AI.
- Quyết định thủ công: shortlist, rejected, interview, suitable, not suitable.
- Ghi chú `admin_notes` cho từng hồ sơ.

> Điểm quan trọng: không dùng chức năng xếp hạng tự động / leaderboard / score board / ranked candidates.

---

## 4. Quy định về điểm số và ranking

### 4.1 Điểm số chỉ là hỗ trợ

- Điểm AI không được dùng để xếp hạng toàn bộ ứng viên theo thứ tự và không hiển thị trên UI như bảng xếp hạng.
- Điểm số là công cụ hỗ trợ cho recruiter trong quá trình xem xét hồ sơ.
- Quyết định cuối cùng do admin thực hiện dựa trên kinh nghiệm và tiêu chí tuyển dụng thực tế.

### 4.2 Không dùng ranking

Các thành phần không được triển khai:

- `ranked_candidates`
- `score_board`
- `top_candidates`
- `leaderboard`

Thay vào đó, hệ thống phải hiển thị:

- danh sách hồ sơ ứng tuyển theo bài job
- trạng thái ứng viên
- điểm AI hỗ trợ
- bộ lọc và sắp xếp thủ công
- ghi chú của admin

---

## 5. Dữ liệu và mô hình lưu trữ

### 5.1 Bảng `job_postings`

```sql
CREATE TABLE job_postings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    department VARCHAR(255),
    location VARCHAR(255),
    job_type VARCHAR(50),
    description TEXT,
    requirements TEXT,
    benefits TEXT,
    status VARCHAR(50) DEFAULT 'active',
    deadline DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2 Bảng `job_applications`

```sql
CREATE TABLE job_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    full_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    cv_file_path VARCHAR(500),
    cover_letter TEXT,
    status VARCHAR(50) DEFAULT 'submitted',
    ai_score INTEGER,
    ai_fit_status VARCHAR(50),
    ai_evaluation JSON,
    admin_notes TEXT,
    review_status VARCHAR(50) DEFAULT 'new',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES job_postings(id)
);
```

### 5.3 Mô hình hiện có của dự án

Dự án hiện có đã có các thành phần phù hợp:

- `JobDescription` mô phỏng JD.
- `CandidateCV` lưu thông tin CV và điểm số.
- API chấm CV theo JD bằng AI.

Bằng vậy, cần bổ sung các model mới cho tuyển dụng website:

- `JobPosting`
- `JobApplication`

---

## 6. Công cụ, backend và công nghệ được ghi nhận

### 6.1 Cơ sở dữ liệu

- SQLite: lưu dữ liệu bài đăng và hồ sơ ứng viên.

### 6.2 Backend và API

- FastAPI: framework xây dựng API cho hệ thống.

### 6.3 AI processing

- Logic AI hiện có trong backend để:
  - trích xuất text từ CV
  - so khớp với JD
  - chấm điểm mức độ phù hợp

### 6.4 File storage

- Thư mục `uploads/` dùng để lưu file CV do người dùng upload.

### 6.5 Cấp độ nâng cao đề xuất

- Export CSV/Excel danh sách ứng viên.
- Hệ thống email thông báo trạng thái cho ứng viên.

---

## 7. Gợi ý API triển khai

### 7.1 Job posting

- `POST /api/v1/jobs`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{id}`
- `PUT /api/v1/jobs/{id}`
- `DELETE /api/v1/jobs/{id}`

### 7.2 Job application

- `POST /api/v1/jobs/{job_id}/apply`
- `GET /api/v1/jobs/{job_id}/applications`
- `GET /api/v1/jobs/{job_id}/applications/{application_id}`
- `PATCH /api/v1/jobs/{job_id}/applications/{application_id}`
- `POST /api/v1/jobs/{job_id}/applications/{application_id}/evaluate`

### 7.3 Response mẫu

```json
{
  "message": "Ứng viên đã nộp CV thành công",
  "application_id": 12,
  "job_id": 5,
  "status": "ai_reviewed",
  "ai_score": 84,
  "ai_fit_status": "Phù hợp"
}
```

---

## 8. Yêu cầu giao diện website

### 8.1 Trang danh sách tin tuyển dụng

- Hiển thị tiêu đề vị trí, mô tả ngắn, địa điểm, ngày đăng.
- Có nút "Apply Now" hoặc "Nộp đơn".

### 8.2 Trang chi tiết tin tuyển dụng

- Mô tả công việc.
- Yêu cầu kỹ năng và kinh nghiệm.
- Nút nộp đơn ứng tuyển.

### 8.3 Form ứng tuyển

- Họ tên
- Email
- Số điện thoại
- Upload CV
- Cover letter (tùy chọn)

### 8.4 Trang quản trị

- Danh sách bài đăng.
- Danh sách ứng viên theo từng job.
- Bộ lọc trạng thái.
- Xem chi tiết AI evaluation.
- Ghi chú admin.
- Sắp xếp và lọc thủ công.

---

## 9. Triển khai thực tế trong dự án hiện tại

### Nên làm theo thứ tự

1. Tạo model `JobPosting` và `JobApplication` trong [app/models.py](app/models.py).
2. Thêm schema trong [app/schemas.py](app/schemas.py).
3. Tạo router mới cho `jobs` và `applications`.
4. Gọi lại `gemini_service.evaluate_cv_against_jd` để đánh giá CV sau khi apply.
5. Thêm endpoint admin review để cập nhật trạng thái và ghi chú.
6. Chỉ dùng điểm AI như tham chiếu hỗ trợ, không tạo ranking.

### Luồng xử lý đúng thực tế

- Form apply -> lưu file -> lưu record -> status = `submitted`
- AI review -> chấm điểm + lưu `ai_evaluation` -> status = `ai_reviewed`
- Admin review -> xem file CV và JSON đánh giá -> quyết định shortlist / interview / rejected

---

## 10. Acceptance Criteria

### 10.1 Functional

- [ ] Admin có thể tạo mới bài tuyển dụng.
- [ ] Người dùng có thể nộp ứng tuyển qua form với đầy đủ thông tin.
- [ ] Hệ thống lưu trữ file CV trong `uploads/`.
- [ ] Hệ thống trích xuất text CV và so sánh với JD.
- [ ] Hệ thống chấm điểm độ phù hợp công việc.
- [ ] Không hiển thị ranking hoặc bảng xếp hạng.
- [ ] Admin có thể xem, lọc, sắp xếp và đánh giá hồ sơ thủ công.

### 10.2 Non-functional

- [ ] API xử lý nhiều ứng viên cùng lúc.
- [ ] Dữ liệu lưu trữ an toàn.
- [ ] Giao diện dễ dùng trên web.
- [ ] Admin có thể quyết định tự do dựa trên dữ liệu và đánh giá cá nhân.

---

## 11. Kết luận

Hệ thống nên tập trung vào workflow: "đăng tin tuyển dụng -> ứng viên nộp đơn -> AI đánh giá CV -> admin kiểm tra và quyết định thủ công". Trong mô hình này, điểm số chỉ là công cụ hỗ trợ, không phải yếu tố ranking. Điều này phù hợp với yêu cầu thực tế của doanh nghiệp và cho phép admin kiểm soát toàn bộ quy trình tuyển dụng một cách chủ động, khoa học và linh hoạt.

---

## 12. Tóm tắt ngắn gọn

- Người nộp đơn điền form và upload CV.
- File CV được lưu ở `uploads/`.
- AI đánh giá CV theo JD.
- Dữ liệu điểm và JSON đánh giá được lưu vào DB.
- Admin xem hồ sơ, lọc/sắp xếp thủ công và quyết định cuối cùng.
- Không ranking.
- Hệ thống này là nền tảng phù hợp để phát triển website tuyển dụng thực tế.
