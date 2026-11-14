"""
AstroPulse (NASA Space Apps) - Phase 2: Decoupled AI Inference Engine
Module: 3_backend_core/ai_inference.py
"""

from typing import Any, Dict, Union


class AIInferenceService:
    def predict_telemetry(self, payload: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
        """
        Applies lightweight deterministic triage rules to a telemetry frame.
        Accepts dict or Pydantic TelemetryInput.
        Returns dict with is_anomaly, health_status, detected_nasa_risk, confidence, triage_protocol_action.
        """
        if hasattr(payload, "model_dump"):
            data = payload.model_dump()
        elif hasattr(payload, "dict"):
            data = payload.dict()
        else:
            data = dict(payload)

        risk_pred, status_pred, triage_action = "Healthy_Baseline", "Normal", "Continue routine telemetry monitoring"
        if float(data.get("spo2_percent", 100)) < 90:
            risk_pred, status_pred, triage_action = "Hypoxia", "Critical", "Administer supplemental oxygen and assess suit integrity"
        elif float(data.get("heart_rate_bpm", 70)) > 120 or float(data.get("systolic_bp_mmhg", 120)) > 160:
            risk_pred, status_pred, triage_action = "Cardiovascular_Stress", "Warning", "Increase monitoring and assess cardiovascular workload"
        elif float(data.get("neutron_radiation_msv_hr", 0)) > 0.5:
            risk_pred, status_pred, triage_action = "Radiation_Exposure", "Warning", "Move crew member to shielded area and review exposure"
        is_anomaly = status_pred != "Normal"
        risk_confidence = 0.97 if is_anomaly else 0.94

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
