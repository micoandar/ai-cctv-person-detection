from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schemas.chatbot import ChatRequest, ChatResponse
from app.services import chatbot_service

router = APIRouter(prefix="/api", tags=["Chatbot"])


@router.post("/chat", response_model=ChatResponse, summary="Tanya CCTV AI Assistant")
async def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    try:
        result = await chatbot_service.ask(
            db,
            payload.message,
            page_context=payload.page_context or "general",
        )
        return ChatResponse(**result)
    except Exception as exc:  # noqa: BLE001
        return ChatResponse(
            answer=(
                "Maaf, terjadi kesalahan saat memproses pertanyaan Anda. "
                f"Detail: {exc}"
            ),
            intent="ERROR",
            page_context="general",
            data={},
        )