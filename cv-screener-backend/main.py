import sys
from pathlib import Path
import logging

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


load_dotenv()

# Cấu hình logging để hiển thị đầy đủ ra console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
logger.info("===== CV Screener Backend đang khởi động... =====")

from app.database import engine, Base
from app.routers import cv, jd, jobs  # Import cả 3 module router

from sqlalchemy import text

# Tự động tạo bảng trong database nếu chưa có (SQLite)
Base.metadata.create_all(bind=engine)

def run_db_migrations():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE job_postings ADD COLUMN views_count INTEGER DEFAULT 0;"))
            conn.commit()
            logger.info("Migrated SQLite schema: added 'views_count' column to 'job_postings'.")
    except Exception:
        # Field already exists or table freshly created
        pass

run_db_migrations()


app = FastAPI(
    title="CV Screener & Evaluator API",
    description="Hệ thống tự động lọc và chấm điểm CV thông minh ứng dụng AI",
    version="1.0.0"
)

# CORS – cho phép frontend local gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các Router module vào hệ thống
app.include_router(cv.router)
app.include_router(jd.router)
app.include_router(jobs.router)

uploads_dir = Path(__file__).resolve().parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
# Serve uploaded CV files
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

frontend_dir = Path(__file__).resolve().parent / "frontend"
# Serve candidate frontend static files
app.mount("/ui", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

admin_dir = Path(__file__).resolve().parent / "frontend-admin"
# Serve recruiter/admin frontend static files
app.mount("/admin", StaticFiles(directory=str(admin_dir), html=True), name="admin")


@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "project": "CV Screener & Evaluator Backend API",
        "docs_url": "/docs",
        "candidate_ui": "/ui/",
        "recruiter_ui": "/admin/",
    }