"""
Jalankan: python run.py
"""
import uvicorn

from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        reload_excludes=[
            "runtime_settings.json",   # ← PENTING: hindari restart saat save settings
            "uploads/*",
            "processed/*",
            "*.log",
            "__pycache__/*",
            "*.pyc",
            "venv/*",
            ".venv/*",
        ],
    )