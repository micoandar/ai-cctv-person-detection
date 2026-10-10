"""
CCTV AI Assistant — Context-Aware.

Alur:
User Question + page_context -> Intent Detection
    -> Query MySQL / Current State (sesuai konteks halaman)
    -> Context -> (Opsional) LLM -> Natural Language Response

page_context:
- "live"    -> prioritaskan state kamera (webcam)
- "video"   -> prioritaskan riwayat deteksi video
- "image"   -> prioritaskan riwayat deteksi gambar
- "general" -> semua sumber (untuk dashboard, history, statistics)

LLM TIDAK BOLEH MENGARANG DATA. Semua angka berasal dari MySQL /
state deteksi. Jika LLM tidak dikonfigurasi, dipakai template jawaban.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import DetectionHistory
from app.services import statistics_service
from app.services.webcam_service import webcam_service

logger = logging.getLogger(__name__)


VALID_PAGE_CONTEXTS = {"live", "video", "image", "general"}

_SOURCE_LABEL = {
    "webcam": "kamera webcam",
    "image": "gambar yang di-upload",
    "video": "video yang di-upload",
}

_CONTEXT_TITLE = {
    "live": "Live Monitoring",
    "video": "Video Detection",
    "image": "Image Detection",
    "general": "AI CCTV",
}


# ======================================================================
# 1. INTENT DETECTION
# ======================================================================
def _has(text: str, *keywords: str) -> bool:
    return any(k in text for k in keywords)


def _extract_window(text: str) -> Optional[Tuple[int, str]]:
    m = re.search(r"(\d+)\s*(menit|minute|minutes|min|jam|hour|hours|j)\b", text)
    if not m:
        return None
    value = int(m.group(1))
    unit_raw = m.group(2)
    unit = "minutes" if unit_raw in ("menit", "minute", "minutes", "min") else "hours"
    return value, unit


def _extract_number(text: str) -> Optional[int]:
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else None


def detect_intent(question: str) -> Tuple[str, Dict[str, Any]]:
    t = (question or "").lower().strip()
    params: Dict[str, Any] = {}

    window = _extract_window(t)
    if window:
        params["window_value"], params["window_unit"] = window

    # --- CAMERA STATUS ---
    if _has(t, "status kamera", "kamera aktif", "kamera nyala", "kamera mati",
            "kamera online", "camera status", "kamera berjalan", "camera on", "camera off"):
        return "CAMERA_STATUS", params
    if _has(t, "kamera", "camera", "webcam") and _has(
        t, "status", "aktif", "online", "mati", "nyala", "berjalan", "off"
    ):
        return "CAMERA_STATUS", params

    # --- LAST IMAGE ---
    if _has(t, "gambar terakhir", "image terakhir", "foto terakhir",
            "last image", "dari gambar", "hasil upload gambar"):
        return "LAST_IMAGE_DETECTION", params

    # --- LAST VIDEO ---
    if _has(t, "video terakhir", "last video", "dari video", "hasil video"):
        return "LAST_VIDEO_DETECTION", params

    # --- TREND ---
    if _has(t, "meningkat", "menurun", "naik", "turun", "trend", "tren",
            "increasing", "decreasing", "semakin banyak", "semakin sedikit"):
        return "TREND_ANALYSIS", params

    # --- HISTORY (time window) ---
    if window and _has(t, "terakhir", "last", "terbaru", "belakangan"):
        return "HISTORY_COUNT", params

    # --- COUNT ABOVE THRESHOLD ---
    if _has(t, "lebih dari", "di atas", "diatas", "above", "more than", "melebihi"):
        params["threshold"] = _extract_number(t) or 10
        return "COUNT_ABOVE_THRESHOLD", params

    # --- PEAK TIME ---
    if _has(t, "jam berapa", "pukul berapa", "kapan", "what time", "waktu puncak", "peak time"):
        return "PEAK_TIME", params

    # --- CURRENT ---
    if _has(t, "sekarang", "saat ini", "current", "right now", "now", "detik ini"):
        return "CURRENT_COUNT", params

    # --- MAX ---
    if _has(t, "terbanyak", "tertinggi", "maksimal", "maximum", " max", "peak",
            "paling banyak", "highest", "puncak"):
        return "MAX_COUNT", params

    # --- MIN ---
    if _has(t, "tersedikit", "terendah", "minimum", "paling sedikit", "lowest"):
        return "MIN_COUNT", params

    # --- AVERAGE ---
    if _has(t, "rata-rata", "rata rata", "average", "mean", "rerata"):
        return "AVERAGE_COUNT", params

    # --- Fallback umum ---
    if _has(t, "berapa", "how many", "jumlah", "count", "total"):
        return "CURRENT_COUNT", params

    return "UNKNOWN", params


# ======================================================================
# 2. HELPERS
# ======================================================================
def _fmt_time(dt: Optional[datetime]) -> str:
    if not dt:
        return "-"
    return dt.strftime("%d %b %Y %H:%M:%S")


def _ago_str(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    secs = int((datetime.now() - dt).total_seconds())
    if secs < 5:
        return "baru saja"
    if secs < 60:
        return f"{secs} detik lalu"
    if secs < 3600:
        return f"{secs // 60} menit lalu"
    if secs < 86400:
        return f"{secs // 3600} jam lalu"
    return f"{secs // 86400} hari lalu"


def _context_intro(page_context: str) -> str:
    """Awalan kalimat sesuai konteks halaman."""
    title = _CONTEXT_TITLE.get(page_context, "AI CCTV")
    return f"[{title}]"


def _normalize_context(raw: Optional[str]) -> str:
    if not raw:
        return "general"
    ctx = str(raw).strip().lower()
    return ctx if ctx in VALID_PAGE_CONTEXTS else "general"


# ======================================================================
# 3. CONTEXT-AWARE: LATEST RECORD
# ======================================================================
def _latest_record_for_context(
    db: Session, page_context: str
) -> Optional[DetectionHistory]:
    """Ambil record terakhir sesuai konteks halaman."""
    if page_context == "video":
        return statistics_service.latest_record(db, source_type="video")
    if page_context == "image":
        return statistics_service.latest_record(db, source_type="image")
    if page_context == "live":
        return statistics_service.latest_record(db, source_type="webcam")
    # general -> semua sumber
    return statistics_service.latest_record(db, source_type=None)


# ======================================================================
# 4. BUILD ANSWER
# ======================================================================
def _build_answer(
    db: Session,
    intent: str,
    params: Dict[str, Any],
    page_context: str,
) -> Tuple[str, Dict[str, Any]]:
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # =====================================================
    # CURRENT_COUNT — paling banyak dipengaruhi page_context
    # =====================================================
    if intent == "CURRENT_COUNT":
        # --- LIVE: pakai state kamera ---
        if page_context == "live":
            state = webcam_service.get_current(include_frame=False)
            count = int(state.get("person_count", 0))
            status = state.get("camera_status", "OFFLINE")

            if status == "ONLINE":
                return (
                    f"Saat ini kamera mendeteksi {count} orang secara real-time.",
                    {
                        "person_count": count,
                        "camera_status": status,
                        "page_context": page_context,
                    },
                )

            # kamera offline → fallback ke record webcam terakhir
            recent = statistics_service.latest_record(db, source_type="webcam")
            if recent:
                return (
                    f"Kamera sedang OFFLINE. Deteksi webcam terakhir tercatat "
                    f"{recent.person_count} orang pada {_fmt_time(recent.detected_at)} "
                    f"({_ago_str(recent.detected_at)}). "
                    f"Silakan jalankan kamera dari halaman Live Monitoring.",
                    {
                        "person_count": int(recent.person_count),
                        "camera_status": status,
                        "detected_at": recent.detected_at.isoformat(timespec="seconds"),
                        "page_context": page_context,
                    },
                )
            return (
                "Kamera sedang OFFLINE dan belum ada deteksi webcam yang tersimpan. "
                "Silakan jalankan kamera dari halaman Live Monitoring.",
                {"person_count": 0, "camera_status": status, "page_context": page_context},
            )

        # --- VIDEO: pakai record video terakhir ---
        if page_context == "video":
            recent = statistics_service.latest_record(db, source_type="video")
            if recent:
                return (
                    f"Pada video terakhir yang di-upload, terdeteksi hingga "
                    f"{recent.person_count} orang (peak), dengan rata-rata confidence "
                    f"{recent.average_confidence * 100:.0f}%. "
                    f"Diproses pada {_fmt_time(recent.detected_at)} ({_ago_str(recent.detected_at)}).",
                    {
                        "person_count": int(recent.person_count),
                        "average_confidence": round(recent.average_confidence or 0.0, 4),
                        "detected_at": recent.detected_at.isoformat(timespec="seconds"),
                        "source": "video",
                        "page_context": page_context,
                    },
                )
            return (
                "Belum ada video yang di-upload untuk dideteksi. "
                "Silakan upload video di halaman Video Detection.",
                {"person_count": 0, "source": "video", "page_context": page_context},
            )

        # --- IMAGE: pakai record image terakhir ---
        if page_context == "image":
            recent = statistics_service.latest_record(db, source_type="image")
            if recent:
                return (
                    f"Pada gambar terakhir yang di-upload, terdeteksi "
                    f"{recent.person_count} orang dengan rata-rata confidence "
                    f"{recent.average_confidence * 100:.0f}%. "
                    f"Diproses pada {_fmt_time(recent.detected_at)} ({_ago_str(recent.detected_at)}).",
                    {
                        "person_count": int(recent.person_count),
                        "average_confidence": round(recent.average_confidence or 0.0, 4),
                        "detected_at": recent.detected_at.isoformat(timespec="seconds"),
                        "source": "image",
                        "page_context": page_context,
                    },
                )
            return (
                "Belum ada gambar yang di-upload untuk dideteksi. "
                "Silakan upload gambar di halaman Image Detection.",
                {"person_count": 0, "source": "image", "page_context": page_context},
            )

        # --- GENERAL: cek kamera dulu, lalu record terbaru apa saja ---
        state = webcam_service.get_current(include_frame=False)
        status = state.get("camera_status", "OFFLINE")
        if status == "ONLINE":
            count = int(state.get("person_count", 0))
            return (
                f"Saat ini kamera mendeteksi {count} orang secara real-time.",
                {
                    "person_count": count,
                    "camera_status": status,
                    "page_context": page_context,
                },
            )

        recent = statistics_service.latest_record(db)
        if recent:
            src_label = _SOURCE_LABEL.get(recent.source_type, recent.source_type)
            return (
                f"Kamera sedang OFFLINE. Deteksi terakhir berasal dari {src_label}, "
                f"tercatat {recent.person_count} orang pada {_fmt_time(recent.detected_at)} "
                f"({_ago_str(recent.detected_at)}).",
                {
                    "person_count": int(recent.person_count),
                    "camera_status": status,
                    "source": recent.source_type,
                    "detected_at": recent.detected_at.isoformat(timespec="seconds"),
                    "page_context": page_context,
                },
            )
        return (
            "Belum ada data deteksi. Jalankan kamera, upload gambar, atau upload video.",
            {"person_count": 0, "page_context": page_context},
        )

    # =====================================================
    # LAST IMAGE / LAST VIDEO — eksplisit
    # =====================================================
    if intent == "LAST_IMAGE_DETECTION":
        row = statistics_service.latest_record(db, source_type="image")
        if not row:
            return (
                "Belum ada gambar yang di-upload untuk dideteksi.",
                {"person_count": 0, "page_context": page_context},
            )
        return (
            f"Pada gambar terakhir yang di-upload ({_fmt_time(row.detected_at)}), "
            f"terdeteksi {row.person_count} orang dengan rata-rata confidence "
            f"{row.average_confidence * 100:.0f}%.",
            {
                "person_count": int(row.person_count),
                "average_confidence": round(row.average_confidence or 0.0, 4),
                "detected_at": row.detected_at.isoformat(timespec="seconds"),
                "page_context": page_context,
            },
        )

    if intent == "LAST_VIDEO_DETECTION":
        row = statistics_service.latest_record(db, source_type="video")
        if not row:
            return (
                "Belum ada video yang di-upload untuk dideteksi.",
                {"person_count": 0, "page_context": page_context},
            )
        return (
            f"Pada video terakhir yang di-upload ({_fmt_time(row.detected_at)}), "
            f"terdeteksi hingga {row.person_count} orang (peak) dengan rata-rata confidence "
            f"{row.average_confidence * 100:.0f}%.",
            {
                "person_count": int(row.person_count),
                "average_confidence": round(row.average_confidence or 0.0, 4),
                "detected_at": row.detected_at.isoformat(timespec="seconds"),
                "page_context": page_context,
            },
        )

    # =====================================================
    # CAMERA STATUS — selalu tentang webcam
    # =====================================================
    if intent == "CAMERA_STATUS":
        status = webcam_service.get_status()
        if status["running"]:
            answer = (
                f"Kamera berstatus ONLINE dan sedang aktif mendeteksi. "
                f"Saat ini terdeteksi {status['person_count']} orang "
                f"pada {status['fps']} FPS."
            )
        else:
            answer = (
                "Kamera berstatus OFFLINE. "
                "Silakan jalankan kamera dari halaman Live Monitoring."
            )
        data = dict(status)
        data["page_context"] = page_context
        return answer, data

    # =====================================================
    # MAX / MIN / AVG / PEAK / HISTORY — pakai semua sumber
    # (analitik lintas sumber; konteks tidak membatasi)
    # =====================================================
    if intent == "MAX_COUNT":
        row = (
            db.query(DetectionHistory)
            .filter(DetectionHistory.detected_at >= today_start)
            .order_by(
                DetectionHistory.person_count.desc(),
                DetectionHistory.detected_at.desc(),
            )
            .first()
        )
        if not row:
            return (
                "Belum ada data deteksi hari ini.",
                {"max_people": 0, "page_context": page_context},
            )
        src_label = _SOURCE_LABEL.get(row.source_type, row.source_type)
        return (
            f"Jumlah orang terbanyak hari ini adalah {row.person_count} orang, "
            f"terdeteksi dari {src_label} pada {_fmt_time(row.detected_at)} "
            f"(confidence {row.average_confidence * 100:.0f}%).",
            {
                "max_people": int(row.person_count),
                "detected_at": row.detected_at.isoformat(timespec="seconds"),
                "source": row.source_type,
                "page_context": page_context,
            },
        )

    if intent == "MIN_COUNT":
        row = (
            db.query(DetectionHistory)
            .filter(DetectionHistory.detected_at >= today_start)
            .order_by(
                DetectionHistory.person_count.asc(),
                DetectionHistory.detected_at.desc(),
            )
            .first()
        )
        if not row:
            return (
                "Belum ada data deteksi hari ini.",
                {"min_people": 0, "page_context": page_context},
            )
        return (
            f"Jumlah orang paling sedikit yang tercatat hari ini adalah "
            f"{row.person_count} orang, pada {_fmt_time(row.detected_at)}.",
            {
                "min_people": int(row.person_count),
                "detected_at": row.detected_at.isoformat(timespec="seconds"),
                "page_context": page_context,
            },
        )

    if intent == "AVERAGE_COUNT":
        avg = (
            db.query(func.avg(DetectionHistory.person_count))
            .filter(DetectionHistory.detected_at >= today_start)
            .scalar()
        )
        avg = round(float(avg or 0.0), 2)
        return (
            f"Rata-rata jumlah orang yang terdeteksi hari ini adalah {avg} orang per pencatatan.",
            {"average_people": avg, "page_context": page_context},
        )

    if intent == "PEAK_TIME":
        row = (
            db.query(DetectionHistory)
            .filter(DetectionHistory.detected_at >= today_start)
            .order_by(
                DetectionHistory.person_count.desc(),
                DetectionHistory.detected_at.desc(),
            )
            .first()
        )
        if not row:
            return (
                "Belum ada data deteksi hari ini.",
                {"peak_time": None, "page_context": page_context},
            )
        src_label = _SOURCE_LABEL.get(row.source_type, row.source_type)
        return (
            f"Puncak jumlah orang hari ini terjadi pada pukul "
            f"{row.detected_at.strftime('%H:%M:%S')} dengan {row.person_count} orang "
            f"(dari {src_label}).",
            {
                "peak_time": row.detected_at.isoformat(timespec="seconds"),
                "peak_people": int(row.person_count),
                "source": row.source_type,
                "page_context": page_context,
            },
        )

    if intent == "HISTORY_COUNT":
        value = int(params.get("window_value", 10))
        unit = params.get("window_unit", "minutes")
        delta = timedelta(minutes=value) if unit == "minutes" else timedelta(hours=value)
        start = now - delta

        rows = (
            db.query(DetectionHistory)
            .filter(DetectionHistory.detected_at >= start)
            .all()
        )
        if not rows:
            return (
                f"Tidak ada data deteksi dalam {value} {unit} terakhir.",
                {"window": f"{value} {unit}", "samples": 0, "page_context": page_context},
            )
        counts = [int(r.person_count) for r in rows]
        avg = round(sum(counts) / len(counts), 2)
        label = f"{value} menit" if unit == "minutes" else f"{value} jam"
        return (
            f"Dalam {label} terakhir terdapat {len(rows)} pencatatan, "
            f"rata-rata {avg} orang, maksimum {max(counts)} orang, "
            f"minimum {min(counts)} orang.",
            {
                "window": label,
                "samples": len(rows),
                "average_people": avg,
                "max_people": max(counts),
                "min_people": min(counts),
                "page_context": page_context,
            },
        )

    if intent == "COUNT_ABOVE_THRESHOLD":
        threshold = int(params.get("threshold", 10))
        count = statistics_service.count_above_threshold(db, threshold, today_start, now)
        return (
            f"Kamera mendeteksi lebih dari {threshold} orang sebanyak {count} kali hari ini.",
            {"threshold": threshold, "occurrences": count, "page_context": page_context},
        )

    if intent == "TREND_ANALYSIS":
        recent_start = now - timedelta(minutes=10)
        previous_start = now - timedelta(minutes=20)

        recent = (
            db.query(func.avg(DetectionHistory.person_count))
            .filter(DetectionHistory.detected_at >= recent_start)
            .scalar()
        )
        previous = (
            db.query(func.avg(DetectionHistory.person_count))
            .filter(
                DetectionHistory.detected_at >= previous_start,
                DetectionHistory.detected_at < recent_start,
            )
            .scalar()
        )
        recent = round(float(recent or 0.0), 2)
        previous = round(float(previous or 0.0), 2)

        if previous == 0 and recent == 0:
            trend = "stabil"
            answer = "Belum cukup data untuk menganalisis tren jumlah orang."
        elif recent > previous:
            trend = "meningkat"
            answer = (
                f"Ya, jumlah orang cenderung MENINGKAT. Rata-rata 10 menit terakhir "
                f"{recent} orang, sebelumnya {previous} orang."
            )
        elif recent < previous:
            trend = "menurun"
            answer = (
                f"Jumlah orang cenderung MENURUN. Rata-rata 10 menit terakhir "
                f"{recent} orang, sebelumnya {previous} orang."
            )
        else:
            trend = "stabil"
            answer = f"Jumlah orang relatif STABIL di sekitar {recent} orang."
        return answer, {
            "trend": trend,
            "recent_average": recent,
            "previous_average": previous,
            "page_context": page_context,
        }

    # =====================================================
    # UNKNOWN
    # =====================================================
    return (
        "Maaf, pertanyaan tersebut berada di luar cakupan sistem AI CCTV ini. "
        "Saya dapat membantu menjawab pertanyaan seputar jumlah orang yang terdeteksi, "
        "statistik deteksi, riwayat, tren, dan status kamera.",
        {"page_context": page_context},
    )


# ======================================================================
# 5. LLM LAYER (OPSIONAL)
# ======================================================================
SYSTEM_PROMPT = (
    "Anda adalah 'CCTV AI Assistant' untuk sistem monitoring AI CCTV. "
    "Jawab SINGKAT, RAMAH, dan dalam Bahasa Indonesia. "
    "ATURAN MUTLAK: Gunakan HANYA data pada konteks yang diberikan. "
    "JANGAN mengarang angka atau kejadian. Jika data tidak ada, katakan datanya belum tersedia."
)


async def _refine_with_llm(
    question: str,
    context: Dict[str, Any],
    fallback: str,
    page_context: str,
) -> str:
    if not settings.LLM_ENABLED or not settings.LLM_API_KEY:
        return fallback

    ctx_label = _CONTEXT_TITLE.get(page_context, "AI CCTV")
    user_prompt = (
        f"Halaman aktif pengguna: {ctx_label}\n"
        f"Pertanyaan pengguna: {question}\n\n"
        f"Data dari database/state saat ini (JSON):\n{context}\n\n"
        f"Jawaban faktual yang sudah dihitung sistem: {fallback}\n\n"
        "Tulis ulang jawaban di atas dengan bahasa yang natural tanpa mengubah angkanya."
    )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.LLM_MODEL,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            return payload["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM gagal dipanggil, memakai jawaban template: %s", exc)
        return fallback


# ======================================================================
# 6. ENTRY POINT
# ======================================================================
async def ask(
    db: Session,
    question: str,
    page_context: Optional[str] = "general",
) -> Dict[str, Any]:
    ctx = _normalize_context(page_context)
    intent, params = detect_intent(question)

    # Override: di tab video/image, pertanyaan "berapa orang" otomatis
    # dianggap "current" untuk sumber tersebut (bukan webcam).
    if ctx in ("video", "image") and intent == "CURRENT_COUNT":
        params["_force_source"] = ctx

    fallback, data = _build_answer(db, intent, params, ctx)

    context = {
        "intent": intent,
        "params": params,
        "data": data,
        "page_context": ctx,
        "camera_status": webcam_service.get_status().get("camera_status"),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    answer = await _refine_with_llm(question, context, fallback, ctx)
    return {"answer": answer, "intent": intent, "page_context": ctx, "data": data}