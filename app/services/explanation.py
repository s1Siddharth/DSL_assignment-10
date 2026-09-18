"""
OmniShield AI — Explanation Service
Generates genuine explanations from model evidence.
No random or fabricated explanations.
"""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def generate_explanation(
    prediction: str,
    attack_type: Optional[str],
    confidence: Optional[float],
    risk_score: float,
    severity: str,
    anomaly_score: Optional[float],
    class_probabilities: Optional[dict],
    raw_features: dict,
    model_feature_importance: Optional[list[dict]],
    feature_names: list[str],
) -> dict[str, Any]:
    """
    Generate an explanation dict based on actual model evidence.

    Returns:
        {
            "summary": str,
            "key_factors": [{"factor": str, "detail": str}],
            "class_probabilities": dict or None,
            "top_features": [{"feature": str, "importance": float, "value": any}],
            "anomaly_note": str or None,
        }
    """
    factors = []

    # ── Prediction confidence ────────────────────────────────────────────────
    if confidence is not None:
        pct = round(confidence * 100, 1)
        factors.append({
            "factor": "Model Confidence",
            "detail": f"The model classified this as '{_label(prediction, attack_type)}' with {pct}% confidence.",
        })
    else:
        factors.append({
            "factor": "Model Confidence",
            "detail": "Confidence information is unavailable for this model.",
        })

    # ── Risk score ───────────────────────────────────────────────────────────
    factors.append({
        "factor": "Risk Assessment",
        "detail": f"Computed risk score: {risk_score}/100 — severity classified as {severity}.",
    })

    # ── Attack-type context ──────────────────────────────────────────────────
    if prediction == "attack" and attack_type:
        attack_desc = _attack_description(attack_type)
        factors.append({
            "factor": "Attack Type",
            "detail": f"Detected as '{attack_type.upper()}'. {attack_desc}",
        })

    # ── Anomaly score ────────────────────────────────────────────────────────
    anomaly_note = None
    if anomaly_score is not None:
        if anomaly_score >= 0.7:
            anomaly_note = (
                f"Anomaly detector flagged this event (score: {anomaly_score:.3f}). "
                "The network behaviour deviates significantly from training baselines."
            )
            factors.append({
                "factor": "Anomaly Detection",
                "detail": anomaly_note,
            })
        elif anomaly_score >= 0.4:
            factors.append({
                "factor": "Anomaly Detection",
                "detail": f"Mild anomaly detected (score: {anomaly_score:.3f}). Behaviour is slightly unusual.",
            })

    # ── Class probability breakdown ──────────────────────────────────────────
    if class_probabilities and len(class_probabilities) > 1:
        top = sorted(class_probabilities.items(), key=lambda x: x[1], reverse=True)[:3]
        prob_details = ", ".join(f"{c}: {v*100:.1f}%" for c, v in top)
        factors.append({
            "factor": "Class Probability Breakdown",
            "detail": f"Top probabilities — {prob_details}.",
        })

    # ── Top important features with their actual values ──────────────────────
    top_features = []
    if model_feature_importance:
        for feat_info in model_feature_importance[:10]:
            feat_name = feat_info.get("feature", "")
            importance = feat_info.get("importance", 0.0)
            value = raw_features.get(feat_name, "N/A")
            top_features.append({
                "feature": feat_name,
                "importance": importance,
                "value": value,
            })

    # ── Summary ──────────────────────────────────────────────────────────────
    summary = _build_summary(prediction, attack_type, confidence, risk_score, severity, anomaly_score)

    return {
        "summary": summary,
        "key_factors": factors,
        "class_probabilities": class_probabilities,
        "top_features": top_features,
        "anomaly_note": anomaly_note,
    }


def _label(prediction: str, attack_type: Optional[str]) -> str:
    if prediction == "attack" and attack_type:
        return attack_type.upper()
    return prediction.capitalize()


def _build_summary(
    prediction: str,
    attack_type: Optional[str],
    confidence: Optional[float],
    risk_score: float,
    severity: str,
    anomaly_score: Optional[float],
) -> str:
    if prediction == "normal":
        return (
            f"Network activity classified as NORMAL with risk score {risk_score}/100. "
            "No attack patterns were detected."
        )
    if prediction == "suspicious":
        return (
            f"Network activity flagged as SUSPICIOUS (risk: {risk_score}/100, severity: {severity}). "
            "Patterns do not match known normal behaviour but no specific attack type was identified."
        )
    # attack
    atk = (attack_type or "unknown").upper()
    conf_str = f" ({confidence*100:.1f}% confidence)" if confidence is not None else ""
    return (
        f"ATTACK detected — type: {atk}{conf_str}. "
        f"Risk score: {risk_score}/100, severity: {severity}. "
        "Immediate investigation is recommended."
    )


def _attack_description(attack_type: str) -> str:
    descriptions = {
        "dos": "Denial-of-Service attack — floods resources to disrupt availability.",
        "ddos": "Distributed Denial-of-Service — coordinated flood from multiple sources.",
        "probe": "Reconnaissance/probe — scanning for vulnerabilities or open ports.",
        "r2l": "Remote-to-Local — attacker gains local access from a remote machine.",
        "u2r": "User-to-Root — privilege escalation from normal user to root.",
        "exploit": "Exploit — leveraging a known software vulnerability.",
        "backdoor": "Backdoor — covert channel for persistent unauthorised access.",
        "shellcode": "Shellcode — execution of injected machine code.",
        "worms": "Worm — self-propagating malware spreading across the network.",
        "fuzzers": "Fuzzing — sending malformed input to find vulnerabilities.",
        "analysis": "Analysis attack — traffic inspection or data exfiltration attempt.",
        "reconnaissance": "Reconnaissance — information gathering prior to an attack.",
        "generic": "Generic attack — pattern matched a known attack signature.",
    }
    return descriptions.get(attack_type.lower(), "Attack pattern identified by the trained classifier.")
