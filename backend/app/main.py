"""
AI CCTV Person Detection & Monitoring System - FastAPI entry point.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import camera, chatbot, detection, statistics
from app.config import settings
from app.database.database import check_connection, init_db
from app.services.cleanup_service import start_background_cleanup
from app.services.detector import get_class_names, get_model_status
from app.services.webcam_service import webcam_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("ai-cctv")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Simpan event loop agar worker thread bisa broadcast ke WebSocket
    webcam_service.attach_loop(asyncio.get_running_loop())

    # ---- Inisialisasi database ----
    ok, message = check_connection()
    if ok:
        try:
            init_db()
            logger.info("Database terhubung & tabel siap digunakan.")
        except Exception as exc:  # noqa: BLE001
            logger.error("Gagal membuat tabel: %s", exc)
    else:
        logger.error(
            "MySQL tidak dapat terhubung. Pastikan MySQL pada XAMPP sudah dijalankan. "
            "Detail: %s",
            message,
        )

    # ---- Cek model ----
    status = get_model_status()
    if not status["exists"]:
        logger.warning(
            "Model YOLO belum ditemukan di %s. Letakkan file best.pt di sana.",
            status["path"],
        )

    # ---- Cleanup worker (hapus file lama berkala) ----
    start_background_cleanup()

    logger.info("%s siap digunakan.", settings.APP_NAME)
    yield

    # ---- Shutdown ----
    webcam_service.stop()
    logger.info("Server dimatikan.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Deteksi person menggunakan YOLO + monitoring real-time.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================================
# STATIC FILES — HARUS DI ATAS include_router
# ======================================================================
app.mount(
    "/media/uploads",
    StaticFiles(directory=str(settings.upload_dir)),
    name="uploads",
)
app.mount(
    "/media/processed",
    StaticFiles(directory=str(settings.processed_dir)),
    name="processed",
)

# ======================================================================
# ROUTERS
# ======================================================================
app.include_router(detection.router)
app.include_router(camera.router)
app.include_router(camera.settings_router)
app.include_router(statistics.router)
app.include_router(chatbot.router)


# ======================================================================
# HEALTH
# ======================================================================
@app.get("/api/health", tags=["Health"], summary="Cek status sistem")
def health():
    db_ok, db_message = check_connection()
    model = get_model_status()
    return {
        "status": "ok" if db_ok and model["exists"] else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": {"connected": db_ok, "message": db_message},
        "model": {
            "loaded": model["loaded"],
            "exists": model["exists"],
            "path": model["path"],
            "classes": get_class_names(),
            "error": model["error"],
        },
        "camera": webcam_service.get_status(),
        "static": {
            "uploads": str(settings.upload_dir),
            "processed": str(settings.processed_dir),
        },
        "cleanup": {
            "delete_original_image": settings.DELETE_ORIGINAL_IMAGE,
            "delete_original_video": settings.DELETE_ORIGINAL_VIDEO,
            "retention_days": settings.RETENTION_DAYS,
        },
    }


# ======================================================================
# WEBSOCKET
# ======================================================================
@app.websocket("/ws/detection")
async def websocket_detection(websocket: WebSocket):
    await websocket.accept()
    webcam_service.register(websocket)

    try:
        await websocket.send_json(
            {
                "type": "status",
                "camera_status": webcam_service.get_status()["camera_status"],
                "message": "Terhubung ke AI CCTV",
                "state": webcam_service.get_current(include_frame=False),
            }
        )

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.debug("WebSocket error: %s", exc)
    finally:
        webcam_service.unregister(websocket)