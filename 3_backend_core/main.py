"""
AstroPulse (NASA Space Apps) - Phase 2: FastAPI Backend Core & Real-Time Server
Module: 3_backend_core/main.py
"""

from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

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
    from .ai_inference import get_inference_service, predict_telemetry
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
    from ai_inference import get_inference_service, predict_telemetry


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite schema & preload AI model
    print("Initializing AstroPulse SQLite persistence layer...")
    init_db()
    print("Preloading AstroPulse AI inference engine...")
    get_inference_service()
    print("AstroPulse Core Backend is fully operational.")
    yield
    print("Shutting down AstroPulse Backend...")


app = FastAPI(
    title="AstroPulse AI Telemetry & Triage Engine",
    description="Autonomous real-time bio-telemetry ingestion, NASA HRP AI triage, and Delay-Tolerant Networking (DTN) gateway.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend and simulator integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
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
    history = get_recent_history(astronaut_id=astronaut_id, limit=limit)
    return {
        "astronaut_id": astronaut_id,
        "count": len(history),
        "history": history,
    }


@app.get("/api/alerts")
def get_alerts(limit: int = Query(50, ge=1, le=200)):
    """Fetch recent medical triage crisis alerts."""
    alerts = get_recent_alerts(limit=limit)
    return {
        "count": len(alerts),
        "alerts": alerts,
    }


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
