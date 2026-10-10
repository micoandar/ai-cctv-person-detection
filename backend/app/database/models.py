"""
Model tabel MySQL.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Index

from app.database.database import Base


class DetectionHistory(Base):
    __tablename__ = "detection_history"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    # source_type: webcam | image | video
    source_type = Column(String(20), nullable=False, index=True)
    person_count = Column(Integer, nullable=False, default=0)
    average_confidence = Column(Float, nullable=False, default=0.0)
    detected_at = Column(DateTime, nullable=False, default=datetime.now, index=True)

    # Opsional
    image_path = Column(String(255), nullable=True)
    session_id = Column(String(64), nullable=True, index=True)

    __table_args__ = (
        Index("ix_detection_source_time", "source_type", "detected_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_type": self.source_type,
            "person_count": self.person_count,
            "average_confidence": round(self.average_confidence or 0.0, 4),
            "detected_at": self.detected_at.isoformat(timespec="seconds")
            if self.detected_at
            else None,
            "image_path": self.image_path,
            "session_id": self.session_id,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<DetectionHistory id={self.id} source={self.source_type} "
            f"people={self.person_count} at={self.detected_at}>"
        )