from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.detection import VideoDetectionResponse
from app.services import video_service
from app.services.image_service import process_image_bytes

router = APIRouter(prefix="/api/detection", tags=["Detection"])


# ======================================================================
# IMAGE DETECTION
# ======================================================================
@router.post("/image", summary="Deteksi person pada gambar yang di-upload")
def detect_image(
    file: UploadFile = File(..., description="File gambar (jpg, jpeg, png, bmp, webp)"),
    confidence: Optional[float] = Form(None, description="Confidence threshold (0.05 - 0.95)"),
):
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="File gambar wajib dikirim.")

    if confidence is not None:
        confidence = max(0.05, min(0.95, float(confidence)))

    try:
        data = file.file.read()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Gagal membaca file: {exc}") from exc
    finally:
        try:
            file.file.close()
        except Exception:  # noqa: BLE001
            pass

    return process_image_bytes(data, file.filename, confidence)


# ======================================================================
# VIDEO DETECTION
# ======================================================================
@router.post(
    "/video",
    response_model=VideoDetectionResponse,
    summary="Upload video untuk deteksi person (diproses di background)",
)
def detect_video(
    file: UploadFile = File(
        ...,
        description="File video (mp4, avi, mov, mkv, webm), maksimal 200 MB",
    ),
):
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="File video wajib dikirim.")

    try:
        data = file.file.read()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Gagal membaca file: {exc}") from exc
    finally:
        try:
            file.file.close()
        except Exception:  # noqa: BLE001
            pass

    task = video_service.submit_video(data, file.filename)
    return task.public()


@router.get(
    "/video/{task_id}",
    response_model=VideoDetectionResponse,
    summary="Cek status & hasil deteksi video",
)
def get_video_result(task_id: str):
    task = video_service.video_task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task video tidak ditemukan.")
    return task.public()