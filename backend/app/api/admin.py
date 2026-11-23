from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import revoke_all
from app.api.deps import require_admin
from app.db.session import get_db
from app.models import ApiErrorLog, Problem, User, UserIntegration
from app.services import ai
from app.api.health import check_db, check_redis

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None


@router.get("/users")
def users(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(User)) or 0
    rows = db.scalars(select(User).order_by(User.id).offset((page - 1) * page_size).limit(page_size)).all()
    counts = dict(db.execute(select(Problem.user_id, func.count()).group_by(Problem.user_id)).all())
    return {"total": total, "page": page, "items": [
        {"id": u.id, "email": u.email, "name": u.name, "is_admin": u.is_admin, "is_active": u.is_active,
         "created_at": u.created_at.isoformat(), "problem_count": counts.get(u.id, 0)} for u in rows]}


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: AdminUserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.id == admin.id and (body.is_active is False or body.is_admin is False):
        raise HTTPException(status_code=400, detail="You cannot disable or demote your own account")
    if body.is_active is not None:
        u.is_active = body.is_active
        if not body.is_active:
            revoke_all(db, u.id)
    if body.is_admin is not None:
        u.is_admin = body.is_admin
    db.commit()
    return {"id": u.id, "is_active": u.is_active, "is_admin": u.is_admin}


@router.get("/system")
def system(db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    errs = db.scalars(select(ApiErrorLog).order_by(ApiErrorLog.id.desc()).limit(20)).all()
    sync_errors = db.execute(select(UserIntegration, User.email).join(User, User.id == UserIntegration.user_id)
                             .where(UserIntegration.last_error.is_not(None)).limit(20)).all()
    return {
        "database": check_db(), "redis": check_redis(),
        "ai_providers_configured": ai.configured_providers(),
        "api_errors_24h": db.scalar(select(func.count()).select_from(ApiErrorLog).where(ApiErrorLog.created_at >= since)) or 0,
        "recent_api_errors": [{"path": e.path, "status": e.status_code, "message": e.message,
                               "at": e.created_at.isoformat()} for e in errs],
        "leetcode_sync_errors": [{"email": email, "error": i.last_error,
                                  "at": i.last_error_at.isoformat() if i.last_error_at else None} for i, email in sync_errors],
    }
