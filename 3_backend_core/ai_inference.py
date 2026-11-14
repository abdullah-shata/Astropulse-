"""
AstroPulse (NASA Space Apps) - Phase 2: Decoupled AI Inference Engine
Module: 3_backend_core/ai_inference.py
"""

from pathlib import Path
import pickle
from typing import Any, Dict, Union
import numpy as np
import pandas as pd


class AIInferenceService:
    def __init__(self, model_path: Union[str, Path] = None):
        if model_path is None:
            # Look in standard decoupled paths
            base_dir = Path(__file__).resolve().parent
            candidates = [
                base_dir.parent / "1_data_and_ai" / "astropulse_ai_engine.pkl",
                base_dir / "astropulse_ai_engine.pkl",
                base_dir.parent / "astropulse_ai_engine.pkl",
                Path("1_data_and_ai/astropulse_ai_engine.pkl").resolve(),
            ]
            for c in candidates:
                if c.exists():
                    model_path = c
                    break

        if not model_path or not Path(model_path).exists():
            raise FileNotFoundError(
                f"Could not locate serialized model artifact 'astropulse_ai_engine.pkl'. "
                f"Searched: {[str(c) for c in candidates]}"
            )

        print(f"Loading AstroPulse AI Engine from: {model_path}")
        with open(model_path, "rb") as f:
            artifact = pickle.load(f)

        self.iso_forest = artifact["iso_forest"]
        self.risk_classifier = artifact["risk_classifier"]
        self.status_classifier = artifact["status_classifier"]
        self.feature_cols = artifact["feature_cols"]
        self.triage_lookup = artifact["triage_lookup"]
        print(f"AI Engine loaded successfully. Features: {len(self.feature_cols)}, Risks: {len(self.triage_lookup)}")

    def predict_telemetry(self, payload: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
        """
        Runs real-time AI inference on a single telemetry frame.
        Accepts dict or Pydantic TelemetryInput.
        Returns dict with is_anomaly, health_status, detected_nasa_risk, confidence, triage_protocol_action.
        """
        if hasattr(payload, "model_dump"):
            data = payload.model_dump()
        elif hasattr(payload, "dict"):
            data = payload.dict()
        else:
            data = dict(payload)

        # Extract features preserving exact column names to eliminate scikit-learn warnings
        feature_vals = {col: [float(data[col])] for col in self.feature_cols}
        X_df = pd.DataFrame(feature_vals)

        # 1. Unsupervised Novelty / Anomaly Detection
        iso_pred = self.iso_forest.predict(X_df)[0]  # 1 for inlier, -1 for outlier

        # 2. Supervised NASA Risk Classification & Posterior Confidence
        risk_pred = self.risk_classifier.predict(X_df)[0]
        risk_probs = self.risk_classifier.predict_proba(X_df)[0]
        risk_confidence = float(np.max(risk_probs))

        # 3. Supervised Health Triage Status
        status_pred = self.status_classifier.predict(X_df)[0]

        # 4. Synthesize Anomaly Flag
        is_anomaly = bool(iso_pred == -1 or status_pred != "Normal" or risk_pred != "Healthy_Baseline")

        # 5. Map NASA Triage Protocol Action
        triage_action = self.triage_lookup.get(
            risk_pred,
            "Continue routine ARCHeR & Tempus Pro telemetry monitoring"
        )

        return {
            "is_anomaly": is_anomaly,
            "health_status": str(status_pred),
            "detected_nasa_risk": str(risk_pred),
            "confidence": round(risk_confidence, 4),
            "triage_protocol_action": triage_action,
        }


# Global Singleton Instance
_service_instance: Union[AIInferenceService, None] = None


def get_inference_service() -> AIInferenceService:
    global _service_instance
    if _service_instance is None:
        _service_instance = AIInferenceService()
    return _service_instance


def predict_telemetry(payload: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
    service = get_inference_service()
    return service.predict_telemetry(payload)
