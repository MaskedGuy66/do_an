from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

# Schema bóc tách tiêu chí chi tiết từ JD
class JDCriteriaSchema(BaseModel):
    required_skills: List[str] = Field(default=[], description="Danh sách các kỹ năng kỹ thuật, công nghệ bắt buộc phải có.")
    preferred_skills: List[str] = Field(default=[], description="Các kỹ năng cộng điểm, ưu tiên (không bắt buộc).")
    min_years_experience: int = Field(default=0, description="Số năm kinh nghiệm tối thiểu yêu cầu. Nếu không đề cập, mặc định là 0.")
    education_requirement: Optional[str] = Field(None, description="Yêu cầu bằng cấp hoặc học vấn (ví dụ: Đại học chuyên ngành CNTT).")
    key_responsibilities: List[str] = Field(default=[], description="Tóm tắt các nhiệm vụ/trách nhiệm chính trong công việc.")

# Schema dùng cho API Request gửi lên từ Client
class JDIngestRequest(BaseModel):
    title: str = Field(..., example="Python Backend Engineer")
    raw_text: str = Field(..., example="Tuyển dụng lập trình viên Python từ 2 năm kinh nghiệm, thành thạo FastAPI...")

class SkillMatchItem(BaseModel):
    skill: str = Field(..., description="Tên kỹ năng hoặc công nghệ.")
    detail: str = Field(..., description="Mô tả mức độ phù hợp của kỹ năng đó trong CV.")

class CVEvaluationSchema(BaseModel):
    total_score: int = Field(..., description="Điểm tổng thể của ứng viên dựa trên độ phù hợp với JD (Thang điểm 100).")
    skills_match: List[SkillMatchItem] = Field(..., description="Đánh giá chi tiết từng kỹ năng yêu cầu đối chiếu với CV.")
    experience_match: str = Field(..., description="Đánh giá về số năm kinh nghiệm, các dự án liên quan của ứng viên so với yêu cầu.")
    pros: List[str] = Field(..., description="Danh sách các điểm mạnh nổi bật của ứng viên.")
    cons: List[str] = Field(..., description="Danh sách các điểm yếu hoặc lỗ hổng kiến thức cần lưu ý.")
    fit_status: str = Field(..., description="Gợi ý phân loại: 'Phù hợp' (Sắp xếp phỏng vấn), 'Tiềm năng' (Vòng cân nhắc), hoặc 'Loại'.")

# --- Job Portal Schemas ---

class JobPostingBase(BaseModel):
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    status: Optional[str] = "active"
    views_count: Optional[int] = 0
    deadline: Optional[datetime] = None

class JobPostingCreate(JobPostingBase):
    pass

class JobPostingUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    status: Optional[str] = None
    views_count: Optional[int] = None
    deadline: Optional[datetime] = None

class JobPostingResponse(JobPostingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JobApplicationBase(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    cover_letter: Optional[str] = None

class JobApplicationResponse(JobApplicationBase):
    id: int
    job_id: int
    cv_file_path: Optional[str] = None
    status: str
    ai_score: Optional[int] = None
    ai_fit_status: Optional[str] = None
    ai_evaluation: Optional[Dict] = None
    admin_notes: Optional[str] = None
    review_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JobApplicationAdminUpdate(BaseModel):
    admin_notes: Optional[str] = None
    review_status: Optional[str] = None
    status: Optional[str] = None  # Allow admin to manually override status

class JobStatsResponse(BaseModel):
    job_id: int
    title: Optional[str] = None
    views_count: int = 0
    total_applications: int = 0
    submitted: int = 0
    ai_reviewed: int = 0
    review_new: int = 0
    review_shortlist: int = 0
    review_interview: int = 0
    review_rejected: int = 0
    review_suitable: int = 0
    review_not_suitable: int = 0
    pass_count: int = 0
    failed_count: int = 0
    pending_count: int = 0
    conversion_rate: float = 0.0
    pass_rate: float = 0.0
    avg_ai_score: Optional[float] = None
    positive_score_count: int = 0
    negative_score_count: int = 0

class JobAnalyticsItem(BaseModel):
    job_id: int
    title: str
    department: Optional[str] = None
    status: str
    views_count: int
    total_applications: int
    pass_count: int
    failed_count: int
    pending_count: int
    conversion_rate: float  # (total_applications / views_count) * 100
    pass_rate: float        # (pass_count / total_applications) * 100
    avg_ai_score: Optional[float] = None

class JobAnalyticsSummary(BaseModel):
    total_jobs: int
    total_views: int
    total_applications: int
    total_pass: int
    total_failed: int
    total_pending: int
    overall_conversion_rate: float
    overall_pass_rate: float
    jobs: List[JobAnalyticsItem]