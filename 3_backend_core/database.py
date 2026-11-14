"""
AstroPulse (NASA Space Apps) - Phase 2: Lightweight SQLite Database Layer
Module: 3_backend_core/database.py
"""

from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "astropulse.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db():
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                astronaut_id TEXT NOT NULL,
                mission_environment TEXT NOT NULL,
                gravity_level_g REAL NOT NULL,
                comm_latency_sec REAL NOT NULL,
                mission_day REAL NOT NULL,
                heart_rate_bpm REAL NOT NULL,
                respiratory_rate_rpm REAL NOT NULL,
                spo2_percent REAL NOT NULL,
                systolic_bp_mmhg REAL NOT NULL,
                diastolic_bp_mmhg REAL NOT NULL,
                body_temp_c REAL NOT NULL,
                blood_sugar_mg_dl REAL NOT NULL,
                neutron_radiation_msv_hr REAL NOT NULL,
                sleep_hours_24h REAL NOT NULL,
                mood_stress_score REAL NOT NULL,
                intracranial_pressure_idx REAL NOT NULL,
                bone_density_loss_pct REAL NOT NULL,
                is_anomaly INTEGER NOT NULL,
                health_status TEXT NOT NULL,
                detected_nasa_risk TEXT NOT NULL,
                confidence REAL NOT NULL,
                triage_protocol_action TEXT NOT NULL
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS medical_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                astronaut_id TEXT NOT NULL,
                health_status TEXT NOT NULL,
                detected_nasa_risk TEXT NOT NULL,
                triage_protocol_action TEXT NOT NULL,
                heart_rate_bpm REAL NOT NULL,
                spo2_percent REAL NOT NULL,
                neutron_radiation_msv_hr REAL NOT NULL,
                intracranial_pressure_idx REAL NOT NULL
            );
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_astro ON telemetry_logs(astronaut_id, timestamp);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON medical_alerts(timestamp);")
    conn.close()


# Auto-initialize on import so DB tables exist immediately
init_db()


def insert_telemetry(record: Dict[str, Any]) -> int:
    conn = get_connection()
    ts = record.get("timestamp") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    with conn:
        cursor = conn.execute("""
            INSERT INTO telemetry_logs (
                timestamp, astronaut_id, mission_environment,
                gravity_level_g, comm_latency_sec, mission_day,
                heart_rate_bpm, respiratory_rate_rpm, spo2_percent,
                systolic_bp_mmhg, diastolic_bp_mmhg, body_temp_c,
                blood_sugar_mg_dl, neutron_radiation_msv_hr, sleep_hours_24h,
                mood_stress_score, intracranial_pressure_idx, bone_density_loss_pct,
                is_anomaly, health_status, detected_nasa_risk, confidence, triage_protocol_action
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            ts,
            record["astronaut_id"],
            record["mission_environment"],
            float(record["gravity_level_g"]),
            float(record["comm_latency_sec"]),
            float(record["mission_day"]),
            float(record["heart_rate_bpm"]),
            float(record["respiratory_rate_rpm"]),
            float(record["spo2_percent"]),
            float(record["systolic_bp_mmhg"]),
            float(record["diastolic_bp_mmhg"]),
            float(record["body_temp_c"]),
            float(record["blood_sugar_mg_dl"]),
            float(record["neutron_radiation_msv_hr"]),
            float(record["sleep_hours_24h"]),
            float(record["mood_stress_score"]),
            float(record["intracranial_pressure_idx"]),
            float(record["bone_density_loss_pct"]),
            1 if record["is_anomaly"] else 0,
            record["health_status"],
            record["detected_nasa_risk"],
            float(record["confidence"]),
            record["triage_protocol_action"],
        ))
        log_id = cursor.lastrowid

        # Automatically insert into medical_alerts if non-normal health status
        if record["health_status"] != "Normal":
            conn.execute("""
                INSERT INTO medical_alerts (
                    timestamp, astronaut_id, health_status, detected_nasa_risk,
                    triage_protocol_action, heart_rate_bpm, spo2_percent,
                    neutron_radiation_msv_hr, intracranial_pressure_idx
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ts,
                record["astronaut_id"],
                record["health_status"],
                record["detected_nasa_risk"],
                record["triage_protocol_action"],
                float(record["heart_rate_bpm"]),
                float(record["spo2_percent"]),
                float(record["neutron_radiation_msv_hr"]),
                float(record["intracranial_pressure_idx"]),
            ))
            
    conn.close()
    return log_id


def insert_batch_telemetry(records: List[Dict[str, Any]]) -> tuple[int, int]:
    conn = get_connection()
    synced_count = 0
    alerts_count = 0

    with conn:
        for record in records:
            ts = record.get("timestamp") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT INTO telemetry_logs (
                    timestamp, astronaut_id, mission_environment,
                    gravity_level_g, comm_latency_sec, mission_day,
                    heart_rate_bpm, respiratory_rate_rpm, spo2_percent,
                    systolic_bp_mmhg, diastolic_bp_mmhg, body_temp_c,
                    blood_sugar_mg_dl, neutron_radiation_msv_hr, sleep_hours_24h,
                    mood_stress_score, intracranial_pressure_idx, bone_density_loss_pct,
                    is_anomaly, health_status, detected_nasa_risk, confidence, triage_protocol_action
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                ts,
                record["astronaut_id"],
                record["mission_environment"],
                float(record["gravity_level_g"]),
                float(record["comm_latency_sec"]),
                float(record["mission_day"]),
                float(record["heart_rate_bpm"]),
                float(record["respiratory_rate_rpm"]),
                float(record["spo2_percent"]),
                float(record["systolic_bp_mmhg"]),
                float(record["diastolic_bp_mmhg"]),
                float(record["body_temp_c"]),
                float(record["blood_sugar_mg_dl"]),
                float(record["neutron_radiation_msv_hr"]),
                float(record["sleep_hours_24h"]),
                float(record["mood_stress_score"]),
                float(record["intracranial_pressure_idx"]),
                float(record["bone_density_loss_pct"]),
                1 if record["is_anomaly"] else 0,
                record["health_status"],
                record["detected_nasa_risk"],
                float(record["confidence"]),
                record["triage_protocol_action"],
            ))
            synced_count += 1

            if record["health_status"] != "Normal":
                conn.execute("""
                    INSERT INTO medical_alerts (
                        timestamp, astronaut_id, health_status, detected_nasa_risk,
                        triage_protocol_action, heart_rate_bpm, spo2_percent,
                        neutron_radiation_msv_hr, intracranial_pressure_idx
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ts,
                    record["astronaut_id"],
                    record["health_status"],
                    record["detected_nasa_risk"],
                    record["triage_protocol_action"],
                    float(record["heart_rate_bpm"]),
                    float(record["spo2_percent"]),
                    float(record["neutron_radiation_msv_hr"]),
                    float(record["intracranial_pressure_idx"]),
                ))
                alerts_count += 1

    conn.close()
    return synced_count, alerts_count


def get_recent_history(astronaut_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.execute("""
        SELECT * FROM telemetry_logs
        WHERE astronaut_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (astronaut_id, limit))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    rows.reverse()  # Return in chronological order (oldest to newest)
    return rows


def get_recent_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.execute("""
        SELECT * FROM medical_alerts
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
