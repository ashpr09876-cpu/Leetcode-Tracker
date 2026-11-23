from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.services import stats

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return stats.overview(db, user)


@router.get("/difficulty")
def difficulty(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return stats.difficulty_stats(db, user)


@router.get("/topics")
def topics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return stats.topic_stats(db, user)


@router.get("/activity")
def activity(granularity: str = Query("week", pattern="^(week|month)$"), periods: int = Query(12, ge=1, le=60),
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return stats.activity_buckets(db, user, granularity, periods)
