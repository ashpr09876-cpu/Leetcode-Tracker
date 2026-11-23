# API
Interactive OpenAPI docs: http://localhost:8000/api/docs (JSON: `/api/openapi.json`). All endpoints under `/api/v1`, Bearer access token except auth/health. `POST /auth/refresh` and `/auth/logout` also need header `X-Requested-With: codetrack` (CSRF defence) and the refresh cookie.

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register` `login` `refresh` `logout` `forgot-password` `reset-password`, `GET /auth/me`, `GET /auth/providers`, `GET /auth/google/login`, `GET /auth/google/callback` |
| Users | `GET/PATCH/DELETE /users/me` |
| Dashboard | `GET /dashboard/summary` `activity` `topic-progress` `recent-problems` |
| Problems | `GET/POST /problems` (q, difficulty, status, topic_id, company_id, bookmarked, sort, page, page_size), `GET/PATCH/DELETE /problems/{id}`, `POST /problems/{id}/bookmark`, `POST /problems/{id}/revision`, `POST /problems/{id}/notes`, `DELETE /problems/{id}/notes/{note_id}` |
| Topics / companies | `GET/POST /topics`, `PATCH/DELETE /topics/{id}`, `GET /companies` |
| Goals | `GET/POST /goals`, `PATCH/DELETE /goals/{id}` |
| Revisions | `GET/POST /revisions`, `PATCH/DELETE /revisions/{id}` |
| Analytics | `GET /analytics/overview` `difficulty` `topics` `activity` |
| LeetCode | `POST /integrations/leetcode/connect`, `GET .../status`, `POST .../sync`, `DELETE .../disconnect` |
| AI | `GET /ai/status`, `POST /ai/chat` `analyze-performance` `recommendations` `roadmap` |
| Admin (admin only) | `GET /admin/users`, `PATCH /admin/users/{id}`, `GET /admin/system` |
| Health | `GET /health/live`, `GET /health/ready` |

Errors: `{"detail": "message"}`; validation: 422 with `errors[]`; AI: `{"detail": {"code": "ai_not_configured" | "ai_provider_error", "message": ...}}` (503 / 502).
