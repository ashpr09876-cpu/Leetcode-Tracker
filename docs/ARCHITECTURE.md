# Architecture
```
Browser (React SPA/PWA) --/api/v1--> FastAPI --SQLAlchemy--> PostgreSQL
                                        |--> Redis (readiness/health probe)
                                        |--> LeetCode public GraphQL (optional, unofficial)
                                        |--> AI provider: Ollama | Gemini | OpenAI | Anthropic (optional)
```
- **Same-origin API.** Dev server (Vite) and nginx (Docker) proxy `/api` to the backend, so the HttpOnly refresh cookie is first-party.
- **Backend layout:** `app/api/*` routers (HTTP + authorization) - `app/services/*` business logic (stats, revisions, AI providers) - `app/integrations/leetcode.py` isolated adapter - `app/models.py` tables - `app/schemas.py` Pydantic v2 - `app/core/*` config/security/rate limit - `alembic/` migrations. There is no separate repository layer: routers query via SQLAlchemy directly, with stats/revision logic in services (deliberate simplification).
- **Auth:** 15-min JWT access token (kept in memory by the SPA) + 14-day opaque refresh token (SHA-256 hashed in DB, HttpOnly cookie scoped to `/api/v1/auth`, rotated on every use, reuse of a rotated token revokes the whole family).
- **Statistics** are computed on read from `problems`, `activity_records`, `revisions` in the **user's timezone**. A day counts toward a streak if it has any attempt or solve event.
- **AI:** `AIProvider` interface + four adapters; the system prompt embeds the user's real aggregated stats; no provider configured => HTTP 503 `ai_not_configured` and the UI says so. Nothing is ever simulated.
- **PWA:** `public/manifest.webmanifest`, `public/sw.js`. The service worker never caches `/api/*` and only caches static assets plus an offline page.
- **Frontend:** React Router, TanStack Query (server state), Axios (token refresh interceptor), React Hook Form + Zod, Recharts, Tailwind v4 with CSS-variable theming (light/dark/system).
