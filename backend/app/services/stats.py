"""All dashboard/analytics/goal calculations. Dates are computed in the user's timezone."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (SOLVED_STATUSES, ActivityRecord, Problem, Revision, Topic, User,
                        UserIntegration, problem_topics)


def user_tz(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def to_local_date(dt: datetime, tz: ZoneInfo) -> date:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).date()


def today_for(user: User) -> date:
    return datetime.now(timezone.utc).astimezone(user_tz(user)).date()


def log_activity(db: Session, user_id: int, problem_id: int | None, kind: str, count: int = 1,
                 when: datetime | None = None) -> None:
    if count <= 0:
        return
    db.add(ActivityRecord(user_id=user_id, problem_id=problem_id, kind=kind, count=count,
                          occurred_at=when or datetime.now(timezone.utc)))


def activity_by_day(db: Session, user: User) -> dict[date, dict[str, int]]:
    tz = user_tz(user)
    out: dict[date, dict[str, int]] = defaultdict(lambda: {"solved": 0, "attempts": 0})
    rows = db.scalars(select(ActivityRecord).where(ActivityRecord.user_id == user.id)).all()
    for r in rows:
        d = to_local_date(r.occurred_at, tz)
        out[d]["solved" if r.kind == "solve" else "attempts"] += r.count
    return out


def compute_streaks(active_days: set[date], today: date) -> tuple[int, int]:
    """Current streak counts back from today (or yesterday if today has no activity yet)."""
    current = 0
    cursor = today if today in active_days else today - timedelta(days=1)
    while cursor in active_days:
        current += 1
        cursor -= timedelta(days=1)
    longest = run = 0
    prev = None
    for d in sorted(active_days):
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        longest = max(longest, run)
        prev = d
    return current, longest


def sum_range(by_day: dict[date, dict[str, int]], start: date, end: date, metric: str) -> int:
    key = "solved" if metric == "solved" else "attempts"
    return sum(v[key] for d, v in by_day.items() if start <= d <= end)


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def month_bounds(d: date) -> tuple[date, date]:
    first = d.replace(day=1)
    nxt = (first + timedelta(days=32)).replace(day=1)
    return first, nxt - timedelta(days=1)


def get_intervals(user: User) -> list[int]:
    prefs = user.preferences
    return list(prefs.revision_intervals) if prefs and prefs.revision_intervals else [1, 3, 7, 14, 30, 60]


def summary(db: Session, user: User) -> dict:
    problems = db.scalars(select(Problem).where(Problem.user_id == user.id)).all()
    solved = [p for p in problems if p.status in SOLVED_STATUSES]
    by_day = activity_by_day(db, user)
    today = today_for(user)
    cur, longest = compute_streaks(set(by_day.keys()), today)
    ws = week_start(today)
    ms, me = month_bounds(today)
    revs = db.scalars(select(Revision).where(Revision.user_id == user.id, Revision.status == "pending")
                      .order_by(Revision.due_date)).all()
    integ = db.scalar(select(UserIntegration).where(UserIntegration.user_id == user.id,
                                                    UserIntegration.provider == "leetcode"))
    data = integ.data if integ else {}
    return {
        "total_problems": len(problems),
        "total_solved": len(solved),
        "easy": sum(1 for p in solved if p.difficulty == "easy"),
        "medium": sum(1 for p in solved if p.difficulty == "medium"),
        "hard": sum(1 for p in solved if p.difficulty == "hard"),
        "current_streak": cur,
        "longest_streak": longest,
        "today": {"solved": by_day[today]["solved"] if today in by_day else 0,
                  "attempts": by_day[today]["attempts"] if today in by_day else 0},
        "week": {"solved": sum_range(by_day, ws, today, "solved"), "attempts": sum_range(by_day, ws, today, "attempts")},
        "month": {"solved": sum_range(by_day, ms, me, "solved"), "attempts": sum_range(by_day, ms, me, "attempts")},
        "daily_goal": user.preferences.daily_goal if user.preferences else 1,
        "due_revisions": sum(1 for r in revs if r.due_date <= today),
        "upcoming_revisions": [
            {"id": r.id, "problem_id": r.problem_id, "problem_title": r.problem.title, "due_date": r.due_date.isoformat(),
             "priority": r.priority, "overdue": r.due_date < today} for r in revs[:5]],
        "acceptance_rate": data.get("acceptance_rate"),
        "contest_rating": data.get("contest_rating"),
        "leetcode": {"connected": integ is not None,
                     "last_sync_at": integ.last_sync_at.isoformat() if integ and integ.last_sync_at else None},
    }


def topic_stats(db: Session, user: User) -> list[dict]:
    topics = db.scalars(select(Topic).where(Topic.user_id == user.id).order_by(Topic.name)).all()
    rows = db.execute(
        select(problem_topics.c.topic_id, Problem.status, Problem.confidence)
        .join(Problem, Problem.id == problem_topics.c.problem_id).where(Problem.user_id == user.id)).all()
    agg: dict[int, list] = defaultdict(list)
    for tid, status, conf in rows:
        agg[tid].append((status, conf))
    out = []
    for t in topics:
        items = agg.get(t.id, [])
        solved = [i for i in items if i[0] in SOLVED_STATUSES]
        out.append({
            "topic_id": t.id, "name": t.name, "total": len(items), "solved": len(solved),
            "mastered": sum(1 for i in items if i[0] == "mastered"),
            "solve_rate": round(len(solved) / len(items) * 100, 1) if items else None,
            "avg_confidence": round(sum(i[1] for i in items) / len(items), 2) if items else None,
        })
    return out


def difficulty_stats(db: Session, user: User) -> list[dict]:
    problems = db.scalars(select(Problem).where(Problem.user_id == user.id)).all()
    return [{"difficulty": d, "total": sum(1 for p in problems if p.difficulty == d),
             "solved": sum(1 for p in problems if p.difficulty == d and p.status in SOLVED_STATUSES)}
            for d in ("easy", "medium", "hard")]


def activity_buckets(db: Session, user: User, granularity: str, periods: int) -> list[dict]:
    by_day = activity_by_day(db, user)
    today = today_for(user)
    buckets: dict[str, dict] = {}
    if granularity == "week":
        starts = [week_start(today) - timedelta(weeks=i) for i in range(periods - 1, -1, -1)]
        for s in starts:
            buckets[s.isoformat()] = {"period": s.isoformat(), "solved": 0, "attempts": 0, "active_days": 0}
        for d, v in by_day.items():
            key = week_start(d).isoformat()
            if key in buckets:
                buckets[key]["solved"] += v["solved"]; buckets[key]["attempts"] += v["attempts"]; buckets[key]["active_days"] += 1
    else:
        y, m = today.year, today.month
        keys = []
        for _ in range(periods):
            keys.append(f"{y:04d}-{m:02d}")
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        for k in reversed(keys):
            buckets[k] = {"period": k, "solved": 0, "attempts": 0, "active_days": 0}
        for d, v in by_day.items():
            key = f"{d.year:04d}-{d.month:02d}"
            if key in buckets:
                buckets[key]["solved"] += v["solved"]; buckets[key]["attempts"] += v["attempts"]; buckets[key]["active_days"] += 1
    return list(buckets.values())


def overview(db: Session, user: User) -> dict:
    problems = db.scalars(select(Problem).where(Problem.user_id == user.id)).all()
    solved = [p for p in problems if p.status in SOLVED_STATUSES]
    today = today_for(user)
    revs = db.scalars(select(Revision).where(Revision.user_id == user.id)).all()
    completed = sum(1 for r in revs if r.status == "completed")
    overdue = sum(1 for r in revs if r.status == "pending" and r.due_date < today)
    by_day = activity_by_day(db, user)
    active30 = sum(1 for i in range(30) if (today - timedelta(days=i)) in by_day)
    denom = completed + overdue
    return {
        "total_problems": len(problems), "total_solved": len(solved),
        "status_counts": {s: sum(1 for p in problems if p.status == s) for s in ("attempted", "solved", "needs_revision", "mastered")},
        "avg_confidence": round(sum(p.confidence for p in problems) / len(problems), 2) if problems else None,
        "avg_time_minutes": round(sum(p.time_spent_minutes for p in solved) / len(solved), 1) if solved else None,
        "total_attempts": sum(p.attempts for p in problems),
        "revisions": {"completed": completed, "pending": sum(1 for r in revs if r.status == "pending"),
                      "overdue": overdue, "skipped": sum(1 for r in revs if r.status == "skipped"),
                      "completion_rate": round(completed / denom * 100, 1) if denom else None},
        "consistency_30d": {"active_days": active30, "percent": round(active30 / 30 * 100, 1)},
    }


def ai_context(db: Session, user: User) -> dict:
    s = summary(db, user)
    topics = [t for t in topic_stats(db, user) if t["total"] > 0]
    weak = sorted(topics, key=lambda t: ((t["solve_rate"] or 0), t["avg_confidence"] or 0))[:5]
    recent = db.scalars(select(Problem).where(Problem.user_id == user.id).order_by(Problem.created_at.desc()).limit(10)).all()
    return {
        "totals": {k: s[k] for k in ("total_problems", "total_solved", "easy", "medium", "hard")},
        "streaks": {"current": s["current_streak"], "longest": s["longest_streak"]},
        "this_week": s["week"], "due_revisions": s["due_revisions"],
        "weakest_topics": weak,
        "topic_coverage": [{"name": t["name"], "total": t["total"], "solved": t["solved"]} for t in topics],
        "recent_problems": [{"title": p.title, "difficulty": p.difficulty, "status": p.status, "confidence": p.confidence} for p in recent],
        "overview": overview(db, user),
    }
