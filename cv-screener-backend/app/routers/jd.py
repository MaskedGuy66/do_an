import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import JobDescription
from app.schemas import JDIngestRequest
from app.services import gemini_service
from app.services.pdf_service import extract_text_from_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jd", tags=["Job Description"])

SUPPORTED_JD_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".png", ".jpg", ".jpeg"}


@router.post("/ingest", status_code=status.HTTP_201_CREATED)
def ingest_jd_text(payload: JDIngestRequest, db: Session = Depends(get_db)):
    """Ingest JD dạng text và trích xuất tiêu chí bằng Gemini."""
    try:
        if not payload.title or not payload.title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tiêu đề vị trí tuyển dụng không được để trống.",
            )

        if not payload.raw_text or not payload.raw_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nội dung mô tả công việc không được để trống.",
            )

        logger.info(f"Ingesting JD: {payload.title}")

        structured_criteria = gemini_service.extract_jd_criteria(payload.raw_text)

        new_jd = JobDescription(
            title=payload.title,
            raw_text=payload.raw_text,
            extracted_criteria=structured_criteria.model_dump(),
            image_path=None,
        )
        db.add(new_jd)
        db.commit()
        db.refresh(new_jd)

        return {
            "message": "Xử lý và lưu Job Description thành công!",
            "jd_id": new_jd.id,
            "title": new_jd.title,
            "extracted_criteria": new_jd.extracted_criteria,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting JD: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi xử lý JD: {str(e)}",
        )


@router.post("/ingest-file", status_code=status.HTTP_201_CREATED)
async def ingest_jd_file(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Nhận JD từ PDF / DOCX / TXT / ảnh và trích xuất tiêu chí bằng Gemini."""
    try:
        if not title or not title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tiêu đề vị trí tuyển dụng không được để trống.",
            )

        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thiếu tên file JD.",
            )

        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in SUPPORTED_JD_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Định dạng file JD không hỗ trợ. Vui lòng upload PDF, DOCX, TXT, JPG, JPEG hoặc PNG.",
            )

        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File JD trống.",
            )

        upload_dir = os.path.join("uploads", "jd")
        os.makedirs(upload_dir, exist_ok=True)
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        try:
            if file_extension in {".png", ".jpg", ".jpeg"}:
                raw_text = gemini_service.extract_text_from_image(file_path)
            else:
                raw_text = extract_text_from_file(file_path)
        except Exception as exc:
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Không thể đọc nội dung file JD: {exc}",
            ) from exc

        if not raw_text or not raw_text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Nội dung JD rỗng hoặc không trích xuất được từ file đã upload.",
            )

        structured_criteria = gemini_service.extract_jd_criteria(raw_text)

        new_jd = JobDescription(
            title=title,
            raw_text=raw_text,
            image_path=file_path if file_extension in {".png", ".jpg", ".jpeg"} else None,
            extracted_criteria=structured_criteria.model_dump(),
        )
        db.add(new_jd)
        db.commit()
        db.refresh(new_jd)

        return {
            "message": "Xử lý JD từ file thành công!",
            "jd_id": new_jd.id,
            "title": new_jd.title,
            "source_file": file.filename,
            "raw_text_preview": raw_text[:600] + ("..." if len(raw_text) > 600 else ""),
            "extracted_criteria": new_jd.extracted_criteria,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting JD file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi xử lý file JD: {str(e)}",
        )


@router.post("/ingest-image", status_code=status.HTTP_201_CREATED)
async def ingest_jd_image(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Nhận JD dạng ảnh và trích xuất tiêu chí bằng Gemini Vision API."""
    try:
        if not title or not title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tiêu đề vị trí tuyển dụng không được để trống.",
            )

        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thiếu tên file ảnh JD.",
            )

        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in {".jpg", ".jpeg", ".png"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chỉ hỗ trợ file ảnh JPG, JPEG hoặc PNG cho JD image ingest.",
            )

        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File ảnh JD trống.",
            )

        upload_dir = os.path.join("uploads", "jd")
        os.makedirs(upload_dir, exist_ok=True)
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        image_path = os.path.join(upload_dir, unique_filename)

        with open(image_path, "wb") as buffer:
            buffer.write(content)

        raw_text = gemini_service.extract_text_from_image(image_path)
        structured_criteria = gemini_service.extract_jd_criteria(raw_text)

        new_jd = JobDescription(
            title=title,
            raw_text=raw_text,
            image_path=image_path,
            extracted_criteria=structured_criteria.model_dump(),
        )
        db.add(new_jd)
        db.commit()
        db.refresh(new_jd)

        return {
            "message": "Xử lý và lưu Job Description từ ảnh thành công!",
            "jd_id": new_jd.id,
            "title": new_jd.title,
            "image_path": new_jd.image_path,
            "raw_text_preview": raw_text[:600] + ("..." if len(raw_text) > 600 else ""),
            "extracted_criteria": new_jd.extracted_criteria,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error ingesting JD image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi xử lý ảnh JD: {str(e)}",
        )


@router.get("/", status_code=status.HTTP_200_OK)
def list_jds(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Lấy danh sách JD."""
    try:
        jds = db.query(JobDescription).offset(skip).limit(limit).all()
        total = db.query(JobDescription).count()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": [
                {
                    "id": jd.id,
                    "title": jd.title,
                    "created_at": jd.created_at.isoformat() if hasattr(jd, "created_at") and jd.created_at else None,
                    "required_skills": jd.extracted_criteria.get("required_skills", []) if jd.extracted_criteria else [],
                    "min_years_experience": jd.extracted_criteria.get("min_years_experience", 0) if jd.extracted_criteria else 0,
                }
                for jd in jds
            ],
        }
    except Exception as e:
        logger.error(f"Error listing JDs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách JD: {str(e)}",
        )


@router.get("/{jd_id}", status_code=status.HTTP_200_OK)
def get_jd_detail(jd_id: int, db: Session = Depends(get_db)):
    """Lấy chi tiết JD theo ID."""
    try:
        jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()

        if not jd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy JD với ID: {jd_id}",
            )

        return {
            "id": jd.id,
            "title": jd.title,
            "raw_text": jd.raw_text,
            "image_path": jd.image_path,
            "extracted_criteria": jd.extracted_criteria,
            "created_at": jd.created_at.isoformat() if hasattr(jd, "created_at") and jd.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting JD detail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy thông tin JD: {str(e)}",
        )


@router.delete("/{jd_id}", status_code=status.HTTP_200_OK)
def delete_jd(jd_id: int, db: Session = Depends(get_db)):
    """Xóa JD theo ID."""
    try:
        jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()

        if not jd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy JD với ID: {jd_id}",
            )

        db.delete(jd)
        db.commit()

        logger.info(f"JD {jd_id} deleted successfully")

        return {
            "message": f"Job Description với ID {jd_id} đã được xóa thành công.",
            "jd_id": jd_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting JD: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xóa JD: {str(e)}",
        )