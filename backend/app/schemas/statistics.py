from typing import List, Optional

from pydantic import BaseModel


class HistoryItem(BaseModel):
    id: int
    source_type: str
    person_count: int
    average_confidence: float
    detected_at: Optional[str] = None
    image_path: Optional[str] = None
    session_id: Optional[str] = None


class HistoryResponse(BaseModel):
    items: List[HistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class TimelinePoint(BaseModel):
    time: str
    timestamp: str
    person_count: float
    average_confidence: float
    samples: int


class TimelineResponse(BaseModel):
    points: List[TimelinePoint]
    bucket_minutes: int
    source_type: Optional[str] = None


class SummaryResponse(BaseModel):
    range_key: str
    start: Optional[str] = None
    end: Optional[str] = None
    current_people: int = 0
    peak_people: int = 0
    min_people: int = 0
    average_people: float = 0.0
    total_records: int = 0
    total_people_detected: int = 0
    peak_time: Optional[str] = None
    webcam_records: int = 0
    image_records: int = 0
    detection_sessions: int = 0