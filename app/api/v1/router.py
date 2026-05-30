from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.engine_proxy import router as engine_proxy_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.simulations import router as sim_router
from app.core.ws_proxy import ws_simulation_proxy

api_router = APIRouter()

# Health
api_router.include_router(health_router, tags=["Health"], include_in_schema=True)

# Auth
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])

# Saved simulations (Backend DB)
api_router.include_router(
    sim_router,
    prefix="/simulations",
    tags=["Saved Simulations"],
)

# Engine proxy (all Engine endpoints, JWT-protected)
api_router.include_router(
    engine_proxy_router,
    prefix="/engine",
    tags=["Engine Proxy"],
)

# WebSocket proxy for live simulation stream
api_router.add_websocket_route(
    "/engine/simulations/{simulation_id}/ws",
    ws_simulation_proxy,
)
