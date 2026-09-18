"""
OmniShield AI — Preprocessing Pipeline
Handles numerical + categorical features with no data leakage.
The preprocessing pipeline is always fit ONLY on training data.
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

logger = logging.getLogger(__name__)


def build_preprocessing_pipeline(
    numerical_cols: list[str],
    categorical_cols: list[str],
) -> ColumnTransformer:
    """
    Build a ColumnTransformer that handles:
    - Numerical features: median imputation → standard scaling
    - Categorical features: constant imputation → one-hot encoding
    """
    transformers = []

    if numerical_cols:
        numerical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )
        transformers.append(("numerical", numerical_pipeline, numerical_cols))

    if categorical_cols:
        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
                (
                    "onehot",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        sparse_output=False,
                    ),
                ),
            ]
        )
        transformers.append(("categorical", categorical_pipeline, categorical_cols))

    if not transformers:
        raise ValueError("No features found to build preprocessing pipeline.")

    return ColumnTransformer(transformers=transformers, remainder="drop")


def identify_feature_types(
    df: pd.DataFrame,
    target_col: str,
) -> tuple[list[str], list[str]]:
    """
    Identify numerical and categorical feature columns,
    excluding the target column.
    Returns (numerical_cols, categorical_cols).
    """
    feature_df = df.drop(columns=[target_col], errors="ignore")

    numerical_cols = feature_df.select_dtypes(
        include=["int64", "float64", "int32", "float32"]
    ).columns.tolist()

    categorical_cols = feature_df.select_dtypes(
        include=["object", "category", "bool"]
    ).columns.tolist()

    logger.info(
        "Feature types — numerical: %d, categorical: %d",
        len(numerical_cols),
        len(categorical_cols),
    )
    return numerical_cols, categorical_cols


def encode_labels(y: pd.Series) -> tuple[np.ndarray, LabelEncoder]:
    """Encode string class labels to integers. Returns (encoded_array, fitted_encoder)."""
    le = LabelEncoder()
    y_encoded = le.fit_transform(y.astype(str))
    return y_encoded, le


def validate_and_clean_dataset(
    df: pd.DataFrame,
    target_col: str,
    min_samples_per_class: int = 2,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Validate and clean the dataset.
    Returns (cleaned_df, list_of_warnings).
    Raises ValueError on fatal issues.
    """
    warnings = []

    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset.")

    # Drop rows where target is null
    before = len(df)
    df = df.dropna(subset=[target_col])
    dropped = before - len(df)
    if dropped > 0:
        warnings.append(f"Dropped {dropped} rows with missing target values.")

    if len(df) < 2:
        raise ValueError(
            f"Dataset has only {len(df)} usable rows after cleaning. Need at least 2."
        )

    # Check class distribution
    class_counts = df[target_col].value_counts()
    small_classes = class_counts[class_counts < min_samples_per_class]
    if not small_classes.empty:
        for cls, count in small_classes.items():
            warnings.append(
                f"Class '{cls}' has only {count} samples (minimum: {min_samples_per_class}). "
                "It may be excluded from training."
            )
        # Remove under-represented classes
        valid_classes = class_counts[class_counts >= min_samples_per_class].index
        df = df[df[target_col].isin(valid_classes)]
        if len(df) < 2:
            raise ValueError(
                "After removing under-represented classes, too few samples remain."
            )

    # Check we have at least 2 classes
    n_classes = df[target_col].nunique()
    if n_classes < 2:
        raise ValueError(
            f"Only {n_classes} class(es) found. Need at least 2 classes for classification."
        )

    # Drop columns that are entirely NaN
    all_nan_cols = [c for c in df.columns if df[c].isna().all()]
    if all_nan_cols:
        df = df.drop(columns=all_nan_cols)
        warnings.append(f"Dropped {len(all_nan_cols)} entirely-empty column(s): {all_nan_cols}")

    # Warn about high-cardinality categorical columns (may cause memory issues)
    for col in df.select_dtypes(include=["object"]).columns:
        if col == target_col:
            continue
        cardinality = df[col].nunique()
        if cardinality > 100:
            warnings.append(
                f"Column '{col}' has high cardinality ({cardinality} unique values). "
                "This may slow training."
            )

    return df, warnings


def prepare_input_for_prediction(
    raw_input: dict,
    feature_names: list[str],
) -> pd.DataFrame:
    """
    Convert raw user input dict to a DataFrame with the correct feature columns.
    Missing features default to NaN (imputer handles them).
    """
    row = {feat: raw_input.get(feat, np.nan) for feat in feature_names}
    df = pd.DataFrame([row])
    return df
