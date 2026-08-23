from httpx import AsyncClient

USER_A = {"email": "task-owner@example.com", "password": "supersecret1"}
USER_B = {"email": "task-intruder@example.com", "password": "supersecret1"}


async def test_tasks_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/tasks")

    assert response.status_code == 401


async def test_task_crud_happy_path(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)

    create_response = await client.post("/api/tasks", json={"title": "Write plan"})
    assert create_response.status_code == 201
    task = create_response.json()
    assert task["status"] == "todo"

    list_response = await client.get("/api/tasks")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = await client.patch(
        f"/api/tasks/{task['id']}", json={"status": "in_progress"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "in_progress"

    delete_response = await client.delete(f"/api/tasks/{task['id']}")
    assert delete_response.status_code == 204

    get_after_delete = await client.get(f"/api/tasks/{task['id']}")
    assert get_after_delete.status_code == 404


async def test_task_status_filter(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)

    todo = await client.post("/api/tasks", json={"title": "Todo task"})
    done = await client.post("/api/tasks", json={"title": "Done task"})
    await client.patch(f"/api/tasks/{done.json()['id']}", json={"status": "done"})

    response = await client.get("/api/tasks", params={"status": "done"})

    assert response.status_code == 200
    titles = [task["title"] for task in response.json()]
    assert titles == ["Done task"]
    assert todo.json()["title"] not in titles


async def test_cannot_access_another_users_task(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)
    create_response = await client.post("/api/tasks", json={"title": "Private task"})
    task_id = create_response.json()["id"]

    await client.post("/api/auth/logout")
    await client.post("/api/auth/signup", json=USER_B)

    response = await client.get(f"/api/tasks/{task_id}")

    assert response.status_code == 404
