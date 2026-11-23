"""Optional demo data. Creates a clearly labelled DEMO account; never touches real accounts.

Usage (from backend/):  python seed_demo.py
Login: demo@codetrack.local / DemoPass123!   (local development only -- delete this account before sharing a deployment)
"""
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.api.auth import create_user
from app.db.session import open_session
from app.models import Problem, Topic, User
from app.services.stats import log_activity

EMAIL = "demo@codetrack.local"
SAMPLE = [("Two Sum", "easy", "Arrays"), ("Valid Parentheses", "easy", "Stacks"), ("Merge Two Sorted Lists", "easy", "Linked Lists"),
          ("Longest Substring Without Repeating Characters", "medium", "Sliding Window"), ("Number of Islands", "medium", "Graphs"),
          ("Coin Change", "medium", "Dynamic Programming"), ("Binary Tree Level Order Traversal", "medium", "Trees"),
          ("Trapping Rain Water", "hard", "Two Pointers"), ("Word Break", "medium", "Dynamic Programming")]


def main() -> None:
    db = open_session()
    if db.scalar(select(User).where(User.email == EMAIL)):
        print("Demo user already exists."); return
    user = create_user(db, EMAIL, "Demo User (sample data)", "DemoPass123!")
    topics = {t.name: t for t in db.scalars(select(Topic).where(Topic.user_id == user.id)).all()}
    rng = random.Random(7)
    now = datetime.now(timezone.utc)
    for i, (title, diff, topic) in enumerate(SAMPLE):
        when = now - timedelta(days=i * 2)
        p = Problem(user_id=user.id, title=f"[DEMO] {title}", difficulty=diff, status=rng.choice(["solved", "mastered", "needs_revision"]),
                    attempts=rng.randint(1, 4), confidence=rng.randint(2, 5), time_spent_minutes=rng.randint(10, 60),
                    solved_at=when, source="demo", topics=[topics[topic]])
        db.add(p); db.flush()
        log_activity(db, user.id, p.id, "attempt", p.attempts, when=when)
        log_activity(db, user.id, p.id, "solve", 1, when=when)
    db.commit()
    print(f"Created demo account {EMAIL} with {len(SAMPLE)} sample problems (all titles start with [DEMO]).")


if __name__ == "__main__":
    main()
