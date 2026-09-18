"""
OmniShield AI — Centralised Configuration
All severity thresholds, risk bands and tunable parameters live here.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class BaseConfig:
    # ── Flask ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production-please")
    DEBUG = False
    TESTING = False

    # ── Database ───────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'omnishield.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # ── File Upload ────────────────────────────────────────────────────────
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {"csv"}

    # ── ML / Model Storage ─────────────────────────────────────────────────
    MODEL_FOLDER = str(BASE_DIR / "models" / "trained")
    MODEL_METADATA_FOLDER = str(BASE_DIR / "models" / "metadata")

    # ── Risk Score Bands (0–100, single source of truth) ──────────────────
    RISK_CRITICAL_THRESHOLD = 80
    RISK_HIGH_THRESHOLD = 60
    RISK_MEDIUM_THRESHOLD = 35
    RISK_LOW_THRESHOLD = 10
    # Anything below RISK_LOW_THRESHOLD is INFO

    # ── Severity labels mapped from risk bands ─────────────────────────────
    SEVERITY_CRITICAL = "CRITICAL"
    SEVERITY_HIGH = "HIGH"
    SEVERITY_MEDIUM = "MEDIUM"
    SEVERITY_LOW = "LOW"
    SEVERITY_INFO = "INFO"

    # ── Attack-type base risk contributions ───────────────────────────────
    # Used by RiskService to weight the final risk score.
    ATTACK_TYPE_RISK_MAP = {
        "normal": 0,
        "dos": 75,
        "probe": 45,
        "r2l": 65,
        "u2r": 85,
        "ddos": 80,
        "exploit": 80,
        "backdoor": 90,
        "shellcode": 90,
        "worms": 85,
        "fuzzers": 50,
        "analysis": 40,
        "reconnaissance": 45,
        "generic": 55,
        "unknown": 50,
    }

    # ── Alert Rules ────────────────────────────────────────────────────────
    ALERT_ON_ATTACK = True
    ALERT_RISK_HIGH_THRESHOLD = 60       # Alert when risk >= this
    ALERT_RISK_CRITICAL_THRESHOLD = 80   # Upgrade to CRITICAL when risk >= this
    ALERT_ANOMALY_THRESHOLD = 0.7        # Normalised anomaly score (0–1)
    ALERT_REPEATED_WINDOW_MINUTES = 10   # Window for repeated-suspicious check
    ALERT_REPEATED_COUNT = 3            # How many suspicious events trigger repeat alert

    # ── Security Score ─────────────────────────────────────────────────────
    SECURITY_SCORE_WINDOW_HOURS = 24     # Look-back window for score calculation
    SECURITY_SCORE_MAX_PENALTY = 80     # Maximum deduction from 100

    # ── Training ───────────────────────────────────────────────────────────
    TRAIN_TEST_SPLIT = 0.4              # 60/40 split allows tiny datasets
    RANDOM_STATE = 42
    RF_N_ESTIMATORS = 100
    RF_MAX_DEPTH = None                 # None = unlimited
    MIN_SAMPLES_PER_CLASS = 1          # Minimum samples needed per class


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    UPLOAD_FOLDER = "/tmp/omnishield_test_uploads"
    MODEL_FOLDER = "/tmp/omnishield_test_models"
    MODEL_METADATA_FOLDER = "/tmp/omnishield_test_metadata"


class ProductionConfig(BaseConfig):
    DEBUG = False
    # Expects DATABASE_URL environment variable for PostgreSQL in production


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
