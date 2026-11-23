from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Revision, User
from app.services.stats import get_intervals, today_for


def due_for_stage(intervals: list[int], stage: int, today: date) -> date:
    return today + timedelta(days=intervals[min(stage, len(intervals) - 1)])


def complete_revision(db: Session, user: User, rev: Revision) -> Revision | None:
    """Mark a revision complete and schedule the next one while stages remain. Returns the new revision, if any."""
    intervals = get_intervals(user)
    rev.status = "completed"
    rev.completed_at = datetime.now(timezone.utc)
    next_stage = rev.stage + 1
    if next_stage >= len(intervals):
        return None
    exists = db.scalar(select(Revision).where(Revision.problem_id == rev.problem_id, Revision.status == "pending"))
    if exists:
        return None
    nxt = Revision(user_id=user.id, problem_id=rev.problem_id, stage=next_stage, priority=rev.priority,
                   due_date=due_for_stage(intervals, next_stage, today_for(user)))
    db.add(nxt)
    return nxt
