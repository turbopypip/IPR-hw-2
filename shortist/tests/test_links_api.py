from datetime import datetime, timedelta, timezone

import pytest

from src.links import crud
from src.links.exceptions import NotUniqueAliasError


def link_payload(url="https://example.com", alias=None):
    payload = {"original_url": url, "expire_at": None}
    if alias is not None:
        payload["custom_alias"] = alias
    return payload


@pytest.mark.anyio
async def test_anonymous_user_can_create_short_link(api_client):
    client, auth = api_client
    auth.optional_user = None

    response = await client.post(
        "/links/shorten",
        json=link_payload("https://example.com/docs"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["original_url"] == "https://example.com/docs"
    assert len(body["short_id"]) == 6
    assert body["custom_alias"] is None


@pytest.mark.anyio
async def test_create_link_validates_payload(api_client):
    client, _ = api_client

    response = await client.post(
        "/links/shorten",
        json=link_payload("not-a-url", "??"),
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_link_rejects_past_expiration(api_client):
    client, _ = api_client

    response = await client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com",
            "custom_alias": None,
            "expire_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_alias_error_returns_bad_request(api_client, monkeypatch):
    client, _ = api_client

    async def raise_alias_error(**kwargs):
        raise NotUniqueAliasError("alias1")

    monkeypatch.setattr("src.links.routers.crud.create_link", raise_alias_error)

    response = await client.post(
        "/links/shorten",
        json=link_payload("https://example.com", "alias1"),
    )

    assert response.status_code == 400
    assert "alias1" in response.json()["detail"]


@pytest.mark.anyio
async def test_redirect_returns_location_and_increments_clicks(api_client):
    client, auth = api_client
    auth.optional_user = auth.required_user

    await client.post(
        "/links/shorten",
        json=link_payload("https://example.com/path", "go123"),
    )
    response = await client.get("/links/go123", follow_redirects=False)
    stats = await client.get("/links/go123/stats")

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/path"
    assert stats.json()["click_count"] == 1


@pytest.mark.anyio
async def test_redirect_unknown_link_returns_not_found(api_client):
    client, _ = api_client

    response = await client.get("/links/missing", follow_redirects=False)

    assert response.status_code == 404
    assert response.json()["detail"] == "Link not found"


@pytest.mark.anyio
async def test_owner_can_read_stats_search_update_and_delete_link(
    api_client,
    session_factory,
):
    client, auth = api_client
    auth.optional_user = auth.required_user

    created = await client.post(
        "/links/shorten",
        json=link_payload("https://docs.example.com/old", "owned"),
    )
    assert created.status_code == 200

    async with session_factory() as session:
        await crud.create_link(
            session,
            original_url="https://docs.example.com/hidden",
            custom_alias="other",
            user_id=2,
        )

    stats = await client.get("/links/owned/stats")
    search = await client.get("/links/search/", params={"original_url": "docs"})
    updated = await client.put(
        "/links/owned",
        json={"original_url": "https://docs.example.com/new", "expire_at": None},
    )
    deleted = await client.delete("/links/owned")
    missing_after_delete = await client.get("/links/owned/stats")

    assert stats.status_code == 200
    assert stats.json()["short_id"] == "owned"
    assert [item["short_id"] for item in search.json()] == ["owned"]
    assert updated.status_code == 200
    assert updated.json()["original_url"] == "https://docs.example.com/new"
    assert deleted.status_code == 200
    assert deleted.json() == {"status": "success"}
    assert missing_after_delete.status_code == 404


@pytest.mark.anyio
async def test_user_cannot_manage_someone_elses_link(api_client, session_factory, stranger):
    client, auth = api_client

    async with session_factory() as session:
        await crud.create_link(
            session,
            original_url="https://private.example.com",
            custom_alias="priv",
            user_id=1,
        )

    auth.required_user = stranger

    stats = await client.get("/links/priv/stats")
    updated = await client.put(
        "/links/priv",
        json={"original_url": "https://private.example.com/new", "expire_at": None},
    )
    deleted = await client.delete("/links/priv")

    assert stats.status_code == 404
    assert updated.status_code == 404
    assert deleted.status_code == 404
