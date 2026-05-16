from fastapi import FastAPI
from httpx import AsyncClient

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine, Base
from app.core.log_config import setup_logging, get_logger, RequestIdMiddleware

setup_logging(level=settings.log_level, log_file=settings.log_file)
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(RequestIdMiddleware)
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def on_startup() -> None:
    if settings.create_tables_on_startup:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created")

    app.state.httpx_client = AsyncClient(timeout=5.0)
    logger.info("Application startup complete — %s %s", settings.app_name, settings.app_version)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    client: AsyncClient | None = getattr(app.state, "httpx_client", None)
    if client is not None:
        await client.aclose()
    logger.info("Application shutdown complete")


@app.get("/", tags=["Root"])
def read_root() -> dict[str, str]:
    return {"message": f"{settings.app_name} running"}