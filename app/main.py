from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
def read_root() -> dict[str, str]:
    return {"message": f"{settings.app_name} running"}
