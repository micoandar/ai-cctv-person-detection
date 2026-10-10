"""
Koneksi database MySQL (XAMPP) menggunakan SQLAlchemy + PyMySQL.
"""
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # cek koneksi mati sebelum dipakai
    pool_recycle=280,        # MySQL default wait_timeout 28800s
    pool_size=5,
    max_overflow=10,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, future=True
)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yield session lalu tutup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Buat semua tabel jika belum ada."""
    from app.database import models  # noqa: F401  (registrasi model)
    Base.metadata.create_all(bind=engine)


def check_connection() -> tuple[bool, str]:
    """Cek koneksi ke MySQL."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "OK"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)