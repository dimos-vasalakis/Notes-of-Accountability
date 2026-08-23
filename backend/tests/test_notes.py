from httpx import AsyncClient

USER_A = {"email": "note-owner@example.com", "password": "supersecret1"}
USER_B = {"email": "note-intruder@example.com", "password": "supersecret1"}


async def test_notes_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/notes")

    assert response.status_code == 401


async def test_note_crud_happy_path(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)

    create_response = await client.post(
        "/api/notes", json={"title": "First note", "content": "# hello"}
    )
    assert create_response.status_code == 201
    note = create_response.json()

    list_response = await client.get("/api/notes")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = await client.get(f"/api/notes/{note['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "First note"

    update_response = await client.patch(
        f"/api/notes/{note['id']}", json={"title": "Updated title"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated title"
    assert update_response.json()["content"] == "# hello"

    delete_response = await client.delete(f"/api/notes/{note['id']}")
    assert delete_response.status_code == 204

    get_after_delete = await client.get(f"/api/notes/{note['id']}")
    assert get_after_delete.status_code == 404


async def test_cannot_access_another_users_note(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)
    create_response = await client.post(
        "/api/notes", json={"title": "Private", "content": ""}
    )
    note_id = create_response.json()["id"]

    await client.post("/api/auth/logout")
    await client.post("/api/auth/signup", json=USER_B)

    response = await client.get(f"/api/notes/{note_id}")

    assert response.status_code == 404
