import logging
import threading
import traceback
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services import score_service

logger = logging.getLogger(__name__)

def run_scoring_task(application_id: int) -> None:
    """Background task entrypoint to run AI scoring for a job application.
    Creates its own DB session and delegates to score_service.run_scoring.
    """
    logger.info(f"[BACKGROUND TASK] ===== run_scoring_task được gọi cho Application ID: {application_id} =====")
    logger.info(f"[BACKGROUND TASK] Bắt đầu background scoring cho Application ID: {application_id}")
    db: Session = SessionLocal()
    try:
        score_service.run_scoring(application_id, db)
        logger.info(f"[BACKGROUND TASK] ===== run_scoring_task hoàn tất cho Application ID: {application_id} =====")
        logger.info(f"[BACKGROUND TASK] Hoàn tất background scoring cho Application ID: {application_id}")
    except Exception as e:
        logger.error(f"[BACKGROUND TASK] LỖI NGHIÊM TRỌNG trong run_scoring_task (Application {application_id}): {str(e)}")
        logger.error(f"[BACKGROUND TASK] Traceback:\n{traceback.format_exc()}")
        logger.error(f"[BACKGROUND TASK] Lỗi nghiêm trọng cho Application {application_id}: {str(e)}")
    finally:
        db.close()
        logger.info(f"[BACKGROUND TASK] DB session đã đóng cho Application ID: {application_id}")


def run_scoring_in_thread(application_id: int) -> None:
    """Chạy scoring trong thread riêng biệt để đảm bảo task được thực thi.
    Dùng threading.Thread thay vì FastAPI BackgroundTasks để tránh bị mất task.
    """
    logger.info(f"[THREAD LAUNCHER] Khởi tạo thread scoring cho Application ID: {application_id}")
    logger.info(f"[THREAD LAUNCHER] Tạo thread scoring cho Application ID: {application_id}")
    thread = threading.Thread(
        target=run_scoring_task,
        args=(application_id,),
        name=f"scoring-app-{application_id}",
        daemon=True,
    )
    thread.start()
    logger.info(f"[THREAD LAUNCHER] Thread '{thread.name}' đã bắt đầu (thread_id={thread.ident}) cho Application ID: {application_id}")
    logger.info(f"[THREAD LAUNCHER] Thread started cho Application ID: {application_id}")
