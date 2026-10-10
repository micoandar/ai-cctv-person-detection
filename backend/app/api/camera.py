from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from app.config import (
    reset_runtime_settings,
    runtime_settings,
    save_runtime_settings,
    settings,
)
from app.schemas.detection import SettingsPayload, WebcamStartRequest
from app.services.detector import get_class_names, get_model_status
from app.services.webcam_service import webcam_service

router = APIRouter(prefix="/api/webcam", tags=["Webcam"])
settings_router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.post("/start", summary="Mulai kamera laptop")
def start_camera(payload: Optional[WebcamStartRequest] = None):
    payload = payload or WebcamStartRequest()
    try:
        result = webcam_service.start(
            camera_index=payload.camera_index,
            confidence=payload.confidence,
            width=payload.width,
            height=payload.height,
            target_fps=payload.target_fps,
        )
        return {"success": True, **result}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Gagal menjalankan kamera: {exc}") from exc


@router.post("/stop", summary="Hentikan kamera")
def stop_camera():
    return {"success": True, **webcam_service.stop()}


@router.get("/status", summary="Status kamera")
def camera_status() -> Dict[str, Any]:
    return webcam_service.get_status()


def _current_settings() -> Dict[str, Any]:
    model = get_model_status()
    return {
        "confidence_threshold": runtime_settings["confidence_threshold"],
        "iou_threshold": runtime_settings["iou_threshold"],
        "detection_fps": runtime_settings["detection_fps"],
        "camera_index": runtime_settings["camera_index"],
        "camera_width": runtime_settings["camera_width"],
        "camera_height": runtime_settings["camera_height"],
        "stats_save_interval": settings.STATS_SAVE_INTERVAL,
        "model_path": model["path"],
        "model_loaded": model["loaded"],
        "model_exists": model["exists"],
        "model_error": model["error"],
        "class_names": get_class_names(),
        "camera_running": webcam_service.is_running(),
    }


@settings_router.get("", summary="Ambil konfigurasi saat ini")
def get_settings() -> Dict[str, Any]:
    return _current_settings()


@settings_router.put("", summary="Simpan konfigurasi deteksi & kamera")
def update_settings(payload: SettingsPayload) -> Dict[str, Any]:
    if payload.confidence_threshold is not None:
        runtime_settings["confidence_threshold"] = max(
            0.05, min(0.95, float(payload.confidence_threshold))
        )
    if payload.detection_fps is not None:
        runtime_settings["detection_fps"] = max(1, min(30, int(payload.detection_fps)))
    if payload.camera_index is not None:
        runtime_settings["camera_index"] = max(0, int(payload.camera_index))
    if payload.camera_width is not None:
        runtime_settings["camera_width"] = int(payload.camera_width)
    if payload.camera_height is not None:
        runtime_settings["camera_height"] = int(payload.camera_height)

    # ← INI YANG PALING PENTING: persist ke file
    saved = save_runtime_settings()

    return {
        "success": True,
        "saved_to_disk": saved,
        "message": (
            "Pengaturan berhasil disimpan."
            if saved
            else "Pengaturan tersimpan sementara (gagal tulis ke file)."
        ),
        "settings": _current_settings(),
    }


@settings_router.post("/reset", summary="Reset pengaturan ke default .env")
def reset_settings() -> Dict[str, Any]:
    reset_runtime_settings()
    return {
        "success": True,
        "message": "Pengaturan berhasil direset ke default.",
        "settings": _current_settings(),
    }