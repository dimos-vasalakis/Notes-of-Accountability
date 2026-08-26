import pytest
from httpx import AsyncClient

from app.services import auth_service

EMAIL = "alice@example.com"
PASSWORD = "supersecret1"


@pytest.fixture(autouse=True)
def _reset_login_lockout() -> None:
    auth_service._failed_attempts.clear()


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


async def test_signup_normalizes_email_case(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/signup", json={"email": "Alice@Example.com", "password": PASSWORD}
    )
    response = await client.post(
        "/api/auth/signup", json={"email": "alice@example.com", "password": PASSWORD}
    )

    assert response.status_code == 409


async def test_login_case_insensitive_email(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    response = await client.post(
        "/api/auth/login", json={"email": "ALICE@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200


async def test_login_locks_out_after_repeated_failures(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})

    for _ in range(5):
        response = await client.post(
            "/api/auth/login", json={"email": EMAIL, "password": "wrong-password"}
        )
        assert response.status_code == 401

    locked_response = await client.post(
        "/api/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert locked_response.status_code == 429
    assert "Retry-After" in locked_response.headers


async def test_login_nonexistent_email_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert response.status_code == 401


async def test_refresh_token_reuse_revokes_all_sessions(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    stolen_refresh = client.cookies.get("refresh_token")

    # Legitimate rotation.
    first_refresh_response = await client.post("/api/auth/refresh")
    assert first_refresh_response.status_code == 204
    valid_refresh = client.cookies.get("refresh_token")

    # Replay of the now-revoked token should be rejected...
    client.cookies.set("refresh_token", stolen_refresh)
    reuse_response = await client.post("/api/auth/refresh")
    assert reuse_response.status_code == 401

    # ...and should have revoked the whole session family, including the
    # token that was legitimately issued by the rotation above.
    client.cookies.set("refresh_token", valid_refresh)
    followup_response = await client.post("/api/auth/refresh")
    assert followup_response.status_code == 401


async def test_logout_all_revokes_every_session(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD})

    response = await client.post("/api/auth/logout-all")
    assert response.status_code == 204

    refresh_response = await client.post("/api/auth/refresh")
    assert refresh_response.status_code == 401
