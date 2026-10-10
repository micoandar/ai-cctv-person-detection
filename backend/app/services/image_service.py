"""
Image upload detection service.

- Validasi file gambar (ext + ukuran + integritas).
- Inference YOLO → detections + gambar bounding box.
- Simpan original (opsional, sesuai .env) + processed ke disk.
- Simpan hasil ke MySQL.
- Response berisi original & processed sebagai base64 (untuk preview frontend).
"""
import base64
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np
from fastapi import HTTPException

from app.config import settings
from app.database.database import SessionLocal
from app.database.models import DetectionHistory
from app.services.detector import detect_persons, draw_detections

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB


def _to_data_url(image: np.ndarray, quality: int = 85) -> str:
    ok, buf = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def process_image_bytes(
    data: bytes,
    filename: Optional[str],
    confidence: Optional[float] = None,
) -> Dict[str, Any]:
    """Proses 1 file gambar: validasi → YOLO → simpan → response."""
    if not data:
        raise HTTPException(status_code=400, detail="File gambar kosong.")

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Ukuran gambar maksimal 15 MB.")

    ext = Path(filename or "upload.jpg").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Format gambar tidak didukung. Gunakan "
                + ", ".join(sorted(ALLOWED_EXTENSIONS))
            ),
        )

    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="File gambar tidak valid atau rusak.")

    # ---- Inference ----
    try:
        detections, avg_conf, inference_ms = detect_persons(image, conf=confidence)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    annotated = draw_detections(image, detections)

    # ---- Simpan file ----
    uid = uuid.uuid4().hex[:10]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = f"{ts}_{uid}{ext}"
    processed_name = f"{ts}_{uid}_detected.jpg"

    original_path = settings.upload_dir / original_name
    processed_path = settings.processed_dir / processed_name

    # Simpan processed (wajib — ini hasil deteksi)
    cv2.imwrite(str(processed_path), annotated)

    # Simpan original hanya jika dikonfigurasi (default: simpan lalu hapus)
    cv2.imwrite(str(original_path), image)

    detected_at = datetime.now()

    # ---- Hapus file original jika dikonfigurasi ----
    original_path_str: Optional[str] = original_name
    if settings.DELETE_ORIGINAL_IMAGE:
        try:
            original_path.unlink(missing_ok=True)
            original_path_str = None
            logger.debug("Original image dihapus (hemat disk): %s", original_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gagal menghapus original image: %s", exc)
            original_path_str = original_name

    # ---- Simpan ke MySQL ----
    try:
        db = SessionLocal()
        try:
            db.add(
                DetectionHistory(
                    source_type="image",
                    person_count=len(detections),
                    average_confidence=float(avg_conf),
                    detected_at=detected_at,
                    image_path=str(processed_path),
                    session_id=None,
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Gagal menyimpan hasil deteksi gambar ke MySQL: %s. "
            "Pastikan MySQL pada XAMPP sudah berjalan.",
            exc,
        )

    return {
        "person_count": len(detections),
        "average_confidence": avg_conf,
        "detections": detections,
        "original_image": _to_data_url(image),      # base64 — tidak butuh file
        "processed_image": _to_data_url(annotated),
        "image_path": original_path_str,             # None jika dihapus
        "processed_path": processed_name,
        "detected_at": detected_at.isoformat(timespec="seconds"),
        "inference_ms": inference_ms,
    }