import logging
import os
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, BackgroundTasks, Query
from app.tasks import run_scoring_task, run_scoring_in_thread
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services import gemini_service
from app.services.pdf_service import extract_text_from_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["Job Portal"])

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024
SUPPORTED_CV_EXTENSIONS = {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"}

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── Job Posting APIs ────────────────────────────────────────────────────────

@router.post("", response_model=schemas.JobPostingResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: schemas.JobPostingCreate, db: Session = Depends(get_db)):
    """Tạo mới tin tuyển dụng."""
    try:
        new_job = models.JobPosting(
            title=payload.title,
            department=payload.department,
            location=payload.location,
            job_type=payload.job_type,
            description=payload.description,
            requirements=payload.requirements,
            benefits=payload.benefits,
            status=payload.status,
            deadline=payload.deadline,
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        return new_job
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi tạo tin tuyển dụng: {str(e)}",
        )


@router.get("/analytics/summary", response_model=schemas.JobAnalyticsSummary)
def get_analytics_summary(db: Session = Depends(get_db)):
    """Thống kê tổng quan báo cáo tuyển dụng toàn hệ thống và theo từng công việc."""
    jobs = db.query(models.JobPosting).order_by(models.JobPosting.created_at.desc()).all()
    all_apps = db.query(models.JobApplication).all()

    total_jobs = len(jobs)
    total_views = sum(j.views_count or 0 for j in jobs)
    total_applications = len(all_apps)

    pass_statuses = {"shortlist", "interview", "suitable", "accepted"}
    failed_statuses = {"rejected", "not_suitable"}

    total_pass = sum(1 for a in all_apps if a.review_status in pass_statuses)
    total_failed = sum(1 for a in all_apps if a.review_status in failed_statuses)
    total_pending = total_applications - total_pass - total_failed

    overall_conversion_rate = round((total_applications / total_views * 100), 2) if total_views > 0 else 0.0
    overall_pass_rate = round((total_pass / total_applications * 100), 2) if total_applications > 0 else 0.0

    job_analytics_items = []
    for j in jobs:
        j_apps = [a for a in all_apps if a.job_id == j.id]
        j_total_apps = len(j_apps)
        j_pass = sum(1 for a in j_apps if a.review_status in pass_statuses)
        j_failed = sum(1 for a in j_apps if a.review_status in failed_statuses)
        j_pending = j_total_apps - j_pass - j_failed

        v_count = j.views_count or 0
        conv_rate = round((j_total_apps / v_count * 100), 2) if v_count > 0 else 0.0
        p_rate = round((j_pass / j_total_apps * 100), 2) if j_total_apps > 0 else 0.0

        scores = [a.ai_score for a in j_apps if a.ai_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None

        job_analytics_items.append(
            schemas.JobAnalyticsItem(
                job_id=j.id,
                title=j.title,
                department=j.department,
                status=j.status or "active",
                views_count=v_count,
                total_applications=j_total_apps,
                pass_count=j_pass,
                failed_count=j_failed,
                pending_count=j_pending,
                conversion_rate=conv_rate,
                pass_rate=p_rate,
                avg_ai_score=avg_score,
            )
        )

    return schemas.JobAnalyticsSummary(
        total_jobs=total_jobs,
        total_views=total_views,
        total_applications=total_applications,
        total_pass=total_pass,
        total_failed=total_failed,
        total_pending=total_pending,
        overall_conversion_rate=overall_conversion_rate,
        overall_pass_rate=overall_pass_rate,
        jobs=job_analytics_items,
    )


@router.get("", response_model=List[schemas.JobPostingResponse])
def list_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    """Lấy danh sách các tin tuyển dụng, có thể lọc theo status (active/closed/draft)."""
    query = db.query(models.JobPosting)
    if status_filter:
        query = query.filter(models.JobPosting.status == status_filter)
    return query.order_by(models.JobPosting.created_at.desc()).all()


@router.get("/{id}", response_model=schemas.JobPostingResponse)
def get_job(id: int, db: Session = Depends(get_db)):
    """Chi tiết tin tuyển dụng."""
    job = db.query(models.JobPosting).filter(models.JobPosting.id == id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tin tuyển dụng.")
    return job


@router.post("/{id}/view", status_code=status.HTTP_200_OK)
def increment_job_view(id: int, db: Session = Depends(get_db)):
    """Ghi nhận 1 lượt truy cập cho bài đăng tuyển dụng."""
    job = db.query(models.JobPosting).filter(models.JobPosting.id == id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tin tuyển dụng.")

    if job.views_count is None:
        job.views_count = 0
    job.views_count += 1
    db.commit()
    db.refresh(job)
    return {"message": "Đã ghi nhận lượt truy cập.", "job_id": job.id, "views_count": job.views_count}



@router.put("/{id}", response_model=schemas.JobPostingResponse)
def update_job(id: int, payload: schemas.JobPostingUpdate, db: Session = Depends(get_db)):
    """Cập nhật tin tuyển dụng."""
    job = db.query(models.JobPosting).filter(models.JobPosting.id == id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tin tuyển dụng.")

    try:
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(job, key, value)
        job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
        return job
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi cập nhật tin tuyển dụng: {str(e)}",
        )


@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_job(id: int, db: Session = Depends(get_db)):
    """Xóa tin tuyển dụng."""
    job = db.query(models.JobPosting).filter(models.JobPosting.id == id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tin tuyển dụng.")

    try:
        db.delete(job)
        db.commit()
        return {"message": "Xóa bài đăng tuyển dụng thành công."}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi xóa tin tuyển dụng: {str(e)}",
        )


# ─── Job Application APIs ─────────────────────────────────────────────────────

@router.post("/{job_id}/apply", status_code=status.HTTP_201_CREATED)
async def apply_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    cv_file: UploadFile = File(...),
    cover_letter: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Ứng viên gửi hồ sơ và hệ thống tự động đánh giá CV bằng AI."""
    job = db.query(models.JobPosting).filter(models.JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tin tuyển dụng tương ứng.")

    if not cv_file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu file CV.")

    file_extension = os.path.splitext(cv_file.filename)[1].lower()
    if file_extension not in SUPPORTED_CV_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng file CV không hỗ trợ. Vui lòng upload PDF, DOCX, TXT hoặc file ảnh.",
        )

    content = await cv_file.read()
    file_size = len(content)
    if file_size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File CV trống.")
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File quá lớn. Kích thước tối đa là {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )

    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        # Save file to uploads/
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # Extract CV text
        if file_extension in {".png", ".jpg", ".jpeg"}:
            cv_text = gemini_service.extract_text_from_image(file_path)
        else:
            cv_text = extract_text_from_file(file_path)

        if not cv_text or len(cv_text.strip()) < 50:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Không thể trích xuất văn bản từ CV. Vui lòng thử file khác rõ ràng hơn.",
            )

        # Create base application record
        new_app = models.JobApplication(
            job_id=job_id,
            full_name=full_name,
            email=email,
            phone=phone,
            cv_file_path=file_path,
            cover_letter=cover_letter,
            status="submitted",
            review_status="new",
        )
        db.add(new_app)
        db.commit()
        db.refresh(new_app)

        # Schedule background AI scoring task via dedicated thread
        run_scoring_in_thread(new_app.id)
        print(f"[APPLY JOB] Background AI scoring task đã được lên lịch cho Application ID: {new_app.id} (Job: '{job.title}')")
        logger.info(f"[APPLY JOB] Background scoring scheduled for Application ID: {new_app.id}")

        return {
            "message": "Ứng viên đã nộp CV thành công. AI đang phân tích hồ sơ của bạn.",
            "application_id": new_app.id,
            "job_id": new_app.job_id,
            "status": new_app.status,
        }

    except HTTPException:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Error in apply_job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi xử lý hồ sơ ứng tuyển: {str(e)}",
        )


@router.get("/{job_id}/applications", response_model=List[schemas.JobApplicationResponse])
def list_applications(
    job_id: int,
    status_filter: Optional[str] = Query(None, alias="status", description="Lọc theo status: submitted | ai_reviewed"),
    review_status: Optional[str] = Query(None, description="Lọc theo review_status: new | shortlist | interview | rejected | suitable | not_suitable"),
    sort_by: Optional[str] = Query("created_at", description="Sắp xếp theo: created_at | full_name | ai_score"),
    order: Optional[str] = Query("desc", description="Chiều sắp xếp: asc | desc"),
    db: Session = Depends(get_db),
):
    """Danh sách hồ sơ ứng tuyển cho tin tuyển dụng cụ thể với bộ lọc và sắp xếp."""
    query = db.query(models.JobApplication).filter(models.JobApplication.job_id == job_id)

    # Filters
    if status_filter:
        query = query.filter(models.JobApplication.status == status_filter)
    if review_status:
        query = query.filter(models.JobApplication.review_status == review_status)

    # Sorting
    sort_col = models.JobApplication.created_at
    if sort_by == "full_name":
        sort_col = models.JobApplication.full_name
    elif sort_by == "ai_score":
        sort_col = models.JobApplication.ai_score

    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    return query.all()


@router.get("/{job_id}/stats", response_model=schemas.JobStatsResponse)
def get_job_stats(job_id: int, db: Session = Depends(get_db)):
    """Thống kê tổng hợp hồ sơ ứng tuyển cho một job."""
    job = db.query(models.JobPosting).filter(models.JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tin tuyển dụng.")

    apps = db.query(models.JobApplication).filter(models.JobApplication.job_id == job_id).all()
    total = len(apps)

    def count_status(s): return sum(1 for a in apps if a.status == s)
    def count_review(r): return sum(1 for a in apps if a.review_status == r)

    pass_statuses = {"shortlist", "interview", "suitable", "accepted"}
    failed_statuses = {"rejected", "not_suitable"}

    pass_c = sum(1 for a in apps if a.review_status in pass_statuses)
    failed_c = sum(1 for a in apps if a.review_status in failed_statuses)
    pending_c = total - pass_c - failed_c

    views_c = job.views_count or 0
    conv_rate = round((total / views_c * 100), 2) if views_c > 0 else 0.0
    p_rate = round((pass_c / total * 100), 2) if total > 0 else 0.0

    scored = [a.ai_score for a in apps if a.ai_score is not None]
    avg_score = round(sum(scored) / len(scored), 1) if scored else None

    return schemas.JobStatsResponse(
        job_id=job_id,
        title=job.title,
        views_count=views_c,
        total_applications=total,
        submitted=count_status("submitted"),
        ai_reviewed=count_status("ai_reviewed"),
        review_new=count_review("new"),
        review_shortlist=count_review("shortlist"),
        review_interview=count_review("interview"),
        review_rejected=count_review("rejected"),
        review_suitable=count_review("suitable"),
        review_not_suitable=count_review("not_suitable"),
        pass_count=pass_c,
        failed_count=failed_c,
        pending_count=pending_c,
        conversion_rate=conv_rate,
        pass_rate=p_rate,
        avg_ai_score=avg_score,
    )



@router.get("/{job_id}/applications/{application_id}", response_model=schemas.JobApplicationResponse)
def get_application(job_id: int, application_id: int, db: Session = Depends(get_db)):
    """Chi tiết hồ sơ ứng tuyển của ứng viên."""
    app_record = (
        db.query(models.JobApplication)
        .filter(models.JobApplication.job_id == job_id, models.JobApplication.id == application_id)
        .first()
    )
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ ứng tuyển.")
    return app_record


@router.patch("/{job_id}/applications/{application_id}", response_model=schemas.JobApplicationResponse)
def review_application(
    job_id: int,
    application_id: int,
    payload: schemas.JobApplicationAdminUpdate,
    db: Session = Depends(get_db),
):
    """Admin review và cập nhật trạng thái tuyển dụng thủ công cùng ghi chú."""
    app_record = (
        db.query(models.JobApplication)
        .filter(models.JobApplication.job_id == job_id, models.JobApplication.id == application_id)
        .first()
    )
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ ứng tuyển.")

    try:
        if payload.admin_notes is not None:
            app_record.admin_notes = payload.admin_notes
        if payload.review_status is not None:
            app_record.review_status = payload.review_status
        if payload.status is not None:
            app_record.status = payload.status

        app_record.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(app_record)
        return app_record
    except Exception as e:
        db.rollback()
        logger.error(f"Error reviewing application: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi cập nhật hồ sơ: {str(e)}",
        )


@router.post("/{job_id}/applications/{application_id}/evaluate")
def evaluate_application_manually(job_id: int, application_id: int, db: Session = Depends(get_db)):
    """Kích hoạt lại đánh giá AI thủ công cho một CV đã nộp."""
    print(f"[MANUAL EVAL] Kích hoạt đánh giá AI thủ công cho Application {application_id} / Job {job_id}")
    logger.info(f"[MANUAL EVAL] Bắt đầu đánh giá thủ công cho Application {application_id}")
    app_record = (
        db.query(models.JobApplication)
        .filter(models.JobApplication.job_id == job_id, models.JobApplication.id == application_id)
        .first()
    )
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ ứng tuyển.")

    if not app_record.cv_file_path or not os.path.exists(app_record.cv_file_path):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Không tìm thấy file CV trên server.")

    try:
        print(f"[MANUAL EVAL] Đọc CV từ file: {app_record.cv_file_path}")
        file_extension = os.path.splitext(app_record.cv_file_path)[1].lower()
        if file_extension in {".png", ".jpg", ".jpeg"}:
            cv_text = gemini_service.extract_text_from_image(app_record.cv_file_path)
        else:
            cv_text = extract_text_from_file(app_record.cv_file_path)

        print(f"[MANUAL EVAL] Đọc CV xong. Độ dài text: {len(cv_text)} ký tự")

        job = db.query(models.JobPosting).filter(models.JobPosting.id == job_id).first()
        print(f"[MANUAL EVAL] Đang đọc JD cho Job: '{job.title}' (ID: {job.id})")
        jd_text = f"Title: {job.title}\nDescription: {job.description or ''}\nRequirements: {job.requirements or ''}"
        jd_criteria = gemini_service.extract_jd_criteria(jd_text)
        print(f"[MANUAL EVAL] Đọc JD xong. required_skills={jd_criteria.required_skills}")

        print(f"[MANUAL EVAL] AI đánh giá bắt đầu cho Application {application_id}...")
        evaluation = gemini_service.evaluate_cv_against_jd(cv_text, jd_criteria.model_dump())
        print(f"[MANUAL EVAL] AI đánh giá kết thúc. Score: {evaluation.total_score} | Fit: {evaluation.fit_status}")

        app_record.ai_score = evaluation.total_score
        app_record.ai_fit_status = evaluation.fit_status
        app_record.ai_evaluation = evaluation.model_dump()
        app_record.status = "ai_reviewed"
        app_record.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(app_record)

        print(f"[MANUAL EVAL] Hoàn tất đánh giá thủ công cho Application {application_id}. Score: {evaluation.total_score}")
        logger.info(f"[MANUAL EVAL] Hoàn tất Application {application_id}: score={evaluation.total_score}")

        return {
            "message": "Đánh giá lại bằng AI thành công.",
            "application_id": app_record.id,
            "status": app_record.status,
            "ai_score": app_record.ai_score,
            "ai_fit_status": app_record.ai_fit_status,
            "ai_evaluation": app_record.ai_evaluation,
        }
    except Exception as e:
        db.rollback()
        import traceback
        print(f"[MANUAL EVAL] LỖI khi đánh giá thủ công Application {application_id}: {str(e)}")
        print(f"[MANUAL EVAL] Traceback:\n{traceback.format_exc()}")
        logger.error(f"Error in manual evaluate: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi đánh giá lại AI: {str(e)}",
        )
