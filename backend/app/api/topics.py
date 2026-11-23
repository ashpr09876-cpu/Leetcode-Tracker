from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Company, Problem, Topic, User, SOLVED_STATUSES, problem_companies
from app.schemas import CompanyOut, TopicIn, TopicOut

router = APIRouter(tags=["topics"])


def _owned(db: Session, user: User, tid: int) -> Topic:
    t = db.scalar(select(Topic).where(Topic.id == tid, Topic.user_id == user.id))
    if not t:
        raise HTTPException(status_code=404, detail="Topic not found")
    return t


@router.get("/topics", response_model=list[TopicOut])
def list_topics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Topic).where(Topic.user_id == user.id).order_by(Topic.name)).all()


@router.post("/topics", response_model=TopicOut, status_code=201)
def create_topic(body: TopicIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    name = body.name.strip()
    if db.scalar(select(Topic.id).where(Topic.user_id == user.id, Topic.name == name)):
        raise HTTPException(status_code=409, detail="You already have a topic with this name")
    t = Topic(user_id=user.id, name=name, is_default=False)
    db.add(t)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You already have a topic with this name")
    return t


@router.patch("/topics/{topic_id}", response_model=TopicOut)
def rename_topic(topic_id: int, body: TopicIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = _owned(db, user, topic_id)
    name = body.name.strip()
    if db.scalar(select(Topic.id).where(Topic.user_id == user.id, Topic.name == name, Topic.id != t.id)):
        raise HTTPException(status_code=409, detail="You already have a topic with this name")
    t.name = name
    db.commit()
    return t


@router.delete("/topics/{topic_id}", status_code=204)
def delete_topic(topic_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, topic_id))  # association rows cascade; problems are kept
    db.commit()


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Company tags are user-applied labels, not official company question lists."""
    out = []
    for c in db.scalars(select(Company).order_by(Company.name)).all():
        probs = db.scalars(select(Problem).where(Problem.user_id == user.id, Problem.companies.any(Company.id == c.id))).all()
        out.append(CompanyOut(id=c.id, name=c.name, total=len(probs),
                              solved=sum(1 for p in probs if p.status in SOLVED_STATUSES)))
    return out
