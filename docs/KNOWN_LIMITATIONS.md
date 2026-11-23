# Known limitations and what was NOT verified
**Not executed (environment had no network/Docker/PostgreSQL):** `pip install`, `npm install`, backend pytest, frontend Vitest, `tsc`/`vite build`, Playwright E2E, Alembic migration, `docker compose up`, PowerShell scripts, live Google/LeetCode/AI calls. What *was* run: Python `py_compile` on every backend file, a TypeScript parse (syntax) check on every frontend file, YAML parsing of `docker-compose.yml`, and PNG icon generation.
**Missing lockfiles:** `package-lock.json` could not be generated. Package versions are unverified pins.
**Spec deviations / gaps:**
- No separate repository layer; `problems`+`user_problems` merged; no `daily_activity`/`bookmarks` tables (see DATABASE.md).
- Initial Alembic migration is metadata-based, not hand-written operations.
- Redis is used only for the readiness/admin health check (rate limiting is in-memory).
- Notification preference is stored but no reminders are sent. No email delivery.
- Admin UI covers user enable/disable and system status; no role editing UI.
- The AI Coach keeps chat history in the page session (messages are persisted server-side but there is no history browser).
- Offline mode shows a fallback page only; app data is intentionally not cached.
- Revision "stages" stop after the last configured interval.
- Frontend tests mock the API layer; E2E needs a running stack.
