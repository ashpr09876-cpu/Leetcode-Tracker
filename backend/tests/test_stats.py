from datetime import date, timedelta

from app.services.stats import compute_streaks, month_bounds, week_start
from tests.conftest import make_problem


def test_streak_math():
    t = date(2025, 3, 10)
    days = {t, t - timedelta(1), t - timedelta(2), t - timedelta(10), t - timedelta(11)}
    assert compute_streaks(days, t) == (3, 3)
    assert compute_streaks({t - timedelta(1), t - timedelta(2)}, t) == (2, 2)  # today not yet active
    assert compute_streaks({t - timedelta(5)}, t) == (0, 1)
    assert compute_streaks(set(), t) == (0, 0)


def test_week_and_month_bounds():
    assert week_start(date(2025, 3, 12)) == date(2025, 3, 10)
    assert month_bounds(date(2025, 2, 14)) == (date(2025, 2, 1), date(2025, 2, 28))


def test_dashboard_summary_from_real_records(client, auth):
    make_problem(client, auth, title="E", difficulty="easy", status="solved", attempts=2)
    make_problem(client, auth, title="M", difficulty="medium", status="mastered", attempts=1)
    make_problem(client, auth, title="H", difficulty="hard", status="attempted", attempts=3)
    s = client.get("/api/v1/dashboard/summary", headers=auth).json()
    assert (s["total_problems"], s["total_solved"], s["easy"], s["medium"], s["hard"]) == (3, 2, 1, 1, 0)
    assert s["today"] == {"solved": 2, "attempts": 6}
    assert s["current_streak"] == 1 and s["longest_streak"] == 1
    assert s["acceptance_rate"] is None and s["contest_rating"] is None  # nothing fabricated
    act = client.get("/api/v1/dashboard/activity", headers=auth).json()
    assert len(act["items"]) == 1 and act["items"][0]["solved"] == 2


def test_empty_dashboard(client, auth):
    s = client.get("/api/v1/dashboard/summary", headers=auth).json()
    assert s["total_solved"] == 0 and s["current_streak"] == 0 and s["upcoming_revisions"] == []


def test_status_change_records_one_solve(client, auth):
    p = make_problem(client, auth, status="attempted", attempts=1)
    client.patch(f"/api/v1/problems/{p['id']}", json={"status": "solved"}, headers=auth)
    client.patch(f"/api/v1/problems/{p['id']}", json={"status": "mastered"}, headers=auth)
    s = client.get("/api/v1/dashboard/summary", headers=auth).json()
    assert s["today"]["solved"] == 1


def test_timezone_changes_day_bucket(client, auth):
    make_problem(client, auth)
    r = client.patch("/api/v1/users/me", json={"timezone": "Pacific/Kiritimati"}, headers=auth)
    assert r.status_code == 200 and r.json()["timezone"] == "Pacific/Kiritimati"
    assert client.patch("/api/v1/users/me", json={"timezone": "Not/AZone"}, headers=auth).status_code == 422


def test_analytics(client, auth, topic_id):
    make_problem(client, auth, difficulty="easy", status="solved", topic_ids=[topic_id], confidence=5)
    make_problem(client, auth, title="b", difficulty="easy", status="attempted", topic_ids=[topic_id], confidence=1)
    d = {x["difficulty"]: x for x in client.get("/api/v1/analytics/difficulty", headers=auth).json()}
    assert d["easy"] == {"difficulty": "easy", "total": 2, "solved": 1} and d["hard"]["total"] == 0
    t = [x for x in client.get("/api/v1/analytics/topics", headers=auth).json() if x["topic_id"] == topic_id][0]
    assert t["total"] == 2 and t["solved"] == 1 and t["solve_rate"] == 50.0 and t["avg_confidence"] == 3.0
    o = client.get("/api/v1/analytics/overview", headers=auth).json()
    assert o["total_problems"] == 2 and o["status_counts"]["attempted"] == 1
    w = client.get("/api/v1/analytics/activity?granularity=week&periods=4", headers=auth).json()
    assert len(w) == 4 and w[-1]["solved"] == 1
    m = client.get("/api/v1/analytics/activity?granularity=month&periods=3", headers=auth).json()
    assert len(m) == 3 and m[-1]["solved"] == 1
