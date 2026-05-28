from fastapi import APIRouter, Depends
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.http_client import get_httpx_client
from app.services.engine_client import check_engine_availability

router = APIRouter()


@router.get("/health")
async def healthcheck(
    db: AsyncSession = Depends(get_db),
    httpx_client: AsyncClient = Depends(get_httpx_client),
) -> dict:
    db_status = "ok"
    engine_status = "ok"
    engine_detail = None

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    engine_probe = await check_engine_availability(httpx_client)
    if engine_probe.get("status") != "ok":
        engine_status = "error"
        engine_detail = engine_probe.get("detail")

    overall = "ok" if db_status == "ok" and engine_status == "ok" else "degraded"
    payload = {"status": overall, "db": db_status, "engine": engine_status}
    if engine_detail:
        payload["engine_detail"] = engine_detail
    return payload
