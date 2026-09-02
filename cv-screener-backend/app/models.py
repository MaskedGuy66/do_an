import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class CandidateCV(Base):
    __tablename__ = "candidate_cvs"

    # 1. Thông tin khóa chính và định danh
    id = Column(Integer, primary_key=True, index=True)
    
    # 2. Thông tin cá nhân trích xuất từ CV (Có thể NULL nếu bật chế độ ẩn danh)
    candidate_name = Column(String, nullable=True) 
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    
    # 3. Quản lý file dữ liệu
    file_path = Column(String, nullable=False) # Đường dẫn vật lý lưu file CV trên server
    
    # Trạng thái xử lý: PENDING (Chờ), PROCESSING (Đang xử lý), DONE (Xong), FAILED (Lỗi)
    status = Column(String, default="PENDING") 
    
    # 4. Dữ liệu văn bản thô sau khi trích xuất và làm sạch
    cleaned_text = Column(Text, nullable=True)
    
    # 5. Kết quả đánh giá từ LLM (AI)
    total_score = Column(Integer, nullable=True)       # Điểm tổng thể (ví dụ: thang điểm 100)
    evaluation_details = Column(JSON, nullable=True)   # Lưu chi tiết điểm thành phần dưới dạng JSON
    
    # 6. Cấu hình bảo mật/lọc
    is_anonymous = Column(Boolean, default=False)      # Chế độ ẩn danh thông tin cá nhân
    
    # 7. Mốc thời gian hệ thống
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)  # Tên vị trí tuyển dụng (Ví dụ: Python Developer)
    raw_text = Column(Text, nullable=True)                  # Văn bản thô nếu HR copy-paste
    image_path = Column(String(512), nullable=True)         # Đường dẫn ảnh nếu HR upload ảnh tin tuyển dụng
    
    # Lưu cấu trúc tiêu chí dạng JSON được bóc tách từ Gemini (skills, experience, education,...)
    extracted_criteria = Column(JSON, nullable=True)
    
    # Mốc thời gian – cần thiết cho listing theo ngày tạo
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    department = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    job_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    benefits = Column(Text, nullable=True)
    status = Column(String(50), default="active")
    views_count = Column(Integer, default=0)
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    applications = relationship("JobApplication", back_populates="job", cascade="all, delete-orphan")

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    cv_file_path = Column(String(500), nullable=True)
    cover_letter = Column(Text, nullable=True)
    status = Column(String(50), default="submitted")
    ai_score = Column(Integer, nullable=True)
    ai_fit_status = Column(String(50), nullable=True)
    ai_evaluation = Column(JSON, nullable=True)
    admin_notes = Column(Text, nullable=True)
    review_status = Column(String(50), default="new")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    job = relationship("JobPosting", back_populates="applications")