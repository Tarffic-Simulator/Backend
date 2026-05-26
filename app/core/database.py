from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings


def _async_url(url_string: str) -> str:
    """Convert a sync SQLAlchemy URL to its async driver equivalent."""
    url = make_url(url_string)
    driver_map = {
        "mysql+pymysql": "mysql+aiomysql",
        "mysql": "mysql+aiomysql",
        "postgresql+psycopg2": "postgresql+asyncpg",
        "postgresql": "postgresql+asyncpg",
        "sqlite": "sqlite+aiosqlite",
    }
    new_driver = driver_map.get(url.drivername, url.drivername)
    return url.set(drivername=new_driver).render_as_string(hide_password=False)


engine = create_async_engine(_async_url(settings.database_url), echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
