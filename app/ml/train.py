"""
OmniShield AI — Training Pipeline
Trains Random Forest classifier on uploaded CSV datasets.
Strictly prevents data leakage: preprocessing is fit ONLY on training data.
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from .preprocessing import (
    build_preprocessing_pipeline,
    encode_labels,
    identify_feature_types,
    validate_and_clean_dataset,
)
from .evaluate import evaluate_model

logger = logging.getLogger(__name__)


def train_model(
    csv_path: str,
    target_column: str,
    model_folder: str,
    metadata_folder: str,
    n_estimators: int = 100,
    test_size: float = 0.2,
    random_state: int = 42,
    min_samples_per_class: int = 5,
) -> dict[str, Any]:
    """
    Full training pipeline:
      CSV → validate → split → fit preprocessing on train → train RF → evaluate → save.

    Returns a result dict with paths and metrics.
    Raises ValueError/RuntimeError on failure.
    """
    logger.info("Starting training pipeline on: %s", csv_path)

    # ── 1. Load CSV ─────────────────────────────────────────────────────────
    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except Exception as exc:
        raise ValueError(f"Failed to read CSV file: {exc}") from exc

    # ── 2. Validate + clean ─────────────────────────────────────────────────
    df, warnings = validate_and_clean_dataset(df, target_column, min_samples_per_class)
    logger.info("Cleaned dataset: %d rows, %d cols. Warnings: %s", len(df), len(df.columns), warnings)

    # ── 3. Identify feature types ────────────────────────────────────────────
    numerical_cols, categorical_cols = identify_feature_types(df, target_column)
    feature_names = numerical_cols + categorical_cols

    if not feature_names:
        raise ValueError("No valid feature columns found after removing the target column.")

    X = df[feature_names]
    y = df[target_column]

    # ── 4. Encode labels ────────────────────────────────────────────────────
    y_encoded, label_encoder = encode_labels(y)

    # ── 5. Train/test split (stratified) ────────────────────────────────────
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y_encoded,
            test_size=test_size,
            random_state=random_state,
            stratify=y_encoded,
        )
    except ValueError:
        # Fall back to non-stratified if stratification fails (very skewed classes)
        logger.warning("Stratified split failed, falling back to random split.")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=test_size, random_state=random_state
        )

    logger.info("Split — train: %d, test: %d", len(X_train), len(X_test))

    # ── 6. Build + fit preprocessing (ONLY on training data) ─────────────────
    preprocessor = build_preprocessing_pipeline(numerical_cols, categorical_cols)
    X_train_transformed = preprocessor.fit_transform(X_train)
    X_test_transformed = preprocessor.transform(X_test)

    # Get output feature names after one-hot encoding
    output_feature_names = _get_output_feature_names(preprocessor, numerical_cols, categorical_cols)

    # ── 7. Train Random Forest ───────────────────────────────────────────────
    rf = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state,
        n_jobs=-1,
    )
    rf.fit(X_train_transformed, y_train)
    logger.info("Random Forest trained with %d estimators.", n_estimators)

    # ── 8. Evaluate ─────────────────────────────────────────────────────────
    metrics = evaluate_model(rf, X_test_transformed, y_test, label_encoder, output_feature_names)

    # ── 9. Save model artifacts ──────────────────────────────────────────────
    version = _generate_version()
    os.makedirs(model_folder, exist_ok=True)
    os.makedirs(metadata_folder, exist_ok=True)

    model_path = os.path.join(model_folder, f"rf_model_{version}.joblib")
    preprocessing_path = os.path.join(model_folder, f"preprocessing_{version}.joblib")
    label_encoder_path = os.path.join(model_folder, f"label_encoder_{version}.joblib")

    joblib.dump(rf, model_path)
    joblib.dump(preprocessor, preprocessing_path)
    joblib.dump(label_encoder, label_encoder_path)

    logger.info("Model saved: %s", model_path)

    return {
        "version": version,
        "model_path": model_path,
        "preprocessing_path": preprocessing_path,
        "label_encoder_path": label_encoder_path,
        "feature_names": feature_names,       # original input feature names
        "output_feature_names": output_feature_names,
        "numerical_cols": numerical_cols,
        "categorical_cols": categorical_cols,
        "target_column": target_column,
        "training_samples": int(len(X_train)),
        "testing_samples": int(len(X_test)),
        "warnings": warnings,
        **metrics,
    }


def _generate_version() -> str:
    """Generate a unique version string based on timestamp + short UUID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:6]
    return f"{ts}_{uid}"


def _get_output_feature_names(
    preprocessor,
    numerical_cols: list[str],
    categorical_cols: list[str],
) -> list[str]:
    """Get the output feature names after ColumnTransformer transformation."""
    names = []
    try:
        for name, transformer, cols in preprocessor.transformers_:
            if name == "numerical":
                names.extend(cols)
            elif name == "categorical":
                ohe = transformer.named_steps.get("onehot")
                if ohe is not None and hasattr(ohe, "get_feature_names_out"):
                    names.extend(ohe.get_feature_names_out(cols).tolist())
                else:
                    names.extend(cols)
    except Exception:
        # Fallback
        names = numerical_cols + categorical_cols
    return names
