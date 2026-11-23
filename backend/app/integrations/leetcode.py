"""Isolated LeetCode adapter.

IMPORTANT: LeetCode has no official, stable public API. This adapter calls the public (unofficial,
undocumented) GraphQL endpoint used by the website, for public profile data only. It never asks for
passwords or session cookies. It may break or be rate-limited at any time; the app works without it.
"""
import httpx

GRAPHQL_URL = "https://leetcode.com/graphql"


class LeetCodeError(Exception):
    pass


class LeetCodeNotFound(LeetCodeError):
    pass


class LeetCodeRateLimited(LeetCodeError):
    pass


class LeetCodeUnavailable(LeetCodeError):
    pass


TAG_MAP = {
    "Array": "Arrays", "String": "Strings", "Hash Table": "Hash Tables", "Linked List": "Linked Lists",
    "Stack": "Stacks", "Queue": "Queues", "Tree": "Trees", "Binary Tree": "Trees",
    "Binary Search Tree": "Binary Search Trees", "Heap (Priority Queue)": "Heaps", "Graph": "Graphs",
    "Breadth-First Search": "Graphs", "Depth-First Search": "Graphs", "Dynamic Programming": "Dynamic Programming",
    "Greedy": "Greedy Algorithms", "Backtracking": "Backtracking", "Recursion": "Recursion", "Sorting": "Sorting",
    "Binary Search": "Searching", "Bit Manipulation": "Bit Manipulation", "Trie": "Tries",
    "Sliding Window": "Sliding Window", "Two Pointers": "Two Pointers",
}

PROFILE_Q = """query userProfile($username: String!) {
  matchedUser(username: $username) { username
    submitStatsGlobal { acSubmissionNum { difficulty count submissions } totalSubmissionNum { difficulty count submissions } } }
  userContestRanking(username: $username) { rating } }"""
RECENT_Q = """query recentAc($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) { id title titleSlug timestamp } }"""
QUESTION_Q = """query q($titleSlug: String!) {
  question(titleSlug: $titleSlug) { questionFrontendId title titleSlug difficulty topicTags { name } } }"""


class LeetCodeClient:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def _query(self, query: str, variables: dict) -> dict:
        try:
            r = httpx.post(GRAPHQL_URL, json={"query": query, "variables": variables}, timeout=self.timeout,
                           headers={"Content-Type": "application/json", "Referer": "https://leetcode.com",
                                    "User-Agent": "CodeTrack/1.0 (personal progress tracker)"})
        except httpx.HTTPError as e:
            raise LeetCodeUnavailable(f"Could not reach LeetCode ({type(e).__name__})") from e
        if r.status_code == 429:
            raise LeetCodeRateLimited("LeetCode is rate limiting requests. Try again later.")
        if r.status_code >= 400:
            raise LeetCodeUnavailable(f"LeetCode returned HTTP {r.status_code}")
        try:
            body = r.json()
        except ValueError as e:
            raise LeetCodeUnavailable("LeetCode returned an invalid response") from e
        if not isinstance(body, dict):
            raise LeetCodeUnavailable("LeetCode returned an unexpected response")
        if body.get("errors"):
            msg = str(body["errors"])[:200]
            if "does not exist" in msg.lower():
                raise LeetCodeNotFound("LeetCode user or problem not found")
            raise LeetCodeUnavailable(f"LeetCode reported an error: {msg}")
        data = body.get("data")
        return data if isinstance(data, dict) else {}

    def fetch_profile(self, username: str) -> dict:
        data = self._query(PROFILE_Q, {"username": username})
        user = data.get("matchedUser")
        if not user:
            raise LeetCodeNotFound(f"LeetCode user '{username}' was not found")
        stats = (user.get("submitStatsGlobal") or {})
        ac = {i.get("difficulty"): i for i in stats.get("acSubmissionNum") or [] if isinstance(i, dict)}
        total = {i.get("difficulty"): i for i in stats.get("totalSubmissionNum") or [] if isinstance(i, dict)}
        rate = None
        try:
            ac_sub, tot_sub = int(ac["All"]["submissions"]), int(total["All"]["submissions"])
            rate = round(ac_sub / tot_sub * 100, 1) if tot_sub > 0 else None
        except (KeyError, TypeError, ValueError):
            rate = None
        rating = None
        contest = data.get("userContestRanking")
        if isinstance(contest, dict) and isinstance(contest.get("rating"), (int, float)):
            rating = round(contest["rating"])
        solved = {}
        for k in ("All", "Easy", "Medium", "Hard"):
            try:
                solved[k.lower()] = int(ac[k]["count"])
            except (KeyError, TypeError, ValueError):
                solved[k.lower()] = None
        return {"username": user.get("username", username), "solved": solved, "acceptance_rate": rate,
                "contest_rating": rating}

    def fetch_recent_accepted(self, username: str, limit: int = 20) -> list[dict]:
        data = self._query(RECENT_Q, {"username": username, "limit": limit})
        out = []
        for item in data.get("recentAcSubmissionList") or []:
            try:
                out.append({"title": str(item["title"]), "slug": str(item["titleSlug"]), "timestamp": int(item["timestamp"])})
            except (KeyError, TypeError, ValueError):
                continue
        return out

    def fetch_question(self, slug: str) -> dict:
        data = self._query(QUESTION_Q, {"titleSlug": slug})
        q = data.get("question")
        if not isinstance(q, dict) or str(q.get("difficulty", "")).lower() not in ("easy", "medium", "hard"):
            raise LeetCodeUnavailable(f"Unexpected question data for '{slug}'")
        try:
            number = int(q.get("questionFrontendId"))
        except (TypeError, ValueError):
            number = None
        tags = [TAG_MAP[t["name"]] for t in q.get("topicTags") or [] if isinstance(t, dict) and t.get("name") in TAG_MAP]
        return {"number": number, "title": str(q.get("title") or slug), "difficulty": q["difficulty"].lower(),
                "topics": sorted(set(tags))}
