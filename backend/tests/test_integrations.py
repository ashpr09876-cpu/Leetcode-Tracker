from app.api import integrations
from app.integrations.leetcode import LeetCodeClient, LeetCodeNotFound, LeetCodeRateLimited, LeetCodeUnavailable
from app.main import app
from app.services import ai


class FakeClient:
    def __init__(self, profile=None, recent=None, question=None, fail=None):
        self.p, self.r, self.q, self.fail = profile, recent or [], question, fail

    def fetch_profile(self, u):
        if self.fail == "profile":
            raise LeetCodeNotFound("LeetCode user not found")
        return self.p or {"username": u, "solved": {}, "acceptance_rate": 61.5, "contest_rating": 1710}

    def fetch_recent_accepted(self, u, limit=20):
        return self.r

    def fetch_question(self, slug):
        if self.fail == "question":
            raise LeetCodeRateLimited("rate limited")
        return {"number": 1, "title": "Two Sum", "difficulty": "easy", "topics": ["Arrays", "Hash Tables"]}


def use(client_obj):
    app.dependency_overrides[integrations.get_client] = lambda: client_obj


def teardown_function():
    app.dependency_overrides.clear()


def test_connect_sync_dedupe(client, auth):
    use(FakeClient(recent=[{"title": "Two Sum", "slug": "two-sum", "timestamp": 1700000000}]))
    assert client.get("/api/v1/integrations/leetcode/status", headers=auth).json()["connected"] is False
    st = client.post("/api/v1/integrations/leetcode/connect", json={"username": "someone"}, headers=auth).json()
    assert st["connected"] and st["acceptance_rate"] == 61.5
    r = client.post("/api/v1/integrations/leetcode/sync", headers=auth).json()
    assert r["ok"] and r["imported"] == 1 and r["last_sync_at"]
    again = client.post("/api/v1/integrations/leetcode/sync", headers=auth).json()
    assert again["imported"] == 0 and again["skipped_existing"] == 1  # no duplicates
    p = client.get("/api/v1/problems", headers=auth).json()["items"][0]
    assert p["source"] == "leetcode" and {t["name"] for t in p["topics"]} == {"Arrays", "Hash Tables"}
    assert client.get("/api/v1/dashboard/summary", headers=auth).json()["contest_rating"] == 1710
    assert client.delete("/api/v1/integrations/leetcode/disconnect", headers=auth).json() == {"connected": False}


def test_unknown_user(client, auth):
    use(FakeClient(fail="profile"))
    assert client.post("/api/v1/integrations/leetcode/connect", json={"username": "ghost"}, headers=auth).status_code == 404
    assert client.post("/api/v1/integrations/leetcode/connect", json={"username": "bad name!"}, headers=auth).status_code == 422


def test_sync_failure_is_reported_not_hidden(client, auth):
    use(FakeClient(recent=[{"title": "Two Sum", "slug": "two-sum", "timestamp": 1700000000}]))
    client.post("/api/v1/integrations/leetcode/connect", json={"username": "someone"}, headers=auth)
    use(FakeClient(recent=[{"title": "Two Sum", "slug": "two-sum", "timestamp": 1700000000}], fail="question"))
    r = client.post("/api/v1/integrations/leetcode/sync", headers=auth)
    assert r.status_code == 429
    st = client.get("/api/v1/integrations/leetcode/status", headers=auth).json()
    assert st["last_error"] and st["last_sync_at"] is None
    assert client.get("/api/v1/problems", headers=auth).json()["total"] == 0  # app still works


def test_sync_requires_connection(client, auth):
    assert client.post("/api/v1/integrations/leetcode/sync", headers=auth).status_code == 400


def test_adapter_error_mapping(monkeypatch):
    import httpx

    class R:
        def __init__(self, code, body=None, bad=False):
            self.status_code, self._b, self._bad = code, body, bad

        def json(self):
            if self._bad:
                raise ValueError("x")
            return self._b

    def run(resp):
        monkeypatch.setattr(httpx, "post", lambda *a, **k: resp)
        return LeetCodeClient().fetch_profile("u")

    import pytest
    with pytest.raises(LeetCodeRateLimited): run(R(429))
    with pytest.raises(LeetCodeUnavailable): run(R(503))
    with pytest.raises(LeetCodeUnavailable): run(R(200, bad=True))
    with pytest.raises(LeetCodeUnavailable): run(R(200, ["not", "a", "dict"]))
    with pytest.raises(LeetCodeNotFound): run(R(200, {"data": {"matchedUser": None}}))
    monkeypatch.setattr(httpx, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("down")))
    with pytest.raises(LeetCodeUnavailable): LeetCodeClient().fetch_profile("u")
    ok = {"data": {"matchedUser": {"username": "u", "submitStatsGlobal": {
        "acSubmissionNum": [{"difficulty": "All", "count": 10, "submissions": 20}, {"difficulty": "Easy", "count": 5, "submissions": 6}],
        "totalSubmissionNum": [{"difficulty": "All", "count": 40, "submissions": 80}]}}, "userContestRanking": {"rating": 1500.4}}}
    prof = run(R(200, ok))
    assert prof["acceptance_rate"] == 25.0 and prof["contest_rating"] == 1500 and prof["solved"]["easy"] == 5


