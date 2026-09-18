"""
OmniShield AI — Risk Service
Deterministic risk score (0–100) and severity classification.
Single source of truth: thresholds come from app config.
"""
import logging
from typing import Optional

from flask import current_app

logger = logging.getLogger(__name__)


def compute_risk_score(
    prediction: str,
    attack_type: Optional[str],
    confidence: Optional[float],
    anomaly_score: Optional[float],
    raw_features: dict,
) -> float:
    """
    Compute a deterministic risk score in [0, 100].

    Formula:
        base_risk  = attack-type contribution (from config map)
        conf_mult  = confidence modifier (higher confidence → higher risk for attacks)
        anomaly_bonus = anomaly score contribution
        feature_bonus = network-feature heuristics (e.g. port 0, large payload)
    """
    cfg = current_app.config

    # ── Base risk from attack type ───────────────────────────────────────────
    attack_risk_map = cfg.get(
        "ATTACK_TYPE_RISK_MAP",
        {"normal": 0, "unknown": 50},
    )

    if prediction == "normal":
        base = 0.0
    elif prediction == "suspicious":
        base = float(attack_risk_map.get("probe", 45))
    else:
        # attack
        key = (attack_type or "unknown").lower().strip()
        base = float(attack_risk_map.get(key, attack_risk_map.get("unknown", 50)))

    # ── Confidence modifier ──────────────────────────────────────────────────
    if confidence is not None and prediction != "normal":
        # Scale: at confidence=1.0 → full base risk; at confidence=0.5 → 60% of base risk
        conf_factor = 0.6 + 0.4 * confidence
        base = base * conf_factor

    # ── Anomaly bonus ────────────────────────────────────────────────────────
    anomaly_bonus = 0.0
    if anomaly_score is not None:
        anomaly_threshold = cfg.get("ALERT_ANOMALY_THRESHOLD", 0.7)
        if anomaly_score >= anomaly_threshold:
            # Add up to 15 points proportional to how anomalous
            anomaly_bonus = 15.0 * ((anomaly_score - anomaly_threshold) / (1.0 - anomaly_threshold + 1e-9))

    # ── Feature heuristics ───────────────────────────────────────────────────
    feature_bonus = _feature_heuristic_bonus(raw_features)

    risk = base + anomaly_bonus + feature_bonus
    risk = max(0.0, min(100.0, risk))
    return round(risk, 2)


def _feature_heuristic_bonus(features: dict) -> float:
    """Small heuristic bonuses based on raw network feature values."""
    bonus = 0.0
    try:
        # Unusually large payload / bytes
        for key in ("src_bytes", "dst_bytes", "bytes_transferred"):
            val = features.get(key)
            if val is not None:
                try:
                    if float(val) > 1_000_000:
                        bonus += 5.0
                        break
                except (TypeError, ValueError):
                    pass

        # Suspicious port 0 usage
        for key in ("src_port", "dst_port", "sport", "dport"):
            val = features.get(key)
            if val is not None:
                try:
                    if int(float(val)) == 0:
                        bonus += 3.0
                        break
                except (TypeError, ValueError):
                    pass

        # High error rate
        for key in ("serror_rate", "rerror_rate", "same_srv_rate"):
            val = features.get(key)
            if val is not None:
                try:
                    if float(val) > 0.8:
                        bonus += 4.0
                        break
                except (TypeError, ValueError):
                    pass
    except Exception:
        pass
    return min(bonus, 15.0)


def classify_severity(risk_score: float) -> str:
    """Map a risk score to a severity label using config thresholds."""
    cfg = current_app.config
    if risk_score >= cfg.get("RISK_CRITICAL_THRESHOLD", 80):
        return cfg.get("SEVERITY_CRITICAL", "CRITICAL")
    if risk_score >= cfg.get("RISK_HIGH_THRESHOLD", 60):
        return cfg.get("SEVERITY_HIGH", "HIGH")
    if risk_score >= cfg.get("RISK_MEDIUM_THRESHOLD", 35):
        return cfg.get("SEVERITY_MEDIUM", "MEDIUM")
    if risk_score >= cfg.get("RISK_LOW_THRESHOLD", 10):
        return cfg.get("SEVERITY_LOW", "LOW")
    return cfg.get("SEVERITY_INFO", "INFO")
