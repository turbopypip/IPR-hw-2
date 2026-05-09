import os
from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASS", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "55432")
os.environ.setdefault("DB_NAME", "shortist_test")
os.environ.setdefault("SECRET", "test-secret")
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:55432/shortist_test",
)

from src.auth.manager import current_optional_user, current_user  # noqa: E402
from src.auth.models import User  # noqa: E402
from src.database import Base, get_db  # noqa: E402
from src.links.models import Link  # noqa: F401, E402
from src.main import app  # noqa: E402


@dataclass
class AuthState:
    required_user: User
    optional_user: User | None = None


def make_user(user_id: int, email: str) -> User:
    return User(
        id=user_id,
        email=email,
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def owner() -> User:
    return make_user(1, "owner@example.com")


@pytest.fixture
def stranger() -> User:
    return make_user(2, "stranger@example.com")


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker]:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        session.add_all(
            [
                make_user(1, "owner@example.com"),
                make_user(2, "stranger@example.com"),
            ]
        )
        await session.commit()

    try:
        yield factory
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
async def api_client(
    session_factory: async_sessionmaker,
    owner: User,
) -> AsyncIterator[tuple[AsyncClient, AuthState]]:
    auth_state = AuthState(required_user=owner)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def override_current_user():
        return auth_state.required_user

    async def override_current_optional_user():
        return auth_state.optional_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = override_current_user
    app.dependency_overrides[current_optional_user] = override_current_optional_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, auth_state

    app.dependency_overrides.clear()
