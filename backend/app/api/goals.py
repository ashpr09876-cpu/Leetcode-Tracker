from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Goal, User
from app.schemas import GoalIn, GoalOut, GoalUpdate
from app.services.stats import activity_by_day, month_bounds, sum_range, today_for, week_start

router = APIRouter(prefix="/goals", tags=["goals"])


def _out(db: Session, g: Goal, by_day: dict, today) -> GoalOut:
    progress = sum_range(by_day, g.start_date, g.end_date, g.metric)
    if progress >= g.target and g.completed_at is None:
        g.completed_at = datetime.now(timezone.utc)
        db.commit()
    return GoalOut(id=g.id, title=g.title, period=g.period, metric=g.metric, target=g.target, start_date=g.start_date,
                   end_date=g.end_date, progress=progress, completed=progress >= g.target, completed_at=g.completed_at,
                   active=g.end_date >= today)


def _owned(db: Session, user: User, gid: int) -> Goal:
    g = db.scalar(select(Goal).where(Goal.id == gid, Goal.user_id == user.id))
    if not g:
        raise HTTPException(status_code=404, detail="Goal not found")
    return g


@router.get("", response_model=list[GoalOut])
def list_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    by_day, today = activity_by_day(db, user), today_for(user)
    goals = db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.end_date.desc(), Goal.id.desc())).all()
    return [_out(db, g, by_day, today) for g in goals]


@router.post("", response_model=GoalOut, status_code=201)
def create_goal(body: GoalIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = today_for(user)
    if body.period == "daily":
        start, end = today, today
    elif body.period == "weekly":
        start = week_start(today); end = start + timedelta(days=6)
    elif body.period == "monthly":
        start, end = month_bounds(today)
    else:
        if not body.start_date or not body.end_date:
            raise HTTPException(status_code=422, detail="Custom goals need a start and end date")
        start, end = body.start_date, body.end_date
    if end < start:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    g = Goal(user_id=user.id, title=body.title, period=body.period, metric=body.metric, target=body.target,
             start_date=start, end_date=end)
    db.add(g)
    db.commit()
    return _out(db, g, activity_by_day(db, user), today)


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, body: GoalUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    g = _owned(db, user, goal_id)
    if body.title is not None: g.title = body.title
    if body.target is not None: g.target = body.target
    if body.end_date is not None:
        if body.end_date < g.start_date:
            raise HTTPException(status_code=422, detail="End date must not be before start date")
        g.end_date = body.end_date
    db.commit()
    return _out(db, g, activity_by_day(db, user), today_for(user))


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, goal_id))
    db.commit()
