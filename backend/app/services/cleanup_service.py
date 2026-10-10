"""
Cleanup service — hapus file processed/uploads yang lebih tua dari RETENTION_DAYS.

Dijalankan sekali saat startup dan setiap 6 jam via background task.
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

CHECK_INTERVAL_HOURS = 6


def _cleanup_dir(directory: Path, max_age_days: int) -> int:
    """Hapus file di directory yang lebih tua dari max_age_days."""
    if not directory.exists() or max_age_days <= 0:
        return 0

    cutoff = time.time() - (max_age_days * 86400)
    deleted = 0

    for f in directory.iterdir():
        if not f.is_file():
            continue
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gagal hapus %s: %s", f.name, exc)

    return deleted


def run_cleanup() -> dict:
    """Hapus file lama dari uploads & processed."""
    days = int(settings.RETENTION_DAYS)
    if days <= 0:
        return {"enabled": False}

    u = _cleanup_dir(settings.upload_dir, days)
    p = _cleanup_dir(settings.processed_dir, days)

    result = {
        "enabled": True,
        "retention_days": days,
        "deleted_uploads": u,
        "deleted_processed": p,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }
    if u or p:
        logger.info(
            "Cleanup selesai: %d file dihapus dari uploads, %d dari processed.",
            u, p,
        )
    return result


def start_background_cleanup():
    """Jalankan cleanup di background thread, sekali saat startup + tiap 6 jam."""
    def worker():
        # Delay awal 30 detik supaya server sudah siap
        time.sleep(30)
        while True:
            try:
                run_cleanup()
            except Exception as exc:  # noqa: BLE001
                logger.exception("Cleanup error: %s", exc)
            time.sleep(CHECK_INTERVAL_HOURS * 3600)

    thread = threading.Thread(target=worker, name="cleanup-worker", daemon=True)
    thread.start()
    logger.info(
        "Cleanup worker aktif (retention=%d hari, interval=%d jam).",
        settings.RETENTION_DAYS,
        CHECK_INTERVAL_HOURS,
    )