from tests.conftest import make_problem, register


def test_crud_and_pagination(client, auth, topic_id):
    p = make_problem(client, auth, topic_ids=[topic_id], confidence=4)
    assert p["topics"][0]["id"] == topic_id and p["solved_at"]
    r = client.patch(f"/api/v1/problems/{p['id']}", json={"title": "Two Sum II", "status": "mastered"}, headers=auth)
    assert r.json()["title"] == "Two Sum II" and r.json()["status"] == "mastered"
    assert client.get(f"/api/v1/problems/{p['id']}", headers=auth).json()["title"] == "Two Sum II"
    for i in range(5):
        make_problem(client, auth, title=f"P{i}", difficulty="hard", status="attempted")
    page = client.get("/api/v1/problems?page_size=2&page=2", headers=auth).json()
    assert page["total"] == 6 and len(page["items"]) == 2
    assert client.delete(f"/api/v1/problems/{p['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/v1/problems/{p['id']}", headers=auth).status_code == 404


def test_search_filter_sort(client, auth):
    make_problem(client, auth, title="Alpha", difficulty="easy", status="solved")
    make_problem(client, auth, title="Beta", difficulty="hard", status="attempted", leetcode_number=42)
    g = lambda q: client.get(f"/api/v1/problems?{q}", headers=auth).json()
    assert [i["title"] for i in g("q=alp")["items"]] == ["Alpha"]
    assert [i["title"] for i in g("q=42")["items"]] == ["Beta"]
    assert g("difficulty=hard")["total"] == 1 and g("status=solved")["total"] == 1
    assert [i["title"] for i in g("sort=title")["items"]] == ["Alpha", "Beta"]
    assert g("q=%25")["total"] == 0  # wildcard characters are escaped


def test_validation(client, auth):
    assert client.post("/api/v1/problems", json={"title": "", "difficulty": "easy"}, headers=auth).status_code == 422
    assert client.post("/api/v1/problems", json={"title": "x", "difficulty": "impossible"}, headers=auth).status_code == 422
    assert client.post("/api/v1/problems", json={"title": "x", "difficulty": "easy", "confidence": 9}, headers=auth).status_code == 422


def test_duplicate_leetcode_url(client, auth):
    url = "https://leetcode.com/problems/two-sum/"
    make_problem(client, auth, url=url)
    assert client.post("/api/v1/problems", json={"title": "again", "difficulty": "easy", "url": url}, headers=auth).status_code == 409


def test_bookmark_and_notes(client, auth):
    p = make_problem(client, auth)
    assert client.post(f"/api/v1/problems/{p['id']}/bookmark", headers=auth).json()["bookmarked"] is True
    assert client.get("/api/v1/problems?bookmarked=true", headers=auth).json()["total"] == 1
    n = client.post(f"/api/v1/problems/{p['id']}/notes", json={"body": "use a hash map"}, headers=auth).json()
    assert client.get(f"/api/v1/problems/{p['id']}", headers=auth).json()["notes"][0]["body"] == "use a hash map"
    assert client.delete(f"/api/v1/problems/{p['id']}/notes/{n['id']}", headers=auth).status_code == 204


def test_user_isolation(client):
    a = register(client, "a@example.com")
    p = make_problem(client, a, title="Private")
    client.cookies.clear()
    b = register(client, "b@example.com")
    assert client.get(f"/api/v1/problems/{p['id']}", headers=b).status_code == 404
    assert client.patch(f"/api/v1/problems/{p['id']}", json={"title": "hacked"}, headers=b).status_code == 404
    assert client.delete(f"/api/v1/problems/{p['id']}", headers=b).status_code == 404
    assert client.post(f"/api/v1/problems/{p['id']}/notes", json={"body": "x"}, headers=b).status_code == 404
    assert client.post("/api/v1/revisions", json={"problem_id": p["id"]}, headers=b).status_code == 404
    assert client.get("/api/v1/problems", headers=b).json()["total"] == 0
    # cannot attach another user's topic
    a_topic = client.get("/api/v1/topics", headers=a).json()[0]["id"]
    r = client.post("/api/v1/problems", json={"title": "x", "difficulty": "easy", "topic_ids": [a_topic]}, headers=b)
    assert r.status_code == 400


def test_topics(client, auth):
    topics = client.get("/api/v1/topics", headers=auth).json()
    assert len(topics) == 20 and any(t["name"] == "Two Pointers" for t in topics)
    t = client.post("/api/v1/topics", json={"name": "Segment Trees"}, headers=auth).json()
    assert client.post("/api/v1/topics", json={"name": "Segment Trees"}, headers=auth).status_code == 409
    assert client.patch(f"/api/v1/topics/{t['id']}", json={"name": "Fenwick Trees"}, headers=auth).json()["name"] == "Fenwick Trees"
    p = make_problem(client, auth, topic_ids=[t["id"]])
    assert client.delete(f"/api/v1/topics/{t['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/v1/problems/{p['id']}", headers=auth).json()["topics"] == []


def test_account_deletion_removes_data(client, auth):
    make_problem(client, auth)
    assert client.delete("/api/v1/users/me", headers=auth).status_code == 204
    assert client.get("/api/v1/auth/me", headers=auth).status_code == 401
