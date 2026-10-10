"""
Statistik & histori deteksi (query MySQL).
Mendukung source_type: webcam | image | video
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models import DetectionHistory


VALID_SOURCE_TYPES = ("webcam", "image", "video")


# ----------------------------------------------------------------------
# Range helper
# ----------------------------------------------------------------------
def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def resolve_range(
    range_key: str = "today",
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Tuple[Optional[datetime], Optional[datetime]]:
    now = datetime.now()
    key = (range_key or "today").lower()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if key == "today":
        return midnight, now
    if key == "yesterday":
        return midnight - timedelta(days=1), midnight
    if key in ("7d", "last7", "7days", "last_7_days"):
        return midnight - timedelta(days=6), now
    if key in ("30d", "last30", "30days", "last_30_days"):
        return midnight - timedelta(days=29), now
    if key == "all":
        return None, None
    if key == "custom":
        return _parse_dt(start), _parse_dt(end) or now

    return midnight, now


def _apply_range(query, start: Optional[datetime], end: Optional[datetime]):
    if start is not None:
        query = query.filter(DetectionHistory.detected_at >= start)
    if end is not None:
        query = query.filter(DetectionHistory.detected_at <= end)
    return query


# ----------------------------------------------------------------------
# History (paginated)
# ----------------------------------------------------------------------
def get_history(
    db: Session,
    range_key: str = "today",
    start: Optional[str] = None,
    end: Optional[str] = None,
    source_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    start_dt, end_dt = resolve_range(range_key, start, end)
    page = max(1, int(page))
    page_size = max(1, min(200, int(page_size)))

    base = db.query(DetectionHistory)
    base = _apply_range(base, start_dt, end_dt)

    if source_type and source_type.lower() in VALID_SOURCE_TYPES:
        base = base.filter(DetectionHistory.source_type == source_type.lower())

    total = base.count()
    items = (
        base.order_by(DetectionHistory.detected_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [item.to_dict() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


# ----------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------
def get_summary(
    db: Session,
    range_key: str = "today",
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Dict[str, Any]:
    start_dt, end_dt = resolve_range(range_key, start, end)

    q = _apply_range(db.query(DetectionHistory), start_dt, end_dt)

    agg = q.with_entities(
        func.count(DetectionHistory.id),
        func.max(DetectionHistory.person_count),
        func.min(DetectionHistory.person_count),
        func.avg(DetectionHistory.person_count),
        func.sum(DetectionHistory.person_count),
        func.avg(DetectionHistory.average_confidence),
    ).first()

    total_records = int(agg[0] or 0)
    peak_people = int(agg[1] or 0)
    min_people = int(agg[2] or 0)
    average_people = round(float(agg[3] or 0.0), 2)
    total_people = int(agg[4] or 0)

    peak_time = None
    if total_records > 0:
        peak_row = (
            q.order_by(
                DetectionHistory.person_count.desc(),
                DetectionHistory.detected_at.desc(),
            ).first()
        )
        if peak_row and peak_row.detected_at:
            peak_time = peak_row.detected_at.isoformat(timespec="seconds")

    webcam_records = (
        _apply_range(
            db.query(func.count(DetectionHistory.id)).filter(
                DetectionHistory.source_type == "webcam"
            ),
            start_dt,
            end_dt,
        ).scalar()
        or 0
    )
    image_records = (
        _apply_range(
            db.query(func.count(DetectionHistory.id)).filter(
                DetectionHistory.source_type == "image"
            ),
            start_dt,
            end_dt,
        ).scalar()
        or 0
    )
    video_records = (
        _apply_range(
            db.query(func.count(DetectionHistory.id)).filter(
                DetectionHistory.source_type == "video"
            ),
            start_dt,
            end_dt,
        ).scalar()
        or 0
    )
    webcam_sessions = (
        _apply_range(
            db.query(func.count(func.distinct(DetectionHistory.session_id))).filter(
                DetectionHistory.source_type == "webcam",
                DetectionHistory.session_id.isnot(None),
            ),
            start_dt,
            end_dt,
        ).scalar()
        or 0
    )
    video_sessions = (
        _apply_range(
            db.query(func.count(func.distinct(DetectionHistory.session_id))).filter(
                DetectionHistory.source_type == "video",
                DetectionHistory.session_id.isnot(None),
            ),
            start_dt,
            end_dt,
        ).scalar()
        or 0
    )

    return {
        "range_key": range_key,
        "start": start_dt.isoformat(timespec="seconds") if start_dt else None,
        "end": end_dt.isoformat(timespec="seconds") if end_dt else None,
        "current_people": 0,  # diisi oleh API layer dari webcam_service
        "peak_people": peak_people,
        "min_people": min_people,
        "average_people": average_people,
        "total_records": total_records,
        "total_people_detected": total_people,
        "peak_time": peak_time,
        "webcam_records": int(webcam_records),
        "image_records": int(image_records),
        "video_records": int(video_records),
        "detection_sessions": int(webcam_sessions) + int(image_records) + int(video_sessions),
    }


# ----------------------------------------------------------------------
# Timeline (chart)
# ----------------------------------------------------------------------
def _bucket_minutes(start: datetime, end: datetime) -> int:
    span = (end - start).total_seconds() / 60.0
    if span <= 60:
        return 1
    if span <= 6 * 60:
        return 5
    if span <= 24 * 60:
        return 15
    if span <= 7 * 24 * 60:
        return 120
    if span <= 31 * 24 * 60:
        return 360
    return 1440


def _floor_dt(dt: datetime, minutes: int) -> datetime:
    if minutes >= 1440:
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    total = dt.hour * 60 + dt.minute
    floored = (total // minutes) * minutes
    return dt.replace(hour=floored // 60, minute=floored % 60, second=0, microsecond=0)


def get_timeline(
    db: Session,
    range_key: str = "today",
    start: Optional[str] = None,
    end: Optional[str] = None,
    source_type: Optional[str] = None,
) -> Dict[str, Any]:
    start_dt, end_dt = resolve_range(range_key, start, end)
    if start_dt is None:
        start_dt = datetime.now() - timedelta(days=7)
    if end_dt is None:
        end_dt = datetime.now()

    bucket = _bucket_minutes(start_dt, end_dt)

    q = db.query(
        DetectionHistory.detected_at,
        DetectionHistory.person_count,
        DetectionHistory.average_confidence,
    )
    q = _apply_range(q, start_dt, end_dt)
    if source_type and source_type.lower() in VALID_SOURCE_TYPES:
        q = q.filter(DetectionHistory.source_type == source_type.lower())
    q = q.order_by(DetectionHistory.detected_at.asc()).limit(60000)

    buckets: Dict[datetime, Dict[str, float]] = {}
    for detected_at, person_count, avg_conf in q.all():
        if detected_at is None:
            continue
        key = _floor_dt(detected_at, bucket)
        slot = buckets.setdefault(
            key, {"sum": 0.0, "conf": 0.0, "n": 0, "peak": 0.0}
        )
        slot["sum"] += float(person_count or 0)
        slot["conf"] += float(avg_conf or 0.0)
        slot["n"] += 1
        slot["peak"] = max(slot["peak"], float(person_count or 0))

    points: List[Dict[str, Any]] = []
    for key in sorted(buckets.keys()):
        slot = buckets[key]
        n = max(1, int(slot["n"]))
        label = key.strftime("%H:%M") if bucket < 1440 else key.strftime("%d %b")
        points.append(
            {
                "time": label,
                "timestamp": key.isoformat(timespec="seconds"),
                "person_count": round(slot["sum"] / n, 2),   # rata-rata (untuk garis chart)
                "peak_people": int(slot["peak"]),             # ← BARU: peak di bucket
                "average_confidence": round(slot["conf"] / n, 4),
                "samples": n,                                 # ← jumlah record di bucket
            }
        )

    return {"points": points, "bucket_minutes": bucket, "source_type": source_type}


# ----------------------------------------------------------------------
# Hourly average (untuk halaman Statistics)
# ----------------------------------------------------------------------
def get_hourly_average(
    db: Session,
    range_key: str = "today",
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    start_dt, end_dt = resolve_range(range_key, start, end)

    q = _apply_range(db.query(DetectionHistory), start_dt, end_dt)
    rows = q.with_entities(
        DetectionHistory.detected_at, DetectionHistory.person_count
    ).all()

    buckets = {h: {"sum": 0.0, "n": 0} for h in range(24)}
    for detected_at, person_count in rows:
        if detected_at is None:
            continue
        b = buckets[detected_at.hour]
        b["sum"] += float(person_count or 0)
        b["n"] += 1

    result = []
    for hour in range(24):
        b = buckets[hour]
        n = b["n"]
        result.append(
            {
                "hour": f"{hour:02d}:00",
                "average_people": round(b["sum"] / n, 2) if n else 0.0,
                "samples": n,
            }
        )
    return result


# ----------------------------------------------------------------------
# Query helpers untuk chatbot
# ----------------------------------------------------------------------
def latest_record(db: Session, source_type: Optional[str] = None):
    q = db.query(DetectionHistory)
    if source_type:
        q = q.filter(DetectionHistory.source_type == source_type)
    return q.order_by(DetectionHistory.detected_at.desc()).first()


def records_between(
    db: Session,
    start: datetime,
    end: datetime,
    source_type: Optional[str] = None,
):
    q = db.query(DetectionHistory).filter(
        DetectionHistory.detected_at >= start,
        DetectionHistory.detected_at <= end,
    )
    if source_type:
        q = q.filter(DetectionHistory.source_type == source_type)
    return q.order_by(DetectionHistory.detected_at.asc()).all()


def count_above_threshold(
    db: Session,
    threshold: int,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> int:
    q = db.query(func.count(DetectionHistory.id)).filter(
        DetectionHistory.person_count > int(threshold)
    )
    q = _apply_range(q, start, end)
    return int(q.scalar() or 0)