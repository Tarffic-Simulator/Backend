"""FastAPI application entrypoint and lifecycle hooks."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.limiter import limiter
from app.core.log_config import RequestIdMiddleware, get_logger, setup_logging

setup_logging(level=settings.log_level, log_file=settings.log_file)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.create_tables_on_startup:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    app.state.httpx_client = AsyncClient(timeout=5.0)
    logger.info(
        "Application startup complete — %s %s", settings.app_name, settings.app_version
    )

    yield

    client: AsyncClient | None = getattr(app.state, "httpx_client", None)
    if client is not None:
        await client.aclose()
    await engine.dispose()
    logger.info("Application shutdown complete")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
def read_root() -> dict[str, str]:
    return {"message": f"{settings.app_name} running"}
