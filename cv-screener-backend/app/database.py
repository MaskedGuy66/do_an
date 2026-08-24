from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./cv_screener.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Lớp Base để các Models (bảng) khác kế thừa
Base = declarative_base()

# 5. Dependency cung cấp DB Session cho mỗi request API và đóng lại khi xong
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()