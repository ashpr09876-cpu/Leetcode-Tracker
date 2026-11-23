import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.integrations.leetcode import (LeetCodeClient, LeetCodeError, LeetCodeNotFound, LeetCodeRateLimited)
from app.models import Problem, Topic, User, UserIntegration
from app.schemas import LeetCodeConnectIn
from app.services.stats import log_activity

log = logging.getLogger("codetrack.leetcode")
router = APIRouter(prefix="/integrations/leetcode", tags=["leetcode"])
DISCLAIMER = ("LeetCode has no official public API. Sync uses LeetCode's unofficial public GraphQL endpoint, "
              "reads public profile data only, and only sees your ~20 most recent accepted submissions.")


def get_client() -> LeetCodeClient:
    return LeetCodeClient()


def _integration(db: Session, user: User) -> UserIntegration | None:
    return db.scalar(select(UserIntegration).where(UserIntegration.user_id == user.id, UserIntegration.provider == "leetcode"))


def _status(i: UserIntegration | None) -> dict:
    if not i:
        return {"connected": False, "disclaimer": DISCLAIMER}
    return {"connected": True, "username": i.external_username,
            "last_sync_at": i.last_sync_at.isoformat() if i.last_sync_at else None,
            "last_error": i.last_error, "last_error_at": i.last_error_at.isoformat() if i.last_error_at else None,
            "acceptance_rate": i.data.get("acceptance_rate"), "contest_rating": i.data.get("contest_rating"),
            "disclaimer": DISCLAIMER}


def _http(e: LeetCodeError) -> HTTPException:
    code = 404 if isinstance(e, LeetCodeNotFound) else 429 if isinstance(e, LeetCodeRateLimited) else 502
    return HTTPException(status_code=code, detail=str(e))


@router.post("/connect")
def connect(body: LeetCodeConnectIn, user: User = Depends(get_current_user), db: Session = Depends(get_db),
            client: LeetCodeClient = Depends(get_client)):
    try:
        profile = client.fetch_profile(body.username)
    except LeetCodeError as e:
        raise _http(e)
    i = _integration(db, user) or UserIntegration(user_id=user.id, provider="leetcode", external_username=body.username)
    i.external_username = body.username
    i.data = {"acceptance_rate": profile["acceptance_rate"], "contest_rating": profile["contest_rating"],
              "solved": profile["solved"]}
    i.last_error = None
    user.leetcode_username = body.username
    db.add(i)
    db.commit()
    return _status(i)


@router.get("/status")
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _status(_integration(db, user))


@router.post("/sync", dependencies=[Depends(rate_limit(6, 60))])
def sync(user: User = Depends(get_current_user), db: Session = Depends(get_db), client: LeetCodeClient = Depends(get_client)):
    i = _integration(db, user)
    if not i:
        raise HTTPException(status_code=400, detail="Connect a LeetCode username first")
    imported = skipped = 0
    topics = {t.name: t for t in db.scalars(select(Topic).where(Topic.user_id == user.id)).all()}
    try:
        profile = client.fetch_profile(i.external_username)
        i.data = {"acceptance_rate": profile["acceptance_rate"], "contest_rating": profile["contest_rating"],
                  "solved": profile["solved"]}
        for item in client.fetch_recent_accepted(i.external_username, 20):
            if db.scalar(select(Problem.id).where(Problem.user_id == user.id, Problem.leetcode_slug == item["slug"])):
                skipped += 1
                continue
            q = client.fetch_question(item["slug"])
            when = datetime.fromtimestamp(item["timestamp"], tz=timezone.utc)
            p = Problem(user_id=user.id, title=q["title"], leetcode_number=q["number"], leetcode_slug=item["slug"],
                        url=f"https://leetcode.com/problems/{item['slug']}/", difficulty=q["difficulty"],
                        status="solved", attempts=1, solved_at=when, source="leetcode",
                        topics=[topics[n] for n in q["topics"] if n in topics])
            db.add(p)
            db.flush()
            log_activity(db, user.id, p.id, "solve", 1, when=when)
            imported += 1
    except LeetCodeError as e:
        i.last_error, i.last_error_at = str(e), datetime.now(timezone.utc)
        db.commit()  # keep anything imported before the failure
        log.warning("LeetCode sync failed for user %s: %s", user.id, e)
        raise _http(e)
    i.last_sync_at, i.last_error = datetime.now(timezone.utc), None
    db.commit()
    return {"ok": True, "imported": imported, "skipped_existing": skipped, **_status(i)}


@router.delete("/disconnect")
def disconnect(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    i = _integration(db, user)
    if i:
        db.delete(i)
    user.leetcode_username = None
    db.commit()
    return {"connected": False}
