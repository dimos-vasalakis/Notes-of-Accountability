from httpx import AsyncClient

USER_A = {"email": "push-owner@example.com", "password": "supersecret1"}

SUBSCRIPTION = {
    "endpoint": "https://push.example.com/abc123",
    "keys": {"p256dh": "p256dh-key", "auth": "auth-key"},
}


async def test_push_subscriptions_require_authentication(client: AsyncClient) -> None:
    response = await client.post("/api/push-subscriptions", json=SUBSCRIPTION)

    assert response.status_code == 401


async def test_create_and_delete_subscription(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)

    create_response = await client.post("/api/push-subscriptions", json=SUBSCRIPTION)
    assert create_response.status_code == 201
    assert create_response.json()["endpoint"] == SUBSCRIPTION["endpoint"]

    delete_response = await client.request(
        "DELETE", "/api/push-subscriptions", json={"endpoint": SUBSCRIPTION["endpoint"]}
    )
    assert delete_response.status_code == 204


async def test_resubscribing_same_endpoint_upserts(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)

    first = await client.post("/api/push-subscriptions", json=SUBSCRIPTION)
    second = await client.post("/api/push-subscriptions", json=SUBSCRIPTION)

    assert first.json()["id"] == second.json()["id"]
