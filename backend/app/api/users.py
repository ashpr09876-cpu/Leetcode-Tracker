from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.auth import _set_refresh_cookie, issue_refresh, revoke_all, user_out
from app.api.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models import User, UserPreference
from app.schemas import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.name is not None:
        user.name = body.name
    if body.timezone is not None:
        try:
            ZoneInfo(body.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise HTTPException(status_code=422, detail="Unknown timezone")
        user.timezone = body.timezone
    if body.leetcode_username is not None:
        user.leetcode_username = body.leetcode_username or None
    if body.preferences is not None:
        prefs = user.preferences or UserPreference(user_id=user.id)
        for k, v in body.preferences.model_dump(exclude_none=True).items():
            setattr(prefs, k, v)
        user.preferences = prefs
    if body.new_password:
        if user.password_hash and not verify_password(body.current_password or "", user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        user.password_hash = hash_password(body.new_password)
        revoke_all(db, user.id)  # sign out every other session
        db.commit()
        _set_refresh_cookie(response, issue_refresh(db, user))
    db.commit()
    return user_out(user)


@router.delete("/me", status_code=204)
def delete_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(user)  # child rows are removed by ON DELETE CASCADE
    db.commit()
    return Response(status_code=204)
