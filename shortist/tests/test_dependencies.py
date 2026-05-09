import pytest
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.auth import get_jwt_strategy
from src.auth.manager import UserManager, get_user_db, get_user_manager
from src.database import get_db


def test_jwt_strategy_uses_configured_lifetime():
    strategy = get_jwt_strategy()

    assert strategy.lifetime_seconds == 3600


@pytest.mark.anyio
async def test_database_dependency_yields_async_session():
    generator = get_db()
    session = await anext(generator)

    assert isinstance(session, AsyncSession)

    await generator.aclose()


@pytest.mark.anyio
async def test_auth_dependency_factories(session_factory):
    async with session_factory() as session:
        user_db_generator = get_user_db(session)
        user_db = await anext(user_db_generator)

        manager_generator = get_user_manager(user_db)
        manager = await anext(manager_generator)

        assert isinstance(user_db, SQLAlchemyUserDatabase)
        assert isinstance(manager, UserManager)

        await manager_generator.aclose()
        await user_db_generator.aclose()
