import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.simulation import SimulationResult
from app.models.user import User
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/twin", tags=["Playback de simulación WebSocket"])

@router.websocket("/ws/{simulation_id}")
async def digital_twin_websocket(websocket: WebSocket, simulation_id: str):
    """
    Reproduce resultados persistidos; no es telemetría IoT ni ejecución en tiempo real.
    Requiere un access token en el parámetro de consulta ``token``.
    """
    token = websocket.query_params.get("token")
    payload = decode_access_token(token) if token else None
    user_id = payload.get("sub") if payload else None
    if not user_id:
        await websocket.close(code=1008, reason="Authentication required")
        return
    async with AsyncSessionLocal() as auth_session:
        user = await auth_session.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if not user:
        await websocket.close(code=1008, reason="Authentication required")
        return
    await websocket.accept()
    logger.info("Cliente conectado al playback WS para simulación %s", simulation_id)

    # Cargar los resultados de la simulación desde la base de datos
    results = []
    async with AsyncSessionLocal() as session:
        stmt = (
            select(SimulationResult)
            .where(SimulationResult.simulation_run_id == simulation_id)
            .order_by(SimulationResult.day_index)
        )
        res = await session.execute(stmt)
        results = res.scalars().all()

    if not results:
        await websocket.send_text(json.dumps({
            "type": "ERROR",
            "message": f"No se encontraron datos para la simulación {simulation_id}"
        }))
        await websocket.close()
        return

    is_playing = True
    current_index = 0
    tick_delay_seconds = 0.5  # Velocidad por defecto (1 día cada 500ms)

    async def receive_commands():
        nonlocal is_playing, tick_delay_seconds, current_index
        try:
            while True:
                data_text = await websocket.receive_text()
                data = json.loads(data_text)
                cmd = data.get("command")

                if cmd == "play":
                    is_playing = True
                    speed = data.get("speed", 1.0)
                    tick_delay_seconds = max(0.05, 0.5 / speed)
                elif cmd == "pause":
                    is_playing = False
                elif cmd == "step":
                    is_playing = False
                    current_index = min(len(results) - 1, current_index + 1)
                elif cmd == "seek":
                    target_day = data.get("day", 1)
                    current_index = max(0, min(len(results) - 1, target_day - 1))
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning(f"Error procesando comando WS: {e}")

    # Tarea en segundo plano para escuchar comandos del cliente
    recv_task = asyncio.create_task(receive_commands())

    try:
        while True:
            if is_playing and current_index < len(results):
                item = results[current_index]
                payload = {
                    "type": "SIMULATION_PLAYBACK_TICK",
                    "evidence_type": "DEMO",
                    "day_index": item.day_index,
                    "date": item.date_str,
                    "weather": {
                        "precip_mm": item.precip_mm,
                        "temp_c": item.temp_c,
                        "solar_rad_mj": item.solar_rad_mj
                    },
                    "micro_plant": {
                        "transpiration_mm": item.plant_transpiration_mm,
                        "root_water_uptake_mm": item.root_water_uptake_mm,
                        "cwsi_stress_index": item.cwsi_stress_index,
                        "sap_flow_velocity_cmh": item.sap_flow_velocity_cmh
                    },
                    "meso_soil": {
                        "soil_moisture_vol": item.soil_moisture_vol,
                        "soil_water_depth_mm": item.soil_water_depth_mm,
                        "percolation_mm": item.percolation_mm
                    },
                    "macro_watershed": {
                        "surface_runoff_mm": item.surface_runoff_mm,
                        "streamflow_m3s": item.streamflow_m3s,
                        "actual_et_mm": item.actual_et_mm
                    }
                }
                await websocket.send_text(json.dumps(payload))
                current_index = (current_index + 1) % len(results)

            await asyncio.sleep(tick_delay_seconds)

    except WebSocketDisconnect:
        logger.info(f"Cliente desconectado de WS para simulación {simulation_id}")
    finally:
        recv_task.cancel()
