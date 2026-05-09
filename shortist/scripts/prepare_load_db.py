import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.auth.models import User  # noqa: F401
from src.database import Base, async_engine
from src.links.models import Link  # noqa: F401


async def main() -> None:
    async_engine.echo = False
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(main())
