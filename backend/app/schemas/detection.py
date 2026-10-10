from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class DetectionItem(BaseModel):
    """Hasil satu deteksi. Field dikirim sebagai 'class' (alias)."""

    model_config = ConfigDict(populate_by_name=True)

    class_name: str = Field(default="person", alias="class")
    confidence: float
    bbox: BBox


class DetectionResult(BaseModel):
    person_count: int = 0
    average_confidence: float = 0.0
    detections: List[DetectionItem] = []


class ImageDetectionResponse(DetectionResult):
    processed_image: Optional[str] = None
    original_image: Optional[str] = None
    image_path: Optional[str] = None
    processed_path: Optional[str] = None
    detected_at: Optional[str] = None
    inference_ms: Optional[float] = None


class WebcamStartRequest(BaseModel):
    camera_index: Optional[int] = None
    confidence: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    target_fps: Optional[int] = None


class WebcamStatusResponse(BaseModel):
    running: bool
    camera_status: str
    session_id: Optional[str] = None
    person_count: int = 0
    fps: float = 0.0
    average_confidence: float = 0.0
    error: Optional[str] = None


class SettingsPayload(BaseModel):
    confidence_threshold: Optional[float] = None
    detection_fps: Optional[int] = None
    camera_index: Optional[int] = None
    camera_width: Optional[int] = None
    camera_height: Optional[int] = None


# ======================================================================
# VIDEO DETECTION
# ======================================================================
class VideoFrameSample(BaseModel):
    frame_index: int
    timestamp: float
    person_count: int
    average_confidence: float


class VideoDetectionResponse(BaseModel):
    task_id: str
    filename: str
    status: str  # queued | processing | transcoding | completed | failed
    video_url: Optional[str] = None
    original_video_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    duration: Optional[float] = None
    total_frames: Optional[int] = None
    processed_frames: Optional[int] = None

    # Statistik
    total_detections: int = 0
    peak_people: int = 0
    min_people: int = 0
    average_people: float = 0.0
    average_confidence: float = 0.0
    peak_time_seconds: Optional[float] = None

    samples: List[VideoFrameSample] = []
    progress: Optional[float] = 0.0
    current_people: int = 0
    elapsed_seconds: Optional[float] = 0.0
    eta_seconds: Optional[float] = None
    processing_ms: Optional[float] = None

    transcode_ok: bool = False
    original_deleted: bool = False
    error: Optional[str] = None


class VideoTaskStatus(BaseModel):
    task_id: str
    status: str
    progress: float
    processed_frames: int
    total_frames: int
    current_people: int
    elapsed_seconds: float
    eta_seconds: Optional[float] = None
    error: Optional[str] = None