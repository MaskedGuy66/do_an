import logging
import os
from sqlalchemy.orm import Session
from app import models
from app.services import gemini_service
from app.services.pdf_service import extract_text_from_file

logger = logging.getLogger(__name__)

def run_scoring(application_id: int, db: Session) -> None:
    """Run AI scoring for a JobApplication in background.
    Fetches the application, extracts CV text, evaluates against the job description,
    and updates the DB record with score, fit status and evaluation details.
    """
    print(f"[BACKGROUND] ===== Bắt đầu scoring cho Application ID: {application_id} =====")
    logger.info(f"[BACKGROUND] Bắt đầu scoring cho Application ID: {application_id}")
    try:
        app_record = db.query(models.JobApplication).filter(models.JobApplication.id == application_id).first()
        if not app_record:
            print(f"[BACKGROUND] Scoring thất bại: Không tìm thấy Application {application_id}")
            logger.error(f"Scoring failed: Application {application_id} not found")
            return

        # Load related job posting
        job = db.query(models.JobPosting).filter(models.JobPosting.id == app_record.job_id).first()
        if not job:
            print(f"[BACKGROUND] Scoring thất bại: Không tìm thấy Job {app_record.job_id} cho Application {application_id}")
            logger.error(f"Scoring failed: Job {app_record.job_id} not found for application {application_id}")
            return

        print(f"[BACKGROUND] Đọc CV từ file: {app_record.cv_file_path}")
        # Extract CV text
        file_extension = os.path.splitext(app_record.cv_file_path)[1].lower()
        if file_extension in {".png", ".jpg", ".jpeg"}:
            cv_text = gemini_service.extract_text_from_image(app_record.cv_file_path)
        else:
            cv_text = extract_text_from_file(app_record.cv_file_path)

        if not cv_text or len(cv_text.strip()) < 50:
            print(f"[BACKGROUND] Cảnh báo: CV text quá ngắn hoặc rỗng cho Application {application_id}. Hủy scoring.")
            logger.warning(f"Insufficient CV text for application {application_id}")
            return

        print(f"[BACKGROUND] Đọc CV xong. Độ dài text: {len(cv_text)} ký tự. Preview: {cv_text[:200].strip()!r}")

        # JD criteria
        print(f"[BACKGROUND] Bắt đầu đọc JD cho Job: '{job.title}' (ID: {job.id})")
        jd_text = f"Title: {job.title}\nDescription: {job.description or ''}\nRequirements: {job.requirements or ''}"
        jd_criteria = gemini_service.extract_jd_criteria(jd_text)
        print(f"[BACKGROUND] Đọc JD xong. Kết quả trích xuất: required_skills={jd_criteria.required_skills}, min_years={jd_criteria.min_years_experience}")

        # Keyword Matching
        print(f"[BACKGROUND] Bắt đầu Matching Word giữa CV và JD...")
        pre_match = gemini_service.pre_match_cv_with_jd(cv_text, jd_criteria.model_dump())
        print(f"[BACKGROUND] Matching Word hoàn tất. Ngành: {pre_match['industry']} | Khớp: {pre_match['matched_required_skills']} | Thiếu: {pre_match['missing_required_skills']} | Năm KN: {pre_match['detected_years_experience']}")

        # AI Evaluation
        print(f"[BACKGROUND] AI đánh giá bắt đầu cho Application {application_id}...")
        evaluation = gemini_service.evaluate_cv_against_jd(cv_text, jd_criteria.model_dump())
        print(f"[BACKGROUND] AI đánh giá kết thúc cho Application {application_id}. Score: {evaluation.total_score} | Fit: {evaluation.fit_status}")

        # Update DB
        app_record.ai_score = evaluation.total_score
        app_record.ai_fit_status = evaluation.fit_status
        app_record.ai_evaluation = evaluation.model_dump()
        app_record.status = "ai_reviewed"
        db.commit()
        print(f"[BACKGROUND] ===== Scoring hoàn tất cho Application {application_id}. Score: {evaluation.total_score} =====")
        logger.info(f"Scoring completed for application {application_id}: score {evaluation.total_score}")
    except Exception as e:
        db.rollback()
        import traceback
        print(f"[BACKGROUND] LỖI khi scoring Application {application_id}: {str(e)}")
        print(f"[BACKGROUND] Traceback:\n{traceback.format_exc()}")
        logger.error(f"Error in scoring application {application_id}: {str(e)}")
