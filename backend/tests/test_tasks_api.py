def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_crud(client):
    r = client.post(
        "/api/tasks",
        json={"content": "补全单测", "priority": 7, "tags": ["test"]},
    )
    assert r.status_code == 200
    task = r.json()
    assert task["content"] == "补全单测"
    assert task["tags"] == ["test"]
    assert task["status"] == "pending"

    r = client.get("/api/tasks")
    assert r.json()["total"] == 1

    r = client.patch(f"/api/tasks/{task['id']}", json={"priority": 9})
    assert r.json()["priority"] == 9

    r = client.delete(f"/api/tasks/{task['id']}")
    assert r.status_code == 204
    assert client.get("/api/tasks").json()["total"] == 0


def test_batch_import(client):
    r = client.post(
        "/api/tasks/batch",
        json={"text": "任务A\n\n任务B\n任务C", "priority": 3},
    )
    created = r.json()["created"]
    assert len(created) == 3
    assert created[0]["content"] == "任务A"


def test_list_sort_and_filter(client):
    for content, priority in [("低", 2), ("高", 8), ("中", 5)]:
        client.post("/api/tasks", json={"content": content, "priority": priority})
    items = client.get("/api/tasks").json()["items"]
    assert [i["priority"] for i in items] == [8, 5, 2]

    items = client.get("/api/tasks", params={"q": "高"}).json()["items"]
    assert len(items) == 1