# ---- AI
def test_ai_unconfigured_is_clear_and_never_fake(client, auth):
    st = client.get("/api/v1/ai/status", headers=auth).json()
    assert st["configured"] is False
    for path, body in (("chat", {"message": "hi"}), ("analyze-performance", {}), ("recommendations", {}), ("roadmap", {})):
        r = client.post(f"/api/v1/ai/{path}", json=body, headers=auth)
        assert r.status_code == 503 and r.json()["detail"]["code"] == "ai_not_configured"


def _configure_ollama(monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "ollama_base_url", "http://ollama.invalid:11434")
    monkeypatch.setattr(get_settings(), "ai_provider", "ollama")


def test_ai_provider_error_maps_to_502(client, auth, monkeypatch):
    _configure_ollama(monkeypatch)
    monkeypatch.setattr(ai.OllamaProvider, "complete", lambda self, s, m: (_ for _ in ()).throw(ai.AIProviderError("ollama request timed out")))
    r = client.post("/api/v1/ai/chat", json={"message": "help"}, headers=auth)
    assert r.status_code == 502 and "timed out" in r.json()["detail"]["message"]


def test_ai_success_uses_user_stats_and_persists(client, auth, monkeypatch):
    _configure_ollama(monkeypatch)
    seen = {}

    def fake(self, system, messages):
        seen["system"], seen["messages"] = system, messages
        return "Focus on graphs."

    monkeypatch.setattr(ai.OllamaProvider, "complete", fake)
    from tests.conftest import make_problem
    make_problem(client, auth, title="Real Problem")
    r = client.post("/api/v1/ai/analyze-performance", json={}, headers=auth).json()
    assert r["reply"] == "Focus on graphs." and r["provider"] == "ollama"
    assert "Real Problem" in seen["system"] and '"total_solved": 1' in seen["system"]
    follow = client.post("/api/v1/ai/chat", json={"message": "more?", "conversation_id": r["conversation_id"]}, headers=auth).json()
    assert len(seen["messages"]) == 3 and follow["conversation_id"] == r["conversation_id"]
    assert client.get("/api/v1/ai/status", headers=auth).json()["used_today"] == 2


def test_ai_usage_limit(client, auth, monkeypatch):
    _configure_ollama(monkeypatch)
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "ai_daily_limit", 1)
    monkeypatch.setattr(ai.OllamaProvider, "complete", lambda self, s, m: "ok")
    assert client.post("/api/v1/ai/chat", json={"message": "one"}, headers=auth).status_code == 200
    assert client.post("/api/v1/ai/chat", json={"message": "two"}, headers=auth).status_code == 429


def test_ai_conversation_isolation(client, monkeypatch):
    from tests.conftest import register
    _configure_ollama(monkeypatch)
    monkeypatch.setattr(ai.OllamaProvider, "complete", lambda self, s, m: "ok")
    a = register(client, "a@example.com")
    cid = client.post("/api/v1/ai/chat", json={"message": "hi"}, headers=a).json()["conversation_id"]
    client.cookies.clear()
    b = register(client, "b@example.com")
    assert client.post("/api/v1/ai/chat", json={"message": "x", "conversation_id": cid}, headers=b).status_code == 404


def test_admin_access_control(client, auth):
    assert client.get("/api/v1/admin/users", headers=auth).status_code == 403
    assert client.get("/api/v1/admin/system", headers=auth).status_code == 403
    assert client.get("/api/v1/admin/users").status_code == 401


def test_admin_functions(client, monkeypatch):
    from app.core.config import get_settings
    from tests.conftest import register
    monkeypatch.setattr(get_settings(), "admin_email", "root@example.com")
    admin = register(client, "root@example.com")
    client.cookies.clear()
    register(client, "u@example.com")
    users = client.get("/api/v1/admin/users", headers=admin).json()
    assert users["total"] == 2
    uid = [u["id"] for u in users["items"] if u["email"] == "u@example.com"][0]
    assert client.patch(f"/api/v1/admin/users/{uid}", json={"is_active": False}, headers=admin).json()["is_active"] is False
    assert client.post("/api/v1/auth/login", json={"email": "u@example.com", "password": "password123"}).status_code == 403
    me = [u["id"] for u in users["items"] if u["email"] == "root@example.com"][0]
    assert client.patch(f"/api/v1/admin/users/{me}", json={"is_active": False}, headers=admin).status_code == 400
    sysinfo = client.get("/api/v1/admin/system", headers=admin).json()
    assert sysinfo["database"] == "ok" and "redis" in sysinfo and "ai_providers_configured" in sysinfo
