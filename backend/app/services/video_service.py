"""
Video upload detection service.

- Video diproses di background thread (tidak memblok event loop).
- Setiap frame di-inference dengan YOLO, digambar bounding box,
  lalu ditulis ke video output sementara (mp4v).
- Setelah selesai, video di-transcode ke H.264 + yuv420p agar
  bisa diputar di browser modern.
- Transcode dijalankan SEBELUM broadcast video_completed, supaya
  browser langsung menerima URL file yang sudah H.264.
- Original video dihapus jika DELETE_ORIGINAL_VIDEO=true.
"""
import logging
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import imageio_ffmpeg
from fastapi import HTTPException

from app.config import runtime_settings, settings
from app.database.database import SessionLocal
from app.database.models import DetectionHistory
from app.services.detector import detect_persons, draw_detections

logger = logging.getLogger(__name__)

ALLOWED_VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_VIDEO_SIZE = 200 * 1024 * 1024  # 200 MB
SAMPLE_EVERY_SEC = 1.0              # simpan 1 sample statistik / detik
BROADCAST_EVERY_N_FRAMES = 3        # broadcast progress tiap N frame


# ======================================================================
# Task Registry
# ======================================================================
@dataclass
class VideoTask:
    task_id: str
    filename: str
    original_path: Path
    processed_path: Path
    output_name: str

    status: str = "queued"
    progress: float = 0.0
    processed_frames: int = 0
    total_frames: int = 0
    current_people: int = 0
    error: Optional[str] = None

    width: int = 0
    height: int = 0
    fps: float = 0.0
    duration: float = 0.0

    total_detections: int = 0
    peak_people: int = 0
    min_people: int = 0
    sum_people: int = 0
    sum_confidence: float = 0.0
    confidence_samples: int = 0
    peak_time_seconds: Optional[float] = None

    samples: List[Dict[str, Any]] = field(default_factory=list)
    started_at: float = 0.0
    finished_at: Optional[float] = None
    transcode_ok: bool = False
    original_deleted: bool = False

    def public(self) -> Dict[str, Any]:
        eta = None
        if self.status == "processing" and self.processed_frames > 0:
            elapsed = time.time() - self.started_at
            rate = self.processed_frames / max(elapsed, 0.001)
            remaining = self.total_frames - self.processed_frames
            eta = round(remaining / max(rate, 0.001), 1)

        elapsed = (self.finished_at or time.time()) - (self.started_at or time.time())

        avg_people = self.sum_people / self.processed_frames if self.processed_frames else 0.0
        avg_conf = (
            self.sum_confidence / self.confidence_samples
            if self.confidence_samples
            else 0.0
        )

        # Cache-buster: setiap kali completed, URL unik → bypass browser cache
        cache_buster = int(self.finished_at) if self.finished_at else int(time.time())

        # Original video URL — None jika file sudah dihapus
        original_url = None
        if not self.original_deleted and self.original_path.exists():
            original_url = f"/media/uploads/{self.original_path.name}?t={cache_buster}"

        return {
            "task_id": self.task_id,
            "filename": self.filename,
            "status": self.status,
            "progress": round(self.progress, 2),
            "processed_frames": self.processed_frames,
            "total_frames": self.total_frames,
            "current_people": self.current_people,
            "width": self.width,
            "height": self.height,
            "fps": round(self.fps, 2),
            "duration": round(self.duration, 2),
            "total_detections": self.total_detections,
            "peak_people": self.peak_people,
            "min_people": self.min_people,
            "average_people": round(avg_people, 2),
            "average_confidence": round(avg_conf, 4),
            "peak_time_seconds": self.peak_time_seconds,
            "samples": self.samples,
            "elapsed_seconds": round(elapsed, 2),
            "eta_seconds": eta,
            "video_url": (
                f"/media/processed/{self.output_name}?t={cache_buster}"
                if self.status == "completed"
                else None
            ),
            "original_video_url": original_url,
            "transcode_ok": self.transcode_ok,
            "original_deleted": self.original_deleted,
            "error": self.error,
        }


