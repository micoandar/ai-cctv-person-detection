"""
Konfigurasi global aplikasi.
Runtime settings (yang diubah dari halaman Settings) di-persist ke
runtime_settings.json agar tidak hilang saat backend restart.
"""
import json
import logging
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
RUNTIME_FILE = BASE_DIR / "runtime_settings.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "AI CCTV Person Detection & Monitoring System"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    DATABASE_URL: str = "mysql+pymysql://root:@localhost:3306/cctv_monitoring"

    MODEL_PATH: str = "models/best.pt"
    CONFIDENCE_THRESHOLD: float = 0.50
    IOU_THRESHOLD: float = 0.45
    IMAGE_SIZE: int = 640
    PERSON_CLASS_NAME: str = "person"

    CAMERA_INDEX: int = 0
    CAMERA_WIDTH: int = 1280
    CAMERA_HEIGHT: int = 720
    TARGET_FPS: int = 10
    JPEG_QUALITY: int = 70
    STREAM_MAX_WIDTH: int = 960

    STATS_SAVE_INTERVAL: int = 5

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    LLM_ENABLED: bool = False
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    DELETE_ORIGINAL_IMAGE: bool = True
    DELETE_ORIGINAL_VIDEO: bool = False
    RETENTION_DAYS: int = 30

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def model_absolute_path(self) -> Path:
        p = Path(self.MODEL_PATH)
        return p if p.is_absolute() else (BASE_DIR / p)

    @property
    def upload_dir(self) -> Path:
        d = BASE_DIR / "uploads"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def processed_dir(self) -> Path:
        d = BASE_DIR / "processed"
        d.mkdir(parents=True, exist_ok=True)
        return d


settings = Settings()


# ======================================================================
# Runtime settings (persist ke runtime_settings.json)
# ======================================================================
_DEFAULT_RUNTIME = {
    "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
    "iou_threshold": settings.IOU_THRESHOLD,
    "detection_fps": settings.TARGET_FPS,
    "camera_index": settings.CAMERA_INDEX,
    "camera_width": settings.CAMERA_WIDTH,
    "camera_height": settings.CAMERA_HEIGHT,
}


def _load_runtime_settings() -> dict:
    data = dict(_DEFAULT_RUNTIME)
    if RUNTIME_FILE.exists():
        try:
            saved = json.loads(RUNTIME_FILE.read_text(encoding="utf-8"))
            for k, v in saved.items():
                if k in data:
                    data[k] = v
            logger.info("Runtime settings di-load dari %s", RUNTIME_FILE.name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gagal membaca %s: %s", RUNTIME_FILE.name, exc)
    return data


def save_runtime_settings() -> bool:
    try:
        RUNTIME_FILE.write_text(
            json.dumps(runtime_settings, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Runtime settings disimpan ke %s", RUNTIME_FILE.name)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Gagal menyimpan runtime settings: %s", exc)
        return False


def reset_runtime_settings() -> dict:
    runtime_settings.clear()
    runtime_settings.update(_DEFAULT_RUNTIME)
    save_runtime_settings()
    return dict(runtime_settings)


runtime_settings: dict = _load_runtime_settings()