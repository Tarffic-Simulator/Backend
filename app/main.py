from fastapi import FastAPI  # pyright: ignore[reportMissingImports]
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine, Base

# Esto crea las tablas en MySQL automáticamente al arrancar
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Root"])
def read_root() -> dict[str, str]:
    return {"message": f"{settings.app_name} running"}