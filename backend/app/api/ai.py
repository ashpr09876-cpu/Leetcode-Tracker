import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.models import AIConversation, AIMessage, User
from app.schemas import AIPromptIn, ChatIn
from app.services import ai, stats

router = APIRouter(prefix="/ai", tags=["ai"], dependencies=[Depends(rate_limit(20, 60))])


def _used_today(db: Session, user: User) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(select(func.count()).select_from(AIMessage).where(
        AIMessage.user_id == user.id, AIMessage.role == "user", AIMessage.created_at >= start)) or 0


def _run(db: Session, user: User, title: str, prompt: str, conv: AIConversation | None = None) -> dict:
    limit = get_settings().ai_daily_limit
    if _used_today(db, user) >= limit:
        raise HTTPException(status_code=429, detail=f"Daily AI usage limit reached ({limit} requests).")
    try:
        provider = ai.resolve_provider(user.preferences.ai_provider if user.preferences else "")
    except ai.AINotConfigured as e:
        raise HTTPException(status_code=503, detail={"code": "ai_not_configured", "message": str(e)})
    if conv is None:
        conv = AIConversation(user_id=user.id, title=title[:160])
        db.add(conv)
        db.flush()
    history = [{"role": m.role, "content": m.content} for m in conv.messages[-10:]]
    system = ai.SYSTEM_PROMPT + json.dumps(stats.ai_context(db, user), default=str)
    try:
        reply = provider.complete(system, [*history, {"role": "user", "content": prompt}])
    except ai.AIError as e:
        db.rollback()
        raise HTTPException(status_code=502, detail={"code": "ai_provider_error", "message": str(e)})
    db.add(AIMessage(conversation_id=conv.id, user_id=user.id, role="user", content=prompt))
    db.add(AIMessage(conversation_id=conv.id, user_id=user.id, role="assistant", content=reply))
    db.commit()
    return {"conversation_id": conv.id, "reply": reply, "provider": provider.name}


@router.get("/status")
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    names = ai.configured_providers()
    s = get_settings()
    pref = user.preferences.ai_provider if user.preferences else ""
    active = pref if pref in names else (s.ai_provider if s.ai_provider in names else None)
    return {"configured": active is not None, "active_provider": active, "available_providers": names,
            "daily_limit": s.ai_daily_limit, "used_today": _used_today(db, user)}


@router.post("/chat")
def chat(body: ChatIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = None
    if body.conversation_id:
        conv = db.scalar(select(AIConversation).where(AIConversation.id == body.conversation_id, AIConversation.user_id == user.id))
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    return _run(db, user, body.message, body.message, conv)


@router.post("/analyze-performance")
def analyze(body: AIPromptIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _run(db, user, "Performance analysis",
                "Analyze my problem-solving performance: strengths, weak topics, consistency, and 3 concrete next steps. " + body.focus)


@router.post("/recommendations")
def recommendations(body: AIPromptIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _run(db, user, "Recommendations",
                "Recommend 5 LeetCode problems that target my weakest topics, plus what to revise first. " + body.focus)


@router.post("/roadmap")
def roadmap(body: AIPromptIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _run(db, user, "Study roadmap",
                "Create a 4-week DSA study roadmap based on my current coverage and goals, with weekly themes. " + body.focus)
