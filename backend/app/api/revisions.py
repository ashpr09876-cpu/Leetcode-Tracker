from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Problem, Revision, User
from app.schemas import RevisionIn, RevisionOut, RevisionUpdate
from app.services.revisions import complete_revision, due_for_stage
from app.services.stats import get_intervals, today_for

router = APIRouter(prefix="/revisions", tags=["revisions"])


def rev_out(r: Revision, today: date) -> RevisionOut:
    return RevisionOut(id=r.id, problem_id=r.problem_id, problem_title=r.problem.title,
                       problem_difficulty=r.problem.difficulty, due_date=r.due_date, priority=r.priority,
                       status=r.status, stage=r.stage, notes=r.notes, completed_at=r.completed_at,
                       overdue=r.status == "pending" and r.due_date < today)


def _owned(db: Session, user: User, rid: int) -> Revision:
    r = db.scalar(select(Revision).where(Revision.id == rid, Revision.user_id == user.id))
    if not r:
        raise HTTPException(status_code=404, detail="Revision not found")
    return r


@router.get("", response_model=list[RevisionOut])
def list_revisions(status: str = "", due_only: bool = False, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    today = today_for(user)
    stmt = select(Revision).where(Revision.user_id == user.id)
    if status:
        stmt = stmt.where(Revision.status == status)
    if due_only:
        stmt = stmt.where(Revision.status == "pending", Revision.due_date <= today)
    rows = db.scalars(stmt.order_by(Revision.due_date, Revision.id)).all()
    prio = {"high": 0, "medium": 1, "low": 2}
    rows = sorted(rows, key=lambda r: (r.due_date, prio.get(r.priority, 1)))
    return [rev_out(r, today) for r in rows]


@router.post("", response_model=RevisionOut, status_code=201)
def create_revision(body: RevisionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.scalar(select(Problem.id).where(Problem.id == body.problem_id, Problem.user_id == user.id)):
        raise HTTPException(status_code=404, detail="Problem not found")
    if db.scalar(select(Revision.id).where(Revision.problem_id == body.problem_id, Revision.status == "pending")):
        raise HTTPException(status_code=409, detail="A pending revision already exists for this problem")
    today = today_for(user)
    r = Revision(user_id=user.id, problem_id=body.problem_id, priority=body.priority, notes=body.notes, stage=0,
                 due_date=body.due_date or due_for_stage(get_intervals(user), 0, today))
    db.add(r)
    db.commit()
    return rev_out(r, today)


@router.patch("/{revision_id}", response_model=RevisionOut)
def update_revision(revision_id: int, body: RevisionUpdate, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    r = _owned(db, user, revision_id)
    if r.status != "pending" and body.status is not None:
        raise HTTPException(status_code=409, detail="Only pending revisions can change status")
    if body.due_date is not None:
        r.due_date = body.due_date
    if body.priority is not None:
        r.priority = body.priority
    if body.notes is not None:
        r.notes = body.notes
    if body.status == "completed":
        complete_revision(db, user, r)
    elif body.status == "skipped":
        r.status = "skipped"
    db.commit()
    return rev_out(r, today_for(user))


@router.delete("/{revision_id}", status_code=204)
def delete_revision(revision_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, revision_id))
    db.commit()
