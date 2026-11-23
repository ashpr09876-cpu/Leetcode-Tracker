from datetime import date, timedelta

from tests.conftest import make_problem


def test_goal_progress_and_completion(client, auth):
    g = client.post("/api/v1/goals", json={"title": "Solve 2", "period": "daily", "target": 2}, headers=auth).json()
    assert g["progress"] == 0 and not g["completed"] and g["active"]
    make_problem(client, auth, title="a")
    assert client.get("/api/v1/goals", headers=auth).json()[0]["progress"] == 1
    make_problem(client, auth, title="b")
    done = client.get("/api/v1/goals", headers=auth).json()[0]
    assert done["completed"] and done["completed_at"]
    assert client.patch(f"/api/v1/goals/{g['id']}", json={"target": 5}, headers=auth).json()["completed"] is False
    assert client.delete(f"/api/v1/goals/{g['id']}", headers=auth).status_code == 204


def test_goal_validation(client, auth):
    assert client.post("/api/v1/goals", json={"title": "x", "period": "custom", "target": 1}, headers=auth).status_code == 422
    bad = {"title": "x", "period": "custom", "target": 1, "start_date": "2025-02-02", "end_date": "2025-02-01"}
    assert client.post("/api/v1/goals", json=bad, headers=auth).status_code == 422
    assert client.post("/api/v1/goals", json={"title": "x", "period": "weekly", "target": 0}, headers=auth).status_code == 422


def test_revision_lifecycle_and_spaced_repetition(client, auth):
    p = make_problem(client, auth)
    r = client.post(f"/api/v1/problems/{p['id']}/revision", json={}, headers=auth).json()
    assert r["status"] == "pending" and r["stage"] == 0
    assert 0 <= (date.fromisoformat(r["due_date"]) - date.today()).days <= 2  # default first interval = 1 day (tz may shift by a day)
    assert client.post("/api/v1/revisions", json={"problem_id": p["id"]}, headers=auth).status_code == 409
    done = client.patch(f"/api/v1/revisions/{r['id']}", json={"status": "completed"}, headers=auth).json()
    assert done["status"] == "completed" and done["completed_at"]
    pending = client.get("/api/v1/revisions?status=pending", headers=auth).json()
    assert len(pending) == 1 and pending[0]["stage"] == 1  # next interval scheduled (3 days by default)
    gap = (date.fromisoformat(pending[0]["due_date"]) - date.fromisoformat(r["due_date"])).days
    assert 1 <= gap <= 3
    assert client.patch(f"/api/v1/revisions/{r['id']}", json={"status": "skipped"}, headers=auth).status_code == 409


def test_custom_intervals_and_due_list(client, auth):
    client.patch("/api/v1/users/me", json={"preferences": {"revision_intervals": [2, 5]}}, headers=auth)
    p = make_problem(client, auth)
    r = client.post("/api/v1/revisions", json={"problem_id": p["id"], "due_date": "2000-01-01", "priority": "high"}, headers=auth).json()
    assert r["overdue"] is True
    assert len(client.get("/api/v1/revisions?due_only=true", headers=auth).json()) == 1
    assert client.get("/api/v1/dashboard/summary", headers=auth).json()["due_revisions"] == 1
    client.patch(f"/api/v1/revisions/{r['id']}", json={"status": "completed"}, headers=auth)  # stage 1 of 2 -> one more
    nxt = client.get("/api/v1/revisions?status=pending", headers=auth).json()[0]
    client.patch(f"/api/v1/revisions/{nxt['id']}", json={"status": "completed"}, headers=auth)  # final stage
    assert client.get("/api/v1/revisions?status=pending", headers=auth).json() == []
    assert client.patch("/api/v1/users/me", json={"preferences": {"revision_intervals": []}}, headers=auth).status_code == 422
    assert client.delete(f"/api/v1/revisions/{r['id']}", headers=auth).status_code == 204
