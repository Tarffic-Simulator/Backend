import httpx
from fastapi import HTTPException
from app.core.config import settings

async def fetch_simulation_data(simulation_id: str) -> dict:
    url = f"{settings.engine_api_url}/simulations/{simulation_id}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error al contactar al Engine")
        return response.json()