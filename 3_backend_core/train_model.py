"""Train and save the AstroPulse inference artifact from the bundled dataset."""

from pathlib import Path
import os
import pickle

for variable in (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "BLAS_NUM_THREADS",
):
    os.environ[variable] = "1"

import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier


ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "astropulse_hybrid_real_dataset.csv"
OUTPUT = Path(__file__).resolve().parent / "astropulse_ai_engine.pkl"

FEATURE_COLS = [
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


def main() -> None:
    if not DATASET.is_file():
        raise FileNotFoundError(f"Telemetry dataset not found: {DATASET}")

    data = pd.read_csv(DATASET)
    missing = [column for column in FEATURE_COLS if column not in data.columns]
    if missing:
        raise ValueError(f"Dataset is missing model features: {missing}")

    features = data[FEATURE_COLS].astype(float)
    iso_forest = IsolationForest(contamination="auto", random_state=42, n_estimators=150)
    iso_forest.fit(features)

    risk_classifier = RandomForestClassifier(
        n_estimators=160,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=1,
    )
    risk_classifier.fit(features, data["detected_nasa_risk"].astype(str))

    status_classifier = RandomForestClassifier(
        n_estimators=160,
        class_weight="balanced_subsample",
        random_state=43,
        n_jobs=1,
    )
    status_classifier.fit(features, data["health_status"].astype(str))

    triage_lookup = (
        data.dropna(subset=["detected_nasa_risk", "triage_protocol_action"])
        .drop_duplicates("detected_nasa_risk")
        .set_index("detected_nasa_risk")["triage_protocol_action"]
        .astype(str)
        .to_dict()
    )

    artifact = {
        "iso_forest": iso_forest,
        "risk_classifier": risk_classifier,
        "status_classifier": status_classifier,
        "feature_cols": FEATURE_COLS,
        "triage_lookup": triage_lookup,
    }
    with OUTPUT.open("wb") as model_file:
        pickle.dump(artifact, model_file, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"Trained AstroPulse inference model from {len(data):,} telemetry rows.")
    print(f"Saved model artifact: {OUTPUT}")


if __name__ == "__main__":
    main()
