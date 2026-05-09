import re

import pytest

from src.links import crud


@pytest.mark.anyio
async def test_generate_short_id_default_shape():
    short_id = crud.generate_short_id()

    assert len(short_id) == 6
    assert re.fullmatch(r"[A-Za-z0-9]+", short_id)


@pytest.mark.anyio
async def test_generate_short_id_custom_length():
    assert len(crud.generate_short_id(length=12)) == 12


@pytest.mark.anyio
async def test_create_link_uses_custom_alias_as_short_id(session_factory):
    async with session_factory() as session:
        link = await crud.create_link(
            session,
            original_url="https://example.com/",
            custom_alias="docs",
            user_id=1,
        )

        assert link.short_id == "docs"
        assert link.click_count == 0
        assert link.user_id == 1


@pytest.mark.anyio
async def test_crud_update_search_increment_and_delete(session_factory):
    async with session_factory() as session:
        owner_link = await crud.create_link(
            session,
            original_url="https://example.com/articles/one",
            custom_alias="owned",
            user_id=1,
        )
        await crud.create_link(
            session,
            original_url="https://example.com/articles/two",
            custom_alias="other",
            user_id=2,
        )

        await crud.increment_click_count(session, owner_link)
        assert owner_link.click_count == 1

        updated = await crud.update_link(
            session,
            owner_link,
            "https://example.com/articles/updated",
        )
        assert updated.original_url == "https://example.com/articles/updated"

        found = await crud.search_links(session, "articles", user_id=1)
        assert [link.short_id for link in found] == ["owned"]

        await crud.delete_link(session, owner_link)
        assert await crud.get_link_by_short_id(session, "owned") is None
