import redis
from fastapi import APIRouter, Response
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_engine

router = APIRouter(prefix="/health", tags=["health"])


def check_db() -> str:
    try:
        with get_engine().connect() as c:
            c.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "unavailable"


def check_redis() -> str:
    try:
        redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=1, socket_timeout=1).ping()
        return "ok"
    except Exception:
        return "unavailable"


@router.get("/live")
def live():
    return {"status": "ok"}


@router.get("/ready")
def ready(response: Response):
    db, rd = check_db(), check_redis()
    if db != "ok":
        response.status_code = 503
        return {"status": "not_ready", "database": db, "redis": rd}
    return {"status": "ready" if rd == "ok" else "degraded", "database": db, "redis": rd}
