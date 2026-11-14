"""
AstroPulse (NASA Space Apps) - Phase 2: Backend Core Schemas
Module: 3_backend_core/schemas.py
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TelemetryInput(BaseModel):
    timestamp: Optional[str] = Field(None, description="ISO timestamp of telemetry frame")
    astronaut_id: str = Field(..., description="Crew identifier (e.g. ASTRO_01)")
    mission_environment: str = Field(..., description="Mission domain (Artemis_DeepSpace, Mars_Transit, Lunar_Base, EVA_Spacewalk)")
    
    # 15 Numeric Physiological & Environmental Features
    gravity_level_g: float = Field(..., description="Local gravitational force in g")
    comm_latency_sec: float = Field(..., description="Communication delay to Earth in seconds")
    mission_day: float = Field(..., description="Mission elapsed day count")
    heart_rate_bpm: float = Field(..., description="Heart rate in beats per minute")
    respiratory_rate_rpm: float = Field(..., description="Respiratory rate in breaths per minute")
    spo2_percent: float = Field(..., description="Blood oxygen saturation percentage")
    systolic_bp_mmhg: float = Field(..., description="Systolic blood pressure in mmHg")
    diastolic_bp_mmhg: float = Field(..., description="Diastolic blood pressure in mmHg")
    body_temp_c: float = Field(..., description="Core body temperature in Celsius")
    blood_sugar_mg_dl: float = Field(..., description="Blood glucose level in mg/dL")
    neutron_radiation_msv_hr: float = Field(..., description="Neutron radiation dosage in mSv/hr")
    sleep_hours_24h: float = Field(..., description="Cumulative sleep in last 24h")
    mood_stress_score: float = Field(..., description="Psychological stress index (1-10)")
    intracranial_pressure_idx: float = Field(..., description="Non-invasive intracranial pressure index")
    bone_density_loss_pct: float = Field(..., description="Estimated bone mineral density loss %")


class AIDiagnosisResult(BaseModel):
    is_anomaly: bool = Field(..., description="Flag if anomaly detected by IsolationForest or risk classifiers")
    health_status: str = Field(..., description="Normal, Warning, or Critical")
    detected_nasa_risk: str = Field(..., description="Identified NASA Human Research Program risk condition")
    confidence: float = Field(..., description="Model classification posterior confidence (0.0 to 1.0)")
    triage_protocol_action: str = Field(..., description="NASA emergency clinical countermeasure instructions")


class EnrichedTelemetry(TelemetryInput, AIDiagnosisResult):
    id: Optional[int] = Field(None, description="Database record ID")


class BatchSyncRequest(BaseModel):
    records: List[TelemetryInput] = Field(..., description="Array of queued DTN telemetry payloads")


class BatchSyncResponse(BaseModel):
    status: str
    synced_count: int
    alerts_generated: int


class MedicalAlert(BaseModel):
    id: int
    timestamp: str
    astronaut_id: str
    health_status: str
    detected_nasa_risk: str
    triage_protocol_action: str
    heart_rate_bpm: float
    spo2_percent: float
    neutron_radiation_msv_hr: float
    intracranial_pressure_idx: float
