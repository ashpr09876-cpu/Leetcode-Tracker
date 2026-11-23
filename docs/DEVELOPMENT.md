# Development
```powershell
# backend (from backend\)
.\.venv\Scripts\python.exe -m pytest -q            # tests use in-memory SQLite, no Docker needed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "add thing"
.\.venv\Scripts\python.exe -m alembic upgrade head
# frontend (from frontend\)
npm run dev      # http://localhost:5173, proxies /api -> :8000
npm test         # Vitest + React Testing Library
npm run build    # type-check + production build
npx playwright install chromium; npx playwright test   # E2E; needs the whole stack running
```
After the first successful `npm install`, commit `package-lock.json` (it could not be generated when this project was created). Same for pinning Python versions with `pip freeze` if you want exact reproducibility.

Backend tests cover: registration/login/invalid credentials, refresh rotation + reuse detection + CSRF header, protected routes, password reset, user isolation, problem CRUD/search/filter/pagination, topics, goals, revision scheduling and custom intervals, dashboard and analytics calculations, LeetCode adapter error mapping and failed-sync reporting, AI not-configured / provider-error / usage-limit paths, admin access control.
Note: dependency versions in `requirements.txt` and `package.json` were chosen from memory without being installed; if a pin conflicts, loosen it.
