"""WebSocket proxy: tunnels the Engine's simulation WebSocket to the client.

The Backend validates the JWT (passed as a query-param because browsers cannot
set Authorization headers on WebSocket connections), then opens a WebSocket
connection to the Engine and relays messages bidirectionally until either side
disconnects.

Usage (registered in router.py):
    router.add_websocket_route(
        "/engine/simulations/{simulation_id}/ws",
        ws_simulation_proxy,
    )
"""

from __future__ import annotations

import asyncio

import httpx
from fastapi import WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.log_config import get_logger
from app.models.user import User

logger = get_logger(__name__)

_ENGINE_WS_BASE = settings.engine_api_url.replace("http://", "ws://").replace(
    "https://", "wss://"
)


async def _authenticate_ws(token: str | None) -> User | None:
    """Validate a JWT token and return the corresponding User, or None."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str | None = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()


async def ws_simulation_proxy(websocket: WebSocket, simulation_id: str) -> None:
    """Authenticate the client and proxy the Engine WebSocket stream.

    The JWT must be supplied as the ``token`` query parameter:
        ws://<backend>/api/v1/engine/simulations/<id>/ws?token=<jwt>
    """
    token: str | None = websocket.query_params.get("token")
    user = await _authenticate_ws(token)

    if user is None:
        logger.warning(
            "WebSocket auth failed for simulation_id=%s — closing with 4001",
            simulation_id,
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    engine_ws_url = f"{_ENGINE_WS_BASE}/simulations/{simulation_id}/ws"
    logger.info(
        "User %s opening WS proxy for simulation_id=%s → %s",
        user.username,
        simulation_id,
        engine_ws_url,
    )

    await websocket.accept()

    try:
        async with httpx.AsyncClient() as http_client:
            async with http_client.stream("GET", engine_ws_url) as _:
                # httpx does not support WebSocket natively; use websockets lib.
                pass
    except Exception:
        pass

    # Use the `websockets` library (available via httpx[http2] or standalone).
    try:
        import websockets  # type: ignore[import]
    except ImportError:
        logger.error(
            "Package 'websockets' is not installed. "
            "Add it to requirements.txt to enable WS proxy."
        )
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    try:
        async with websockets.connect(engine_ws_url) as engine_ws:

            async def _client_to_engine() -> None:
                """Forward messages from the frontend client to the Engine."""
                try:
                    while True:
                        data = await websocket.receive_text()
                        await engine_ws.send(data)
                except (WebSocketDisconnect, Exception):
                    pass

            async def _engine_to_client() -> None:
                """Forward messages from the Engine to the frontend client."""
                try:
                    async for message in engine_ws:
                        await websocket.send_text(
                            message if isinstance(message, str) else message.decode()
                        )
                except (WebSocketDisconnect, Exception):
                    pass

            await asyncio.gather(
                _client_to_engine(),
                _engine_to_client(),
                return_exceptions=True,
            )

    except websockets.exceptions.ConnectionClosedError as exc:
        logger.info(
            "Engine WS closed for simulation_id=%s: %s", simulation_id, exc
        )
    except Exception as exc:
        logger.error(
            "WS proxy error for simulation_id=%s: %s", simulation_id, exc
        )
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info(
            "WS proxy closed for simulation_id=%s user=%s",
            simulation_id,
            user.username,
        )
