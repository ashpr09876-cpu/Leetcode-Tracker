from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Problem, User
from app.schemas import ProblemOut
from app.services import stats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return stats.summary(db, user)


@router.get("/activity")
def activity(days: int = Query(365, ge=7, le=730), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from datetime import timedelta
    start = stats.today_for(user) - timedelta(days=days - 1)
    by_day = stats.activity_by_day(db, user)
    return {"start": start.isoformat(), "days": days,
            "items": [{"date": d.isoformat(), **v} for d, v in sorted(by_day.items()) if d >= start]}


@router.get("/topic-progress")
def topic_progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return stats.topic_stats(db, user)


@router.get("/recent-problems", response_model=list[ProblemOut])
def recent_problems(limit: int = Query(5, ge=1, le=20), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Problem).where(Problem.user_id == user.id).order_by(Problem.created_at.desc(), Problem.id.desc())
                      .limit(limit)).unique().all()
    return [ProblemOut.model_validate(p) for p in rows]
