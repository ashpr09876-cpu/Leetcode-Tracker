import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.ratelimit import rate_limit
from app.core.security import (create_access_token, create_state_token, hash_password, hash_token,
                               new_opaque_token, verify_password, verify_state_token)
from app.db.session import get_db
from app.models import (DEFAULT_COMPANIES, DEFAULT_TOPICS, Company, PasswordResetToken, RefreshToken,
                        Topic, User, UserPreference, utcnow)
from app.schemas import ForgotIn, LoginIn, RegisterIn, ResetIn, TokenOut, UserOut

log = logging.getLogger("codetrack.auth")
router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "refresh_token"
AUTH_PATH = "/api/v1/auth"
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def user_out(u: User) -> UserOut:
    out = UserOut.model_validate(u)
    out.has_password = u.password_hash is not None
    return out


def _set_refresh_cookie(resp: Response, raw: str) -> None:
    s = get_settings()
    resp.set_cookie(COOKIE, raw, httponly=True, secure=s.cookie_secure, samesite="lax",
                    max_age=s.refresh_token_days * 86400, path=AUTH_PATH)


def issue_refresh(db: Session, user: User, family: str | None = None) -> str:
    raw = new_opaque_token()
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(raw), family_id=family or new_opaque_token()[:32],
                        expires_at=utcnow() + timedelta(days=get_settings().refresh_token_days)))
    db.commit()
    return raw


def revoke_all(db: Session, user_id: int) -> None:
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
               .values(revoked_at=utcnow()))


def _csrf(request: Request) -> None:
    # Custom header cannot be sent cross-site without a CORS preflight (origins are restricted).
    if request.headers.get("x-requested-with") != "codetrack":
        raise HTTPException(status_code=403, detail="Missing CSRF header")


def ensure_companies(db: Session) -> None:
    have = set(db.scalars(select(Company.name)).all())
    for n in DEFAULT_COMPANIES:
        if n not in have:
            db.add(Company(name=n))
    db.flush()


def create_user(db: Session, email: str, name: str, password: str | None, google_sub: str | None = None) -> User:
    s = get_settings()
    user = User(email=email.lower(), name=name, password_hash=hash_password(password) if password else None,
                google_sub=google_sub, is_admin=bool(s.admin_email) and email.lower() == s.admin_email.lower())
    user.preferences = UserPreference()
    db.add(user)
    db.flush()
    for t in DEFAULT_TOPICS:
        db.add(Topic(user_id=user.id, name=t, is_default=True))
    ensure_companies(db)
    db.commit()
    return user


@router.get("/providers")
def providers():
    s = get_settings()
    return {"google": bool(s.google_client_id and s.google_client_secret)}


@router.post("/register", response_model=TokenOut, status_code=201, dependencies=[Depends(rate_limit(10, 60))])
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = create_user(db, body.email, body.name, body.password)
    _set_refresh_cookie(response, issue_refresh(db, user))
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenOut, dependencies=[Depends(rate_limit(10, 60))])
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been disabled")
    _set_refresh_cookie(response, issue_refresh(db, user))
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/refresh", response_model=TokenOut, dependencies=[Depends(rate_limit(60, 60))])
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    _csrf(request)
    raw = request.cookies.get(COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="No session")
    tok = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    if not tok:
        raise HTTPException(status_code=401, detail="Invalid session")
    if tok.revoked_at is not None:  # reuse of a rotated token: revoke the whole family
        db.execute(update(RefreshToken).where(RefreshToken.family_id == tok.family_id, RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=utcnow()))
        db.commit()
        raise HTTPException(status_code=401, detail="Session revoked")
    expires = tok.expires_at if tok.expires_at.tzinfo else tok.expires_at.replace(tzinfo=timezone.utc)
    user = db.get(User, tok.user_id)
    if expires < datetime.now(timezone.utc) or not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Session expired")
    tok.revoked_at = utcnow()
    new_raw = issue_refresh(db, user, family=tok.family_id)
    _set_refresh_cookie(response, new_raw)
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    _csrf(request)
    raw = request.cookies.get(COOKIE)
    if raw:
        tok = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
        if tok:
            db.execute(update(RefreshToken).where(RefreshToken.family_id == tok.family_id, RefreshToken.revoked_at.is_(None))
                       .values(revoked_at=utcnow()))
            db.commit()
    response.delete_cookie(COOKIE, path=AUTH_PATH)
    return {"ok": True}


