from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services import statistics_service
from app.services.webcam_service import webcam_service

router = APIRouter(prefix="/api/statistics", tags=["Statistics"])


@router.get("/current", summary="Statistik deteksi saat ini")
def current_statistics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    state = webcam_service.get_current(include_frame=False)
    latest = statistics_service.latest_record(db)

    return {
        "camera_status": state.get("camera_status", "OFFLINE"),
        "person_count": state.get("person_count", 0),
        "fps": state.get("fps", 0.0),
        "average_confidence": state.get("average_confidence", 0.0),
        "detections": state.get("detections", []),
        "timestamp": state.get("timestamp"),
        "last_record": latest.to_dict() if latest else None,
    }


@router.get("/history", summary="Riwayat deteksi dengan filter & pagination")
def history(
    range: str = Query("today", description="today | yesterday | 7d | 30d | all | custom"),
    start: Optional[str] = Query(None, description="Format YYYY-MM-DD atau ISO datetime"),
    end: Optional[str] = Query(None, description="Format YYYY-MM-DD atau ISO datetime"),
    source_type: Optional[str] = Query(None, description="webcam | image"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return statistics_service.get_history(
        db,
        range_key=range,
        start=start,
        end=end,
        source_type=source_type,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", summary="Ringkasan statistik")
def summary(
    range: str = Query("today"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    data = statistics_service.get_summary(db, range_key=range, start=start, end=end)
    state = webcam_service.get_current(include_frame=False)
    data["current_people"] = int(state.get("person_count", 0))
    data["camera_status"] = state.get("camera_status", "OFFLINE")
    return data


@router.get("/timeline", summary="Data timeline untuk chart")
def timeline(
    range: str = Query("today"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return statistics_service.get_timeline(
        db, range_key=range, start=start, end=end, source_type=source_type
    )


@router.get("/hourly", summary="Rata-rata orang per jam")
def hourly(
    range: str = Query("today"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return {"items": statistics_service.get_hourly_average(db, range, start, end)}