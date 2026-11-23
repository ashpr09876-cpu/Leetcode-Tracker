import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import SOLVED_STATUSES, Company, Problem, ProblemNote, Revision, Topic, User
from app.schemas import (NoteIn, NoteOut, Page, ProblemCreate, ProblemOut, ProblemUpdate, RevisionBookmarkIn,
                         RevisionOut)
from app.services.revisions import due_for_stage
from app.services.stats import get_intervals, log_activity, today_for
from app.api.revisions import rev_out

router = APIRouter(prefix="/problems", tags=["problems"])
SLUG_RE = re.compile(r"leetcode\.com/problems/([a-z0-9\-]+)", re.I)
SORTS = {"newest": Problem.created_at.desc(), "oldest": Problem.created_at.asc(), "title": Problem.title.asc(),
         "difficulty": Problem.difficulty.asc(), "confidence": Problem.confidence.asc(),
         "time": Problem.time_spent_minutes.desc()}


def _owned(db: Session, user: User, problem_id: int) -> Problem:
    p = db.scalar(select(Problem).where(Problem.id == problem_id, Problem.user_id == user.id))
    if not p:
        raise HTTPException(status_code=404, detail="Problem not found")
    return p


def _topics(db: Session, user: User, ids: list[int]) -> list[Topic]:
    ids = list(set(ids))
    rows = db.scalars(select(Topic).where(Topic.id.in_(ids), Topic.user_id == user.id)).all() if ids else []
    if len(rows) != len(ids):
        raise HTTPException(status_code=400, detail="One or more topics do not exist")
    return list(rows)


def _companies(db: Session, ids: list[int]) -> list[Company]:
    ids = list(set(ids))
    rows = db.scalars(select(Company).where(Company.id.in_(ids))).all() if ids else []
    if len(rows) != len(ids):
        raise HTTPException(status_code=400, detail="One or more companies do not exist")
    return list(rows)


def _slug(url: str | None) -> str | None:
    m = SLUG_RE.search(url or "")
    return m.group(1).lower() if m else None


@router.get("", response_model=Page)
def list_problems(q: str = "", difficulty: str = "", status: str = "", topic_id: int | None = None,
                  company_id: int | None = None, bookmarked: bool | None = None, sort: str = "newest",
                  page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Problem).where(Problem.user_id == user.id)
    if q.strip():
        esc = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        cond = Problem.title.ilike(f"%{esc}%", escape="\\")
        if q.strip().isdigit():
            cond = cond | (Problem.leetcode_number == int(q.strip()))
        stmt = stmt.where(cond)
    if difficulty:
        stmt = stmt.where(Problem.difficulty == difficulty)
    if status:
        stmt = stmt.where(Problem.status == status)
    if topic_id:
        stmt = stmt.where(Problem.topics.any(Topic.id == topic_id))
    if company_id:
        stmt = stmt.where(Problem.companies.any(Company.id == company_id))
    if bookmarked is not None:
        stmt = stmt.where(Problem.bookmarked == bookmarked)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(SORTS.get(sort, SORTS["newest"]), Problem.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).unique().all()
    return Page(items=[ProblemOut.model_validate(p) for p in rows], total=total, page=page, page_size=page_size)


@router.post("", response_model=ProblemOut, status_code=201)
def create_problem(body: ProblemCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    slug = _slug(body.url)
    if slug and db.scalar(select(Problem.id).where(Problem.user_id == user.id, Problem.leetcode_slug == slug)):
        raise HTTPException(status_code=409, detail="You are already tracking this problem")
    data = body.model_dump(exclude={"topic_ids", "company_ids"})
    p = Problem(user_id=user.id, leetcode_slug=slug, **data)
    p.topics = _topics(db, user, body.topic_ids)
    p.companies = _companies(db, body.company_ids)
    if p.status in SOLVED_STATUSES:
        p.solved_at = datetime.now(timezone.utc)
    db.add(p)
    db.flush()
    log_activity(db, user.id, p.id, "attempt", p.attempts)
    if p.solved_at:
        log_activity(db, user.id, p.id, "solve", 1)
    db.commit()
    return ProblemOut.model_validate(p)


@router.get("/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProblemOut.model_validate(_owned(db, user, problem_id))


@router.patch("/{problem_id}", response_model=ProblemOut)
def update_problem(problem_id: int, body: ProblemUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _owned(db, user, problem_id)
    data = body.model_dump(exclude_unset=True)
    topic_ids, company_ids = data.pop("topic_ids", None), data.pop("company_ids", None)
    old_attempts = p.attempts
    if "url" in data:
        slug = _slug(data["url"])
        if slug and slug != p.leetcode_slug and db.scalar(select(Problem.id).where(
                Problem.user_id == user.id, Problem.leetcode_slug == slug, Problem.id != p.id)):
            raise HTTPException(status_code=409, detail="You are already tracking this problem")
        p.leetcode_slug = slug
    for k, v in data.items():
        if v is None and k in ("title", "difficulty", "status", "attempts", "time_spent_minutes", "confidence", "bookmarked"):
            continue
        setattr(p, k, v)
    if topic_ids is not None:
        p.topics = _topics(db, user, topic_ids)
    if company_ids is not None:
        p.companies = _companies(db, company_ids)
    if p.attempts > old_attempts:
        log_activity(db, user.id, p.id, "attempt", p.attempts - old_attempts)
    if p.status in SOLVED_STATUSES and p.solved_at is None:
        p.solved_at = datetime.now(timezone.utc)
        log_activity(db, user.id, p.id, "solve", 1)
    db.commit()
    return ProblemOut.model_validate(p)


@router.delete("/{problem_id}", status_code=204)
def delete_problem(problem_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, problem_id))
    db.commit()


@router.post("/{problem_id}/bookmark", response_model=ProblemOut)
def toggle_bookmark(problem_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _owned(db, user, problem_id)
    p.bookmarked = not p.bookmarked
    db.commit()
    return ProblemOut.model_validate(p)


@router.post("/{problem_id}/notes", response_model=NoteOut, status_code=201)
def add_note(problem_id: int, body: NoteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _owned(db, user, problem_id)
    n = ProblemNote(problem_id=p.id, user_id=user.id, body=body.body)
    db.add(n)
    db.commit()
    return NoteOut.model_validate(n)


@router.delete("/{problem_id}/notes/{note_id}", status_code=204)
def delete_note(problem_id: int, note_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.scalar(select(ProblemNote).where(ProblemNote.id == note_id, ProblemNote.problem_id == problem_id,
                                            ProblemNote.user_id == user.id))
    if not n:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(n)
    db.commit()


@router.post("/{problem_id}/revision", response_model=RevisionOut, status_code=201)
def schedule_revision(problem_id: int, body: RevisionBookmarkIn, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    p = _owned(db, user, problem_id)
    if db.scalar(select(Revision.id).where(Revision.problem_id == p.id, Revision.status == "pending")):
        raise HTTPException(status_code=409, detail="A pending revision already exists for this problem")
    r = Revision(user_id=user.id, problem_id=p.id, priority=body.priority, notes=body.notes, stage=0,
                 due_date=body.due_date or due_for_stage(get_intervals(user), 0, today_for(user)))
    db.add(r)
    db.commit()
    return rev_out(r, today_for(user))