@router.post("/forgot-password", dependencies=[Depends(rate_limit(5, 60))])
def forgot_password(body: ForgotIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user and user.is_active:
        raw = new_opaque_token()
        db.add(PasswordResetToken(user_id=user.id, token_hash=hash_token(raw), expires_at=utcnow() + timedelta(hours=1)))
        db.commit()
        link = f"{get_settings().frontend_url}/reset-password?token={raw}"
        # No email service is configured: the link is written to the backend console (local development).
        log.warning("PASSWORD RESET LINK for %s (email delivery is not configured): %s", user.email, link)
    return {"message": "If an account exists for that email, a reset link has been generated. "
                       "In local development the link is printed in the backend console."}


@router.post("/reset-password", dependencies=[Depends(rate_limit(10, 60))])
def reset_password(body: ResetIn, db: Session = Depends(get_db)):
    tok = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(body.token)))
    exp = tok.expires_at if tok and tok.expires_at.tzinfo else (tok.expires_at.replace(tzinfo=timezone.utc) if tok else None)
    if not tok or tok.used_at is not None or exp < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")
    user = db.get(User, tok.user_id)
    user.password_hash = hash_password(body.password)
    tok.used_at = utcnow()
    revoke_all(db, user.id)
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_out(user)


# ---- Google OAuth 2.0 / OpenID Connect (authorization-code flow with state validation)
@router.get("/google/login")
def google_login():
    s = get_settings()
    if not (s.google_client_id and s.google_client_secret):
        raise HTTPException(status_code=503, detail="Google login is not configured. Set GOOGLE_CLIENT_ID and "
                                                    "GOOGLE_CLIENT_SECRET in backend/.env (see docs/DEPLOYMENT.md).")
    state = create_state_token("google")
    q = urlencode({"client_id": s.google_client_id, "redirect_uri": s.google_redirect_uri, "response_type": "code",
                   "scope": "openid email profile", "state": state, "prompt": "select_account"})
    resp = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{q}")
    resp.set_cookie("oauth_state", state, httponly=True, secure=s.cookie_secure, samesite="lax", max_age=600, path=AUTH_PATH)
    return resp


@router.get("/google/callback")
def google_callback(request: Request, code: str = "", state: str = "", error: str = "", db: Session = Depends(get_db)):
    s = get_settings()
    fail = RedirectResponse(f"{s.frontend_url}/login?error=google_failed")
    fail.delete_cookie("oauth_state", path=AUTH_PATH)
    cookie_state = request.cookies.get("oauth_state")
    if error or not code or not state or not cookie_state or state != cookie_state or not verify_state_token(state, "google"):
        return fail
    try:
        tr = httpx.post("https://oauth2.googleapis.com/token", timeout=15, data={
            "code": code, "client_id": s.google_client_id, "client_secret": s.google_client_secret,
            "redirect_uri": s.google_redirect_uri, "grant_type": "authorization_code"})
        tr.raise_for_status()
        access = tr.json()["access_token"]
        ui = httpx.get("https://openidconnect.googleapis.com/v1/userinfo", timeout=15,
                       headers={"Authorization": f"Bearer {access}"})
        ui.raise_for_status()
        info = ui.json()
        sub, email = str(info["sub"]), str(info["email"]).lower()
        if not info.get("email_verified"):
            return fail
    except (httpx.HTTPError, KeyError, ValueError):
        log.exception("Google OAuth callback failed")
        return fail
    user = db.scalar(select(User).where(User.google_sub == sub)) or db.scalar(select(User).where(User.email == email))
    if user is None:
        user = create_user(db, email, str(info.get("name", "")), None, google_sub=sub)
    elif user.google_sub is None:
        user.google_sub = sub
        db.commit()
    if not user.is_active:
        return fail
    resp = RedirectResponse(f"{s.frontend_url}/auth/callback")
    _set_refresh_cookie(resp, issue_refresh(db, user))
    resp.delete_cookie("oauth_state", path=AUTH_PATH)
    return resp
