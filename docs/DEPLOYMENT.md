# Deployment & optional configuration
## Local Docker
`scripts\start.ps1 -Docker` (profile `full`). Production hosting needs: HTTPS, `ENV=production`, a long random `SECRET_KEY` (the app refuses to start otherwise), `COOKIE_SECURE=true`, `CORS_ORIGINS`/`FRONTEND_URL` set to your real origin, a managed PostgreSQL, backups, and a reverse proxy. Remove the demo account.
## Google login (optional)
Google Cloud Console > APIs & Services > Credentials > OAuth client (Web). Authorized redirect URI: `http://localhost:8000/api/v1/auth/google/callback` (dev) or `http://localhost:8080/api/v1/auth/google/callback` (Docker). Put the id/secret in `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`, restart. Without them the login page states that Google login is not configured.
## AI (optional) - set `AI_PROVIDER` plus the matching key in `backend/.env` (or `.env` for Docker)
- `ollama` (free, local): install Ollama, `ollama pull llama3.1`, set `OLLAMA_BASE_URL=http://localhost:11434` (from Docker: `http://host.docker.internal:11434`).
- `gemini` (`GEMINI_API_KEY`, free tier available), `openai` (`OPENAI_API_KEY`), `anthropic` (`ANTHROPIC_API_KEY`).
All four adapters are implemented the same way over HTTPS; **none has been tested against a live service** by the author of this scaffold. Users can pick among configured providers in Settings. Usage limit: `AI_DAILY_LIMIT` requests/user/day.
## Email
Not implemented. Password-reset links are written to the backend log. Add an SMTP/API sender in `app/api/auth.py::forgot_password` for real deployments.
## LeetCode sync
Uses LeetCode's unofficial public GraphQL endpoint for public data only; it can break or be rate-limited at any time and sees only your ~20 most recent accepted submissions. Manual entry always works.
