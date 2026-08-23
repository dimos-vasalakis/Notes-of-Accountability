from httpx import AsyncClient

EMAIL = "alice@example.com"
PASSWORD = "supersecret1"


async def test_signup_creates_user_and_sets_cookies(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/signup", json={"email": EMAIL, "password": PASSWORD}
    )

    assert response.status_code == 201
    assert response.json()["email"] == EMAIL
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


async def test_signup_duplicate_email_returns_409(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    response = await client.post(
        "/api/auth/signup", json={"email": EMAIL, "password": PASSWORD}
    )

    assert response.status_code == 409


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    response = await client.post(
        "/api/auth/login", json={"email": EMAIL, "password": "wrong-password"}
    )

    assert response.status_code == 401


async def test_login_success_sets_cookies(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    response = await client.post(
        "/api/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )

    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/auth/me")

    assert response.status_code == 401


async def test_me_returns_current_user_when_authenticated(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    response = await client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


async def test_refresh_rotates_tokens(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    old_refresh = client.cookies.get("refresh_token")

    response = await client.post("/api/auth/refresh")

    assert response.status_code == 204
    new_refresh = response.cookies.get("refresh_token")
    assert new_refresh is not None
    assert new_refresh != old_refresh


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})

    logout_response = await client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    refresh_response = await client.post("/api/auth/refresh")
    assert refresh_response.status_code == 401
