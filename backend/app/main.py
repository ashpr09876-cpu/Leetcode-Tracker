import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import (admin, ai, analytics, auth, dashboard, goals, health, integrations, problems, revisions,
                     topics, users)
from app.core.config import get_settings
from app.db.session import open_session
from app.models import ApiErrorLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("codetrack")

app = FastAPI(title="CodeTrack API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_list, allow_credentials=True,
                   allow_methods=["GET", "POST", "PATCH", "DELETE"],
                   allow_headers=["Authorization", "Content-Type", "X-Requested-With"])


def _record_error(path: str, status: int, message: str) -> None:
    try:
        db = open_session()
        try:
            db.add(ApiErrorLog(path=path[:300], status_code=status, message=message[:300]))
            db.commit()
        finally:
            db.close()
    except Exception:  # monitoring must never break a request
        log.exception("Could not record API error")


@app.exception_handler(StarletteHTTPException)
async def http_exc(request: Request, exc: StarletteHTTPException):
    if exc.status_code >= 500:
        _record_error(request.url.path, exc.status_code, str(exc.detail))
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_exc(request: Request, exc: RequestValidationError):
    errors = [{"loc": [str(x) for x in e["loc"]], "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse({"detail": "Validation failed", "errors": errors}, status_code=422)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    _record_error(request.url.path, 500, type(exc).__name__)
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


API = "/api/v1"
for r in (auth, users, dashboard, problems, topics, goals, revisions, analytics, integrations, ai, admin):
    app.include_router(r.router, prefix=API)
app.include_router(health.router)
