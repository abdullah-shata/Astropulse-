"""
AstroPulse (NASA Space Apps) - Phase 3: Real-Time Physiological Telemetry Simulator
Module: 2_telemetry_simulator/simulator.py

Simulates hardware telemetry streams for all 4 astronauts simultaneously at 1Hz.
Features:
- Groups records by astronaut_id preserving physiological time-series continuity.
- Streams 4 JSON payloads (one per astronaut) every 1 second to POST /api/telemetry.
- CLI flag `--crisis-demo`: Jumps directly to offset 590 (10s before degradation at 600).
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
import pandas as pd


def load_dataset() -> pd.DataFrame:
    """Locate and load the verified NASA bio-telemetry dataset."""
    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir.parent / "1_data_and_ai" / "astropulse_hybrid_real_dataset.csv",
        base_dir.parent / "astropulse_hybrid_real_dataset.csv",
        base_dir / "astropulse_hybrid_real_dataset.csv",
        Path("1_data_and_ai/astropulse_hybrid_real_dataset.csv").resolve(),
    ]
    for c in candidates:
        if c.exists():
            print(f"Loaded telemetry dataset from: {c}")
            return pd.read_csv(c)

    raise FileNotFoundError(
        f"Unable to find astropulse_hybrid_real_dataset.csv. Searched: {[str(c) for c in candidates]}"
    )


def send_payload(url: str, payload: dict, timeout: float = 3.0) -> dict:
    """Send JSON payload to backend endpoint via standard HTTP POST."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "AstroPulse-Simulator/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        resp_data = response.read().decode("utf-8")
        return json.loads(resp_data)


def run_simulator(
    target_url: str = "http://127.0.0.1:8000/api/telemetry",
    interval: float = 1.0,
    crisis_demo: bool = False,
    start_index: int = 0,
    loop: bool = True,
    max_steps: int = None,
):
    df = load_dataset()

    # Required payload features
    feature_cols = [
        "gravity_level_g",
        "comm_latency_sec",
        "mission_day",
        "heart_rate_bpm",
        "respiratory_rate_rpm",
        "spo2_percent",
        "systolic_bp_mmhg",
        "diastolic_bp_mmhg",
        "body_temp_c",
        "blood_sugar_mg_dl",
        "neutron_radiation_msv_hr",
        "sleep_hours_24h",
        "mood_stress_score",
        "intracranial_pressure_idx",
        "bone_density_loss_pct",
    ]

    # Group into chronological series per astronaut
    astronaut_groups = {}
    for astro_id in ["ASTRO_01", "ASTRO_02", "ASTRO_03", "ASTRO_04"]:
        sub_df = df[df["astronaut_id"] == astro_id].reset_index(drop=True)
        if len(sub_df) > 0:
            astronaut_groups[astro_id] = sub_df

    total_records = min(len(g) for g in astronaut_groups.values())

    if crisis_demo:
        start_index = 590
        print("\n" + "!" * 70)
        print("🚨 CRISIS DEMO MODE ACTIVATED")
        print("Jumping directly to offset 590 (10s prior to crisis degradation at index 600)")
        print("Judges can observe Normal -> Warning -> Critical transition in 10 seconds.")
        print("!" * 70 + "\n")

    current_idx = start_index % total_records
    step_count = 0

    print("=" * 70)
    print("🛰️ ASTROPULSE 1Hz TELEMETRY SENSOR SIMULATOR")
    print(f"Target Endpoint: {target_url}")
    print(f"Streaming Active Crew: {list(astronaut_groups.keys())}")
    print(f"Starting Index: {current_idx} / {total_records}")
    print(f"Tick Interval: {interval}s")
    print("=" * 70 + "\n")

    try:
        while True:
            step_count += 1
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            print(f"--- [TICK #{step_count:04d} | OFFSET {current_idx:04d} | {now_iso} UTC] ---")

            for astro_id, sub_df in astronaut_groups.items():
                row = sub_df.iloc[current_idx]

                payload = {
                    "timestamp": now_iso,
                    "astronaut_id": astro_id,
                    "mission_environment": str(row["mission_environment"]),
                }
                for f in feature_cols:
                    payload[f] = float(row[f])

                try:
                    result = send_payload(target_url, payload)
                    status = result.get("health_status", "Unknown")
                    risk = result.get("detected_nasa_risk", "Unknown")
                    conf = result.get("confidence", 0.0)

                    # Status badge indicator
                    if status == "Normal":
                        badge = "🟢 NORMAL  "
                    elif status == "Warning":
                        badge = "🟡 WARNING "
                    else:
                        badge = "🔴 CRITICAL"

                    hr = payload["heart_rate_bpm"]
                    spo2 = payload["spo2_percent"]
                    rad = payload["neutron_radiation_msv_hr"]

                    print(
                        f"  {badge} [{astro_id}] HR: {hr:5.1f} | SpO2: {spo2:5.1f}% | "
                        f"Rad: {rad:.4f} mSv | Risk: {risk} ({conf*100:.1f}%)"
                    )

                except urllib.error.URLError as e:
                    print(f"  ⚠️ [{astro_id}] Connection Failed: Backend unreachable at {target_url} ({e.reason})")
                except Exception as e:
                    print(f"  ❌ [{astro_id}] Transmission Error: {e}")

            current_idx += 1
            if current_idx >= total_records:
                if loop:
                    print("\n[LOOP] Reached end of time-series. Looping back to start...\n")
                    current_idx = 0
                else:
                    print("\nSimulator finished streaming dataset.")
                    break

            if max_steps and step_count >= max_steps:
                print(f"\nReached max step limit ({max_steps}). Stopping simulator.")
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nSimulation halted by user (SIGINT).")


def main():
    parser = argparse.ArgumentParser(
        description="AstroPulse Real-Time Telemetry Hardware Simulator (NASA Space Apps 2026)"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://127.0.0.1:8000/api/telemetry",
        help="FastAPI telemetry ingestion endpoint (default: http://127.0.0.1:8000/api/telemetry)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Stream frequency interval in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--crisis-demo",
        action="store_true",
        help="Jump immediately to offset 590 to demonstrate the live crisis transition at 600",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Custom start record offset (default: 0)",
    )
    parser.add_argument(
        "--no-loop",
        action="store_true",
        help="Do not loop when reaching end of dataset",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Stop after N ticks (useful for automated testing)",
    )

    args = parser.parse_args()
    run_simulator(
        target_url=args.url,
        interval=args.interval,
        crisis_demo=args.crisis_demo,
        start_index=args.start_index,
        loop=not args.no_loop,
        max_steps=args.max_steps,
    )


if __name__ == "__main__":
    main()
