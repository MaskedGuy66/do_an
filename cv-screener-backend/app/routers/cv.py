from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
import os
import uuid
import logging

from app.database import get_db
from app import models
from app.services import gemini_service
from app.services.pdf_service import extract_text_from_file

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024
MIN_TEXT_LENGTH = 50
SUPPORTED_CV_EXTENSIONS = {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cv", tags=["Candidate CV"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_cv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload CV theo nhiều định dạng: PDF, DOCX, TXT, ảnh scan."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu tên file CV.")

    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in SUPPORTED_CV_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hệ thống chỉ hỗ trợ PDF, DOCX, TXT, JPG, JPEG hoặc PNG.",
        )

    content = await file.read()
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
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        if file_extension in {".png", ".jpg", ".jpeg"}:
            raw_text = gemini_service.extract_text_from_image(file_path)
        else:
            raw_text = extract_text_from_file(file_path)

        if not raw_text or len(raw_text.strip()) < MIN_TEXT_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Không thể trích xuất đủ văn bản từ file CV. Vui lòng thử file khác hoặc chuyển file sang PDF/DOCX/TXT rõ nét hơn.",
            )

        new_cv = models.CandidateCV(
            file_path=file_path,
            status="PENDING",
            cleaned_text=raw_text,
            is_anonymous=False,
        )
        db.add(new_cv)
        db.commit()
        db.refresh(new_cv)

        return {
            "message": "Tải lên và trích xuất CV thành công!",
            "cv_id": new_cv.id,
            "filename": file.filename,
            "status": new_cv.status,
            "text_length": len(raw_text),
            "extracted_text_preview": raw_text[:300] + ("..." if len(raw_text) > 300 else ""),
        }

    except HTTPException:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Error uploading CV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi xử lý file CV: {str(e)}",
        )


@router.get("/", status_code=status.HTTP_200_OK)
def list_cvs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        cvs = db.query(models.CandidateCV).offset(skip).limit(limit).all()
        total = db.query(models.CandidateCV).count()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": [
                {
                    "id": cv.id,
                    "filename": cv.file_path.split("/")[-1] if cv.file_path else None,
                    "status": cv.status,
                    "total_score": cv.total_score,
                    "created_at": cv.created_at.isoformat() if cv.created_at else None,
                    "candidate_name": cv.candidate_name,
                    "email": cv.email,
                }
                for cv in cvs
            ],
        }
    except Exception as e:
        logger.error(f"Error listing CVs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách CV: {str(e)}",
        )


@router.get("/{cv_id}", status_code=status.HTTP_200_OK)
def get_cv_detail(cv_id: int, db: Session = Depends(get_db)):
    try:
        cv = db.query(models.CandidateCV).filter(models.CandidateCV.id == cv_id).first()
        if not cv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy CV với ID: {cv_id}",
            )

        return {
            "id": cv.id,
            "candidate_name": cv.candidate_name,
            "email": cv.email,
            "phone": cv.phone,
            "file_path": cv.file_path,
            "status": cv.status,
            "total_score": cv.total_score,
            "is_anonymous": cv.is_anonymous,
            "created_at": cv.created_at.isoformat() if cv.created_at else None,
            "updated_at": cv.updated_at.isoformat() if cv.updated_at else None,
            "cleaned_text_preview": cv.cleaned_text[:500] + "..." if cv.cleaned_text and len(cv.cleaned_text) > 500 else cv.cleaned_text,
            "evaluation_details": cv.evaluation_details,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting CV detail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy thông tin CV: {str(e)}",
        )


@router.post("/{cv_id}/evaluate/{jd_id}", status_code=status.HTTP_200_OK)
def evaluate_candidate_cv(cv_id: int, jd_id: int, db: Session = Depends(get_db)):
    try:
        cv_record = db.query(models.CandidateCV).filter(models.CandidateCV.id == cv_id).first()
        jd_record = db.query(models.JobDescription).filter(models.JobDescription.id == jd_id).first()

        if not cv_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy thông tin CV ứng viên với ID: {cv_id}",
            )
        if not jd_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy mô tả công việc (JD) với ID: {jd_id}",
            )

        logger.info(f"Evaluating CV {cv_id} against JD {jd_id}")

        evaluation_result = gemini_service.evaluate_cv_against_jd(
            cv_text=cv_record.cleaned_text or "",
            jd_criteria=jd_record.extracted_criteria or {},
        )

        cv_record.total_score = evaluation_result.total_score
        cv_record.status = "EVALUATED"
        cv_record.evaluation_details = evaluation_result.model_dump()

        db.commit()
        db.refresh(cv_record)

        return {
            "message": f"Chấm điểm ứng viên thành công cho vị trí: {jd_record.title}!",
            "cv_id": cv_record.id,
            "jd_id": jd_record.id,
            "score": cv_record.total_score,
            "fit_status": evaluation_result.fit_status,
            "evaluation_details": cv_record.evaluation_details,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error evaluating CV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý chấm điểm: {str(e)}",
        )


@router.post("/match/{jd_id}", status_code=status.HTTP_200_OK)
def match_candidates(jd_id: int, db: Session = Depends(get_db)):
    """Đánh giá toàn bộ CV đối với 1 JD và trả về danh sách ranking theo mức độ phù hợp."""
    jd_record = db.query(models.JobDescription).filter(models.JobDescription.id == jd_id).first()
    if not jd_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy mô tả công việc (JD) với ID: {jd_id}",
        )

    cvs = db.query(models.CandidateCV).all()
    ranked = []

    for cv in cvs:
        if not cv.cleaned_text:
            continue

        evaluation = gemini_service.evaluate_cv_against_jd(
            cv_text=cv.cleaned_text,
            jd_criteria=jd_record.extracted_criteria or {},
        )

        filename = f"CV-{cv.id}"
        if cv.file_path:
            original_name = os.path.basename(cv.file_path)
            if original_name and original_name != str(cv.id):
                filename = f"CV-{cv.id} · {os.path.splitext(original_name)[0]}"

        ranked.append(
            {
                "cv_id": cv.id,
                "filename": filename,
                "total_score": evaluation.total_score,
                "fit_status": evaluation.fit_status,
                "skills_match": evaluation.skills_match,
                "experience_match": evaluation.experience_match,
                "pros": evaluation.pros,
                "cons": evaluation.cons,
                "evaluation_details": evaluation.model_dump(),
            }
        )

    ranked.sort(key=lambda item: item["total_score"], reverse=True)
    return {
        "jd_id": jd_id,
        "jd_title": jd_record.title,
        "total_candidates": len(ranked),
        "data": ranked,
    }


@router.delete("/{cv_id}", status_code=status.HTTP_200_OK)
def delete_cv(cv_id: int, db: Session = Depends(get_db)):
    try:
        cv = db.query(models.CandidateCV).filter(models.CandidateCV.id == cv_id).first()
        if not cv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy CV với ID: {cv_id}",
            )

        if cv.file_path and os.path.exists(cv.file_path):
            os.remove(cv.file_path)
            logger.info(f"File deleted: {cv.file_path}")

        db.delete(cv)
        db.commit()

        return {
            "message": f"CV với ID {cv_id} đã được xóa thành công.",
            "cv_id": cv_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting CV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xóa CV: {str(e)}",
        )