class VideoTaskManager:
    def __init__(self) -> None:
        self._tasks: Dict[str, VideoTask] = {}
        self._lock = threading.Lock()

    def add(self, task: VideoTask) -> None:
        with self._lock:
            self._tasks[task.task_id] = task

    def get(self, task_id: str) -> Optional[VideoTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def all(self) -> List[VideoTask]:
        with self._lock:
            return list(self._tasks.values())

    def cleanup_old(self, max_age_seconds: int = 3600) -> None:
        now = time.time()
        with self._lock:
            stale = [
                tid
                for tid, t in self._tasks.items()
                if t.finished_at and (now - t.finished_at) > max_age_seconds
            ]
            for tid in stale:
                self._tasks.pop(tid, None)


video_task_manager = VideoTaskManager()


# ======================================================================
# Submit
# ======================================================================
def submit_video(data: bytes, filename: str) -> VideoTask:
    if not data:
        raise HTTPException(status_code=400, detail="File video kosong.")

    if len(data) > MAX_VIDEO_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran video maksimal {MAX_VIDEO_SIZE // (1024 * 1024)} MB.",
        )

    ext = Path(filename or "upload.mp4").suffix.lower()
    if ext not in ALLOWED_VIDEO_EXT:
        raise HTTPException(
            status_code=400,
            detail="Format video tidak didukung. Gunakan "
            + ", ".join(sorted(ALLOWED_VIDEO_EXT)),
        )

    uid = uuid.uuid4().hex[:10]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = f"{ts}_{uid}{ext}"
    output_name = f"{ts}_{uid}_detected.mp4"

    original_path = settings.upload_dir / original_name
    processed_path = settings.processed_dir / output_name

    original_path.write_bytes(data)

    probe = cv2.VideoCapture(str(original_path))
    if not probe.isOpened():
        probe.release()
        try:
            original_path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
        raise HTTPException(status_code=400, detail="File video tidak valid atau rusak.")

    total_frames = int(probe.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(probe.get(cv2.CAP_PROP_FPS) or 0) or 25.0
    width = int(probe.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(probe.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    probe.release()

    task = VideoTask(
        task_id=uid,
        filename=filename,
        original_path=original_path,
        processed_path=processed_path,
        output_name=output_name,
    )
    task.total_frames = total_frames
    task.fps = fps
    task.width = width
    task.height = height
    task.duration = total_frames / fps if fps else 0.0
    task.status = "queued"

    video_task_manager.add(task)

    thread = threading.Thread(
        target=_process_video, args=(task,), name=f"video-{uid}", daemon=True
    )
    thread.start()

    return task


# ======================================================================
# Worker
# ======================================================================
def _process_video(task: VideoTask) -> None:
    from app.services.webcam_service import webcam_service  # hindari circular import

    task.status = "processing"
    task.started_at = time.time()

    _broadcast(webcam_service, {
        "type": "video_progress",
        "task_id": task.task_id,
        "status": "processing",
        "progress": 0.0,
        "processed_frames": 0,
        "total_frames": task.total_frames,
    })

    cap = cv2.VideoCapture(str(task.original_path))
    writer = None
    processing_start = time.perf_counter()

    last_sample_ts = -999.0
    last_broadcast_frame = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break

            # ---------- Inference ----------
            try:
                detections, avg_conf, _ = detect_persons(frame)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Inference error pada video: %s", exc)
                detections, avg_conf = [], 0.0

            annotated = draw_detections(frame, detections, draw_header=True)

            # ---------- Tulis video output (mp4v sementara) ----------
            if writer is None:
                h, w = annotated.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(
                    str(task.processed_path), fourcc, task.fps or 25.0, (w, h)
                )
            writer.write(annotated)

            # ---------- Update statistik ----------
            person_count = len(detections)
            task.processed_frames += 1
            task.current_people = person_count
            task.total_detections += person_count
            task.sum_people += person_count
            if detections:
                task.sum_confidence += avg_conf
                task.confidence_samples += 1

            if person_count > task.peak_people:
                task.peak_people = person_count
                task.peak_time_seconds = round(
                    task.processed_frames / (task.fps or 25.0), 2
                )

            if task.min_people == 0 or person_count < task.min_people:
                task.min_people = person_count

            # ---------- Sampling tiap N detik ----------
            current_ts = task.processed_frames / (task.fps or 25.0)
            if current_ts - last_sample_ts >= SAMPLE_EVERY_SEC:
                last_sample_ts = current_ts
                task.samples.append(
                    {
                        "frame_index": task.processed_frames,
                        "timestamp": round(current_ts, 2),
                        "person_count": person_count,
                        "average_confidence": round(avg_conf, 4),
                    }
                )

            # ---------- Progress ----------
            if task.total_frames > 0:
                task.progress = min(
                    100.0, (task.processed_frames / task.total_frames) * 100.0
                )

            # ---------- Broadcast berkala ----------
            if task.processed_frames - last_broadcast_frame >= BROADCAST_EVERY_N_FRAMES:
                last_broadcast_frame = task.processed_frames
                _broadcast(webcam_service, {
                    "type": "video_progress",
                    "task_id": task.task_id,
                    "status": "processing",
                    "progress": round(task.progress, 2),
                    "processed_frames": task.processed_frames,
                    "total_frames": task.total_frames,
                    "current_people": person_count,
                    "elapsed_seconds": round(time.time() - task.started_at, 1),
                })

    except Exception as exc:  # noqa: BLE001
        logger.exception("Gagal memproses video: %s", exc)
        task.status = "failed"
        task.error = str(exc)
        task.finished_at = time.time()
        _broadcast(webcam_service, {
            "type": "video_failed",
            "task_id": task.task_id,
            "error": str(exc),
        })
        _safe_release(cap, writer)
        return

    # ==============================================================
    # Frame loop selesai → release → transcode → broadcast
    # ==============================================================
    _safe_release(cap, writer)

    # Notif: transcode mulai
    _broadcast(webcam_service, {
        "type": "video_progress",
        "task_id": task.task_id,
        "status": "transcoding",
        "progress": 99.0,
        "processed_frames": task.processed_frames,
        "total_frames": task.total_frames,
        "current_people": task.current_people,
        "elapsed_seconds": round(time.time() - task.started_at, 1),
    })

    task.status = "transcoding"
    transcode_ok = False
    if task.processed_path.exists():
        temp_h264 = task.processed_path.with_suffix(".h264.mp4")
        logger.info("Transcoding %s → H.264 ...", task.processed_path.name)
        t0 = time.time()
        transcode_ok = _transcode_to_h264(task.processed_path, temp_h264)
        if transcode_ok:
            try:
                task.processed_path.unlink()
            except Exception:  # noqa: BLE001
                pass
            temp_h264.rename(task.processed_path)
            logger.info(
                "Transcode selesai dalam %.1fs → %s",
                time.time() - t0,
                task.processed_path.name,
            )
        else:
            logger.warning(
                "Transcode gagal, file tetap mp4v (tidak bisa diputar di browser)."
            )
            if temp_h264.exists():
                try:
                    temp_h264.unlink()
                except Exception:  # noqa: BLE001
                    pass

    task.transcode_ok = transcode_ok

    # ---------- Hapus original video jika dikonfigurasi ----------
    if settings.DELETE_ORIGINAL_VIDEO:
        try:
            if task.original_path.exists():
                task.original_path.unlink()
                task.original_deleted = True
                logger.info("Original video dihapus: %s", task.original_path.name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gagal menghapus original video: %s", exc)
            task.original_deleted = False

    task.progress = 100.0
    task.status = "completed"
    task.finished_at = time.time()

    _save_to_database(task)

    # ---------- Broadcast SETELAH transcode selesai ----------
    public = task.public()
    public["processing_ms"] = round(
        (time.perf_counter() - processing_start) * 1000.0, 2
    )

    _broadcast(webcam_service, {
        "type": "video_completed",
        "task_id": task.task_id,
        "result": public,
    })

    logger.info(
        "Video %s selesai. Frame=%d, peak=%d, avg=%.2f, transcode_ok=%s, original_deleted=%s",
        task.task_id, task.processed_frames, task.peak_people,
        task.sum_people / max(task.processed_frames, 1),
        transcode_ok, task.original_deleted,
    )


def _safe_release(cap, writer) -> None:
    try:
        if cap is not None:
            cap.release()
    except Exception:  # noqa: BLE001
        pass
    try:
        if writer is not None:
            writer.release()
    except Exception:  # noqa: BLE001
        pass


# ======================================================================
# Broadcast (reuse dari webcam_service)
# ======================================================================
def _broadcast(webcam_service, payload: Dict[str, Any]) -> None:
    try:
        webcam_service._broadcast(payload)  # noqa: SLF001
    except Exception:  # noqa: BLE001
        logger.debug("Broadcast video gagal (mungkin tidak ada client).")


# ======================================================================
# Transcode ke H.264 (browser-compatible)
# ======================================================================
def _transcode_to_h264(src: Path, dst: Path) -> bool:
    """Konversi video mp4v (MPEG-4 Part 2) ke H.264 + yuv420p."""
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        logger.error("ffmpeg binary tidak tersedia: %s", exc)
        return False

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(src),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        str(dst),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=1800, check=False,
        )
        if result.returncode != 0:
            logger.error(
                "ffmpeg gagal (code=%s): %s",
                result.returncode,
                result.stderr.decode("utf-8", errors="ignore")[-500:],
            )
            return False
        return dst.exists() and dst.stat().st_size > 0
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timeout saat transcode %s", src)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.exception("Transcode error: %s", exc)
        return False


# ======================================================================
# Simpan ke MySQL
# ======================================================================
def _save_to_database(task: VideoTask) -> None:
    db = SessionLocal()
    try:
        base_time = datetime.now()
        avg_conf = (
            task.sum_confidence / task.confidence_samples
            if task.confidence_samples
            else 0.0
        )
        db.add(
            DetectionHistory(
                source_type="video",
                person_count=int(task.peak_people),
                average_confidence=float(avg_conf),
                detected_at=base_time,
                image_path=str(task.processed_path),
                session_id=task.task_id,
            )
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error(
            "Gagal menyimpan hasil video ke MySQL: %s. "
            "Pastikan MySQL pada XAMPP sudah berjalan.",
            exc,
        )
    finally:
        db.close()