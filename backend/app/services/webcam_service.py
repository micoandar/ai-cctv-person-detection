"""
Webcam service.

- Membuka webcam lewat OpenCV (cv2.VideoCapture).
- Menjalankan inference YOLO pada thread terpisah (tidak memblok event loop).
- Broadcast hasil + frame ter-anotasi ke semua WebSocket client.
- Menyimpan statistik ke MySQL secara berkala dengan interval ADAPTIF:
    * Ada orang   → simpan tiap STATS_SAVE_INTERVAL detik (default 5s)
    * 0 orang     → simpan tiap ZERO_HEARTBEAT_INTERVAL detik (default 60s)
  Tujuannya: hindari database penuh record "0 orang" berulang, tapi tetap
  ada heartbeat bahwa kamera masih berjalan.
"""
import asyncio
import base64
import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Set

import cv2

from app.config import runtime_settings, settings
from app.database.database import SessionLocal
from app.database.models import DetectionHistory
from app.services.detector import detect_persons, draw_detections

logger = logging.getLogger(__name__)

# Interval simpan saat 0 orang (heartbeat — tanda kamera masih jalan)
ZERO_HEARTBEAT_INTERVAL = 60  # detik


class WebcamService:
    def __init__(self) -> None:
        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._clients: Set[Any] = set()
        self._clients_lock = threading.Lock()
        self._state_lock = threading.Lock()

        self._running = False
        self._session_id: Optional[str] = None
        self._error: Optional[str] = None
        self._fps = 0.0
        self._last_save = 0.0
        self._last_saved_count: Optional[int] = None

        self._current: Dict[str, Any] = self._empty_state()

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _empty_state() -> Dict[str, Any]:
        return {
            "type": "detection",
            "person_count": 0,
            "fps": 0.0,
            "average_confidence": 0.0,
            "detections": [],
            "camera_status": "OFFLINE",
            "frame": None,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # ------------------------------------------------------------------
    # WebSocket clients
    # ------------------------------------------------------------------
    def register(self, websocket) -> None:
        with self._clients_lock:
            self._clients.add(websocket)
        logger.info("WebSocket client terhubung (total=%d)", len(self._clients))

    def unregister(self, websocket) -> None:
        with self._clients_lock:
            self._clients.discard(websocket)
        logger.info("WebSocket client terputus (total=%d)", len(self._clients))

    def client_count(self) -> int:
        with self._clients_lock:
            return len(self._clients)

    def _broadcast(self, payload: Dict[str, Any]) -> None:
        with self._clients_lock:
            clients = list(self._clients)
        if not clients or self._loop is None or self._loop.is_closed():
            return

        data = json.dumps(payload, default=str)
        for ws in clients:
            asyncio.run_coroutine_threadsafe(self._safe_send(ws, data), self._loop)

    async def _safe_send(self, websocket, data: str) -> None:
        try:
            await websocket.send_text(data)
        except Exception:  # noqa: BLE001
            self.unregister(websocket)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def is_running(self) -> bool:
        return self._running

    def get_current(self, include_frame: bool = False) -> Dict[str, Any]:
        with self._state_lock:
            state = dict(self._current)
        if not include_frame:
            state.pop("frame", None)
        return state

    def get_status(self) -> Dict[str, Any]:
        with self._state_lock:
            state = dict(self._current)
        return {
            "running": self._running,
            "camera_status": "ONLINE" if self._running else "OFFLINE",
            "session_id": self._session_id,
            "person_count": state.get("person_count", 0),
            "fps": state.get("fps", 0.0),
            "average_confidence": state.get("average_confidence", 0.0),
            "error": self._error,
            "clients": self.client_count(),
        }

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------
    def start(
        self,
        camera_index: Optional[int] = None,
        confidence: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        target_fps: Optional[int] = None,
    ) -> Dict[str, Any]:
        if self._running:
            return {
                "running": True,
                "message": "Kamera sudah berjalan",
                "session_id": self._session_id,
            }

        if camera_index is not None:
            runtime_settings["camera_index"] = int(camera_index)
        if confidence is not None:
            runtime_settings["confidence_threshold"] = float(confidence)
        if width is not None:
            runtime_settings["camera_width"] = int(width)
        if height is not None:
            runtime_settings["camera_height"] = int(height)
        if target_fps is not None:
            runtime_settings["detection_fps"] = int(target_fps)

        index = int(runtime_settings["camera_index"])
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(
                "Webcam tidak tersedia. Pastikan kamera tidak sedang dipakai "
                "aplikasi lain dan browser/aplikasi memiliki izin kamera."
            )

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(runtime_settings["camera_width"]))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(runtime_settings["camera_height"]))
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._cap = cap
        self._stop_event.clear()
        self._session_id = uuid.uuid4().hex[:12]
        self._fps = 0.0
        self._error = None
        self._last_save = time.time()
        self._last_saved_count = None
        self._running = True

        with self._state_lock:
            self._current = self._empty_state()
            self._current["camera_status"] = "ONLINE"

        self._thread = threading.Thread(
            target=self._run, name="webcam-worker", daemon=True
        )
        self._thread.start()

        self._broadcast(
            {
                "type": "status",
                "camera_status": "ONLINE",
                "session_id": self._session_id,
                "message": "Kamera dimulai",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )

        logger.info("Webcam dimulai (index=%s, session=%s)", index, self._session_id)
        return {
            "running": True,
            "session_id": self._session_id,
            "message": "Kamera berhasil dijalankan",
        }

    def stop(self) -> Dict[str, Any]:
        if not self._running and self._thread is None:
            return {"running": False, "message": "Kamera tidak sedang berjalan"}

        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=6)
        self._thread = None
        self._running = False

        self._broadcast(
            {
                "type": "status",
                "camera_status": "OFFLINE",
                "message": "Kamera dihentikan",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )
        logger.info("Webcam dihentikan")
        return {"running": False, "message": "Kamera dihentikan"}

    def _release_camera(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:  # noqa: BLE001
                pass
            self._cap = None

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------
    def _run(self) -> None:
        frame_interval = 1.0 / max(1, int(runtime_settings["detection_fps"]))
        logger.info("Worker webcam berjalan (target %.1f FPS)", 1.0 / frame_interval)

        try:
            while not self._stop_event.is_set():
                loop_start = time.perf_counter()

                if self._cap is None:
                    break

                ok, frame = self._cap.read()
                if not ok or frame is None:
                    self._error = "Gagal membaca frame dari kamera."
                    logger.warning(self._error)
                    time.sleep(0.3)
                    continue

                self._error = None

                # ---- Inference ----
                try:
                    detections, avg_conf, _ = detect_persons(frame)
                except FileNotFoundError as exc:
                    self._error = str(exc)
                    logger.error(self._error)
                    time.sleep(1.0)
                    continue
                except Exception as exc:  # noqa: BLE001
                    self._error = f"Inference error: {exc}"
                    logger.exception(self._error)
                    detections, avg_conf = [], 0.0

                annotated = draw_detections(frame, detections)

                # ---- FPS (smoothed) ----
                elapsed = time.perf_counter() - loop_start
                inst_fps = 1.0 / elapsed if elapsed > 0 else 0.0
                self._fps = (
                    inst_fps if self._fps <= 0 else (self._fps * 0.8 + inst_fps * 0.2)
                )

                # ---- Encode frame hanya jika ada client ----
                frame_data_url = None
                if self.client_count() > 0:
                    frame_data_url = self._encode_frame(annotated)

                payload = {
                    "type": "detection",
                    "person_count": len(detections),
                    "fps": round(self._fps, 1),
                    "average_confidence": avg_conf,
                    "detections": detections,
                    "camera_status": "ONLINE",
                    "frame": frame_data_url,
                    "session_id": self._session_id,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }

                with self._state_lock:
                    self._current = payload

                self._broadcast(payload)

                # ---- Simpan statistik (interval adaptif) ----
                self._maybe_save_statistics(len(detections), avg_conf)

                # ---- Batasi FPS inference ----
                sleep_for = frame_interval - (time.perf_counter() - loop_start)
                if sleep_for > 0:
                    time.sleep(sleep_for)

        finally:
            self._release_camera()
            self._running = False

            offline = self._empty_state()
            offline["camera_status"] = "OFFLINE"
            offline["timestamp"] = datetime.now().isoformat(timespec="seconds")
            with self._state_lock:
                self._current = offline

            self._broadcast(
                {
                    "type": "status",
                    "camera_status": "OFFLINE",
                    "message": "Kamera berhenti",
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
            )
            logger.info("Worker webcam selesai")

    # ------------------------------------------------------------------
    # Statistik: interval adaptif
    # ------------------------------------------------------------------
    def _maybe_save_statistics(self, person_count: int, avg_conf: float) -> None:
        """
        Tentukan apakah perlu simpan statistik ke DB.

        Aturan:
        - person_count > 0  → interval = STATS_SAVE_INTERVAL (default 5s)
        - person_count == 0 → interval = ZERO_HEARTBEAT_INTERVAL (default 60s)

        Tujuannya mengurangi record "0 orang" yang berulang-ulang.
        """
        now = time.time()

        # Interval simpan berdasarkan kondisi saat ini
        if person_count > 0:
            interval = int(settings.STATS_SAVE_INTERVAL)
        else:
            interval = ZERO_HEARTBEAT_INTERVAL

        elapsed = now - self._last_save
        if elapsed < interval:
            return

        # Simpan
        self._last_save = now
        self._last_saved_count = person_count
        self._save_statistics(person_count, avg_conf)

    def _save_statistics(self, person_count: int, avg_conf: float) -> None:
        """Simpan 1 baris statistik ke MySQL."""
        db = SessionLocal()
        try:
            db.add(
                DetectionHistory(
                    source_type="webcam",
                    person_count=int(person_count),
                    average_confidence=float(avg_conf),
                    detected_at=datetime.now(),
                    session_id=self._session_id,
                )
            )
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.error(
                "Gagal menyimpan statistik webcam ke MySQL: %s. "
                "Pastikan MySQL pada XAMPP sudah berjalan.",
                exc,
            )
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------------
    @staticmethod
    def _encode_frame(frame) -> Optional[str]:
        try:
            h, w = frame.shape[:2]
            max_w = int(settings.STREAM_MAX_WIDTH)
            if w > max_w:
                scale = max_w / float(w)
                frame = cv2.resize(
                    frame,
                    (int(w * scale), int(h * scale)),
                    interpolation=cv2.INTER_AREA,
                )
            ok, buf = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), int(settings.JPEG_QUALITY)],
            )
            if not ok:
                return None
            return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode(
                "ascii"
            )
        except Exception:  # noqa: BLE001
            logger.exception("Gagal encode frame")
            return None


# Singleton
webcam_service = WebcamService()