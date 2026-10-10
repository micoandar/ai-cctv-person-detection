"""
Detector YOLO.

ATURAN PENTING:
- Model di-load SEKALI saja (lazy singleton, thread-safe).
- Tidak boleh load model per request / per frame.
"""
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.config import runtime_settings, settings

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()
_model_error: Optional[str] = None


# ----------------------------------------------------------------------
# Model loading
# ----------------------------------------------------------------------
def load_model():
    """Load model YOLO sekali saja (thread-safe)."""
    global _model, _model_error

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        model_path = settings.model_absolute_path
        if not model_path.exists():
            _model_error = (
                f"Model YOLO tidak ditemukan di '{model_path}'. "
                "Pastikan file best.pt sudah diletakkan pada folder backend/models/."
            )
            logger.error(_model_error)
            raise FileNotFoundError(_model_error)

        try:
            from ultralytics import YOLO  # import lambat, dilakukan di sini

            logger.info("Memuat model YOLO dari %s ...", model_path)
            t0 = time.time()
            _model = YOLO(str(model_path))
            _model_error = None
            logger.info("Model berhasil dimuat dalam %.2f detik", time.time() - t0)
        except Exception as exc:  # noqa: BLE001
            _model_error = f"Gagal memuat model YOLO: {exc}"
            logger.exception(_model_error)
            raise

        return _model


def get_model_status() -> Dict[str, Any]:
    return {
        "loaded": _model is not None,
        "path": str(settings.model_absolute_path),
        "exists": settings.model_absolute_path.exists(),
        "error": _model_error,
    }


def get_class_names() -> List[str]:
    try:
        model = load_model()
        names = model.names
        if isinstance(names, dict):
            return [names[k] for k in sorted(names.keys())]
        return list(names)
    except Exception:  # noqa: BLE001
        return []


# ----------------------------------------------------------------------
# Inference
# ----------------------------------------------------------------------
def detect_persons(
    image: np.ndarray,
    conf: Optional[float] = None,
    iou: Optional[float] = None,
    imgsz: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], float, float]:
    """
    Jalankan inference pada satu frame/gambar.

    Returns:
        (detections, average_confidence, inference_ms)
    """
    model = load_model()

    conf = float(conf) if conf is not None else float(runtime_settings["confidence_threshold"])
    iou = float(iou) if iou is not None else float(runtime_settings["iou_threshold"])
    imgsz = int(imgsz) if imgsz is not None else int(settings.IMAGE_SIZE)

    t0 = time.perf_counter()
    results = model.predict(
        source=image,
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        verbose=False,
    )
    inference_ms = (time.perf_counter() - t0) * 1000.0

    if not results:
        return [], 0.0, inference_ms

    result = results[0]
    names = result.names
    detections: List[Dict[str, Any]] = []

    boxes = getattr(result, "boxes", None)
    if boxes is not None:
        for box in boxes:
            try:
                cls_id = int(box.cls[0].item())
            except Exception:  # noqa: BLE001
                continue

            if isinstance(names, dict):
                class_name = names.get(cls_id, str(cls_id))
            else:
                class_name = names[cls_id] if cls_id < len(names) else str(cls_id)

            # Model hanya punya 1 class: person
            if class_name != settings.PERSON_CLASS_NAME:
                continue

            xyxy = box.xyxy[0].tolist()
            x1, y1, x2, y2 = (float(v) for v in xyxy)
            confidence = float(box.conf[0].item())

            detections.append(
                {
                    "class": class_name,
                    "confidence": round(confidence, 4),
                    "bbox": {
                        "x1": round(x1, 1),
                        "y1": round(y1, 1),
                        "x2": round(x2, 1),
                        "y2": round(y2, 1),
                    },
                }
            )

    detections.sort(key=lambda d: d["confidence"], reverse=True)
    avg_conf = (
        round(sum(d["confidence"] for d in detections) / len(detections), 4)
        if detections
        else 0.0
    )
    return detections, avg_conf, round(inference_ms, 2)


# ----------------------------------------------------------------------
# Drawing
# ----------------------------------------------------------------------
BOX_COLOR = (127, 255, 0)      # BGR - hijau neon
TEXT_COLOR = (13, 18, 32)      # BGR - gelap


def draw_detections(
    image: np.ndarray,
    detections: List[Dict[str, Any]],
    draw_header: bool = True,
) -> np.ndarray:
    """Gambar bounding box + label pada image."""
    annotated = image.copy()

    for idx, det in enumerate(detections, start=1):
        b = det["bbox"]
        p1 = (int(b["x1"]), int(b["y1"]))
        p2 = (int(b["x2"]), int(b["y2"]))

        cv2.rectangle(annotated, p1, p2, BOX_COLOR, 2)

        label = f"Person #{idx}  {det['confidence'] * 100:.0f}%"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_y1 = max(0, p1[1] - th - 10)
        cv2.rectangle(
            annotated, (p1[0], label_y1), (p1[0] + tw + 10, label_y1 + th + 10),
            BOX_COLOR, -1,
        )
        cv2.putText(
            annotated, label, (p1[0] + 5, label_y1 + th + 3),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_COLOR, 1, cv2.LINE_AA,
        )

    if draw_header:
        header = f"Person Detected: {len(detections)}"
        cv2.putText(
            annotated, header, (14, 34),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 5, cv2.LINE_AA,
        )
        cv2.putText(
            annotated, header, (14, 34),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, BOX_COLOR, 2, cv2.LINE_AA,
        )

    return annotated