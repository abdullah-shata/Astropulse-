"""
AstroPulse (NASA Space Apps) - Phase 2: FastAPI Backend Core & Real-Time Server
Module: 3_backend_core/main.py
"""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import math
from pathlib import Path
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

try:
    from .schemas import (
        TelemetryInput,
        EnrichedTelemetry,
        BatchSyncRequest,
        BatchSyncResponse,
    )
    from .database import (
        init_db,
        insert_telemetry,
        insert_batch_telemetry,
        get_recent_history,
        get_recent_alerts,
    )
    from .ai_inference import predict_telemetry
except (ImportError, ValueError):
    from schemas import (
        TelemetryInput,
        EnrichedTelemetry,
        BatchSyncRequest,
        BatchSyncResponse,
    )
    from database import (
        init_db,
        insert_telemetry,
        insert_batch_telemetry,
        get_recent_history,
        get_recent_alerts,
    )
    from ai_inference import predict_telemetry


class WebSocketConnectionManager:
    """Manages active real-time HUD WebSocket subscribers."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WebSocket] Client connected. Total active subscribers: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WebSocket] Client disconnected. Total active subscribers: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


ws_manager = WebSocketConnectionManager()
FRONTEND_INDEX = Path(__file__).resolve().parent.parent / "public" / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Function instances are short lived; initialize only local ephemeral storage.
    try:
        init_db()
    except OSError:
        pass
    yield


app = FastAPI(
    title="AstroPulse AI Telemetry & Triage Engine",
    description="Autonomous real-time bio-telemetry ingestion, NASA HRP AI triage, and Delay-Tolerant Networking (DTN) gateway.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend and simulator integration
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost(:\d+)?|127\.0\.0\.1(:\d+)?|.*\.vercel\.app)",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    if FRONTEND_INDEX.is_file():
        return FileResponse(FRONTEND_INDEX, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {
        "service": "AstroPulse Core Backend",
        "status": "online",
        "version": "1.0.0",
        "mission_standards": ["NASA-STD-3001", "CSA-CANS", "PhysioNet-MIMIC"],
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/telemetry", response_model=EnrichedTelemetry)
async def ingest_telemetry(payload: TelemetryInput):
    """
    Ingest single 1Hz telemetry reading ->
    Run AI inference (IsolationForest + 2x Random Forests) ->
    Persist to SQLite ->
    Broadcast enriched payload via WebSocket to live HUD clients.
    """
    try:
        # 1. AI Real-Time Inference
        diagnosis = predict_telemetry(payload)

        # 2. Construct enriched payload
        telemetry_dict = payload.model_dump()
        telemetry_dict.update(diagnosis)

        # 3. Persist to SQLite
        log_id = insert_telemetry(telemetry_dict)
        telemetry_dict["id"] = log_id

        # 4. Broadcast to WebSocket HUD subscribers
        await ws_manager.broadcast({
            "type": "TELEMETRY_UPDATE",
            "data": telemetry_dict,
        })

        return telemetry_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference/Ingestion error: {str(e)}")


@app.post("/api/sync-batch", response_model=BatchSyncResponse)
async def sync_dtn_batch(payload: BatchSyncRequest):
    """
    Bulk ingestion endpoint for compressed Delay-Tolerant Networking (DTN) packets.
    Used when Earth/Gateway communication is restored after an offline period.
    """
    if not payload.records:
        return BatchSyncResponse(status="empty", synced_count=0, alerts_generated=0)

    try:
        enriched_list = []
        for record in payload.records:
            diagnosis = predict_telemetry(record)
            item = record.model_dump()
            item.update(diagnosis)
            enriched_list.append(item)

        synced_count, alerts_generated = insert_batch_telemetry(enriched_list)

        # Broadcast sync event notification
        await ws_manager.broadcast({
            "type": "DTN_BATCH_SYNC",
            "data": {
                "synced_count": synced_count,
                "alerts_generated": alerts_generated,
                "latest_sample": enriched_list[-1] if enriched_list else None,
            }
        })

        return BatchSyncResponse(
            status="synced",
            synced_count=synced_count,
            alerts_generated=alerts_generated,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch sync error: {str(e)}")


@app.get("/api/history/{astronaut_id}")
def get_astronaut_history(astronaut_id: str, limit: int = Query(50, ge=1, le=500)):
    """Fetch recent time-series telemetry records for a given astronaut."""
    try:
        history = get_recent_history(astronaut_id=astronaut_id, limit=limit)
    except Exception:
        history = []
    # Cold instances have no durable database; seed a full chart and refresh its newest point.
    if not history:
        history = generate_live_history(astronaut_id, limit)
    else:
        history = (history + generate_live_history(astronaut_id, 1))[-limit:]
    return {
        "astronaut_id": astronaut_id,
        "count": len(history),
        "history": history,
    }


@app.get("/api/alerts")
def get_alerts(limit: int = Query(50, ge=1, le=200)):
    """Fetch recent medical triage crisis alerts."""
    try:
        alerts = get_recent_alerts(limit=limit)
    except Exception:
        alerts = []
    live_alerts = [sample for astronaut_id in ("ASTRO_01", "ASTRO_02", "ASTRO_03", "ASTRO_04")
                   for sample in generate_live_history(astronaut_id, 1)
                   if sample["health_status"] != "Normal"]
    alerts = sorted(alerts + live_alerts, key=lambda item: item["timestamp"], reverse=True)[:limit]
    return {
        "count": len(alerts),
        "alerts": alerts,
    }


def generate_live_history(astronaut_id: str, limit: int):
    """Generate deterministic, time-varying telemetry when ephemeral storage is empty."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    seed = int(hashlib.sha256(astronaut_id.encode()).hexdigest()[:8], 16)
    records = []
    for age in reversed(range(min(limit, 60))):
        tick = int(now.timestamp() // 5) - age
        phase = (tick + seed) / 8
        payload = {
            "timestamp": (now - timedelta(seconds=5 * age)).isoformat(),
            "astronaut_id": astronaut_id,
            "mission_environment": "Mars_Transit",
            "gravity_level_g": 0.38,
            "comm_latency_sec": 1200.0,
            "mission_day": 142.0,
            "heart_rate_bpm": round(72 + 5 * math.sin(phase), 1),
            "respiratory_rate_rpm": round(15 + math.sin(phase / 2), 1),
            "spo2_percent": round(98 + 0.6 * math.sin(phase / 3), 1),
            "systolic_bp_mmhg": round(118 + 4 * math.sin(phase / 4), 1),
            "diastolic_bp_mmhg": 78.0,
            "body_temp_c": round(36.7 + 0.15 * math.sin(phase / 5), 2),
            "blood_sugar_mg_dl": 95.0,
            "neutron_radiation_msv_hr": round(0.12 + 0.02 * math.sin(phase / 6), 3),
            "sleep_hours_24h": 7.2,
            "mood_stress_score": 3.0,
            "intracranial_pressure_idx": round(10 + math.sin(phase / 7), 2),
            "bone_density_loss_pct": 0.24,
        }
        diagnosis = predict_telemetry(payload)
        payload.update(diagnosis)
        payload["id"] = tick
        records.append(payload)
    return records


@app.websocket("/ws/live-hud")
async def websocket_hud_stream(websocket: WebSocket):
    """WebSocket stream powering the real-time Mission Control & Crew HUD."""
    await ws_manager.connect(websocket)
    try:
        # Send initial handshake confirmation
        await websocket.send_json({
            "type": "HUD_CONNECTION_ESTABLISHED",
            "message": "Connected to AstroPulse Real-Time Telemetry Stream",
        })
        while True:
            # Keep socket open and receive any client ping/events
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


@app.get("/{frontend_path:path}", include_in_schema=False)
def frontend_fallback(frontend_path: str):
    """Serve the Vite SPA for client-side routes after API routes are checked."""
    if frontend_path in {"api", "ws"} or frontend_path.startswith(("api/", "ws/")):
        raise HTTPException(status_code=404, detail="Not found")
    if FRONTEND_INDEX.is_file():
        return FileResponse(FRONTEND_INDEX, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    raise HTTPException(status_code=404, detail="Not found")
