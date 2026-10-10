from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: Optional[List[ChatMessage]] = None
    # Konteks halaman aktif: "live" | "video" | "image" | "general"
    page_context: Optional[str] = "general"


class ChatResponse(BaseModel):
    answer: str
    intent: str
    page_context: str = "general"
    data: Dict[str, Any] = {}