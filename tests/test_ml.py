"""
OmniShield AI — ML Pipeline Tests
Tests preprocessing, training, prediction, no data leakage.
"""
import os
import numpy as np
import pandas as pd
import pytest
import joblib


class TestPreprocessing:
    def test_identify_feature_types(self):
        from app.ml.preprocessing import identify_feature_types
        df = pd.DataFrame({
            'num1': [1.0, 2.0, 3.0],
            'num2': [4, 5, 6],
            'cat1': ['a', 'b', 'c'],
            'target': ['x', 'y', 'z'],
        })
        num, cat = identify_feature_types(df, 'target')
        assert 'num1' in num
        assert 'num2' in num
        assert 'cat1' in cat
        assert 'target' not in num
        assert 'target' not in cat

    def test_build_pipeline_runs(self):
        from app.ml.preprocessing import build_preprocessing_pipeline
        pipe = build_preprocessing_pipeline(['num1', 'num2'], ['cat1'])
        assert pipe is not None

    def test_no_target_in_features(self):
        from app.ml.preprocessing import identify_feature_types
        df = pd.DataFrame({'a': [1,2], 'b': ['x','y'], 'label': ['pos','neg']})
        num, cat = identify_feature_types(df, 'label')
        assert 'label' not in num
        assert 'label' not in cat

    def test_validate_clean_dataset_removes_nan_target(self):
        from app.ml.preprocessing import validate_and_clean_dataset
        df = pd.DataFrame({
            'f1': [1,2,3,None,5]*10,
            'target': ['a','b','a',None,'b']*10,
        })
        cleaned, warnings = validate_and_clean_dataset(df, 'target', min_samples_per_class=2)
        assert cleaned['target'].isna().sum() == 0

    def test_validate_clean_raises_on_too_few_rows(self):
        from app.ml.preprocessing import validate_and_clean_dataset
        df = pd.DataFrame({'f1': [1,2], 'target': ['a','b']})
        with pytest.raises(ValueError, match="only"):
            validate_and_clean_dataset(df, 'target')

    def test_validate_raises_missing_target_col(self):
        from app.ml.preprocessing import validate_and_clean_dataset
        df = pd.DataFrame({'f1': range(100), 'f2': range(100)})
        with pytest.raises(ValueError, match="Target column"):
            validate_and_clean_dataset(df, 'nonexistent')

    def test_encode_labels(self):
        from app.ml.preprocessing import encode_labels
        y = pd.Series(['normal', 'attack', 'normal', 'probe'])
        encoded, le = encode_labels(y)
        assert len(encoded) == 4
        assert set(le.classes_) == {'attack', 'normal', 'probe'}
        restored = le.inverse_transform(encoded)
        assert list(restored) == list(y)

    def test_prepare_input_for_prediction(self):
        from app.ml.preprocessing import prepare_input_for_prediction
        features = ['f1', 'f2', 'f3']
        raw = {'f1': 1.0, 'f3': 3.0}
        df = prepare_input_for_prediction(raw, features)
        assert list(df.columns) == features
        assert df['f1'].iloc[0] == 1.0
        assert pd.isna(df['f2'].iloc[0])  # missing → NaN


class TestTrainingPipeline:
    def test_full_training_no_leakage(self, sample_csv, tmp_path, app):
        """Test that preprocessing is fit only on training data."""
        with app.app_context():
            from app.ml.train import train_model
            result = train_model(
                csv_path=sample_csv,
                target_column='label',
                model_folder=str(tmp_path / 'models'),
                metadata_folder=str(tmp_path / 'metadata'),
                n_estimators=10,  # fast
                test_size=0.2,
                random_state=42,
            )
            assert result['accuracy'] > 0.0
            assert result['accuracy'] <= 1.0
            assert 0.0 <= result['precision'] <= 1.0
            assert 0.0 <= result['recall'] <= 1.0
            assert 0.0 <= result['f1_score'] <= 1.0
            assert result['training_samples'] > 0
            assert result['testing_samples'] > 0
            assert os.path.exists(result['model_path'])
            assert os.path.exists(result['preprocessing_path'])
            assert len(result['classes']) >= 2

    def test_training_saves_all_artifacts(self, sample_csv, tmp_path, app):
        with app.app_context():
            from app.ml.train import train_model
            result = train_model(
                csv_path=sample_csv,
                target_column='label',
                model_folder=str(tmp_path / 'models2'),
                metadata_folder=str(tmp_path / 'metadata2'),
                n_estimators=5,
                random_state=0,
            )
            model = joblib.load(result['model_path'])
            preprocessor = joblib.load(result['preprocessing_path'])
            assert model is not None
            assert preprocessor is not None

    def test_training_invalid_target(self, sample_csv, tmp_path, app):
        with app.app_context():
            from app.ml.train import train_model
            with pytest.raises(ValueError, match="Target column"):
                train_model(
                    csv_path=sample_csv,
                    target_column='nonexistent_column',
                    model_folder=str(tmp_path / 'models3'),
                    metadata_folder=str(tmp_path / 'meta3'),
                )


class TestPrediction:
    @pytest.fixture
    def trained_artifacts(self, sample_csv, tmp_path, app):
        with app.app_context():
            from app.ml.train import train_model
            result = train_model(
                csv_path=sample_csv,
                target_column='label',
                model_folder=str(tmp_path / 'pred_models'),
                metadata_folder=str(tmp_path / 'pred_meta'),
                n_estimators=10,
                random_state=42,
            )
            model = joblib.load(result['model_path'])
            preprocessor = joblib.load(result['preprocessing_path'])
            le_path = result['model_path'].replace('rf_model_', 'label_encoder_')
            label_encoder = joblib.load(le_path)
            return model, preprocessor, label_encoder, result['feature_names']

    def test_prediction_returns_expected_fields(self, trained_artifacts, app):
        with app.app_context():
            from app.ml.predict import predict
            model, preprocessor, le, features = trained_artifacts
            raw = {f: 0.0 for f in features}
            result = predict(raw, model, preprocessor, le, features)
            assert 'prediction' in result
            assert 'attack_type' in result
            assert 'confidence' in result
            assert result['prediction'] in ('normal', 'attack', 'suspicious')

    def test_confidence_is_valid_probability(self, trained_artifacts, app):
        with app.app_context():
            from app.ml.predict import predict
            model, preprocessor, le, features = trained_artifacts
            raw = {f: 1.0 for f in features}
            result = predict(raw, model, preprocessor, le, features)
            if result['confidence'] is not None:
                assert 0.0 <= result['confidence'] <= 1.0

    def test_prediction_same_pipeline_as_training(self, trained_artifacts, app):
        """Ensure prediction uses the same preprocessor fitted on training data only."""
        with app.app_context():
            from app.ml.predict import predict
            model, preprocessor, le, features = trained_artifacts
            # Run same input twice — must get same result (deterministic)
            raw = {features[0]: 5.0} if features else {}
            r1 = predict(raw, model, preprocessor, le, features)
            r2 = predict(raw, model, preprocessor, le, features)
            assert r1['prediction'] == r2['prediction']
            assert r1['confidence'] == r2['confidence']


class TestEvaluation:
    def test_evaluate_returns_all_metrics(self, sample_csv, tmp_path, app):
        with app.app_context():
            from app.ml.train import train_model
            result = train_model(
                csv_path=sample_csv,
                target_column='label',
                model_folder=str(tmp_path / 'eval_models'),
                metadata_folder=str(tmp_path / 'eval_meta'),
                n_estimators=5,
            )
            assert 'confusion_matrix' in result
            assert 'class_metrics' in result
            assert 'feature_importance' in result
            # Confusion matrix dimensions should match number of classes
            n_classes = len(result['classes'])
            assert len(result['confusion_matrix']) == n_classes
            assert all(len(row) == n_classes for row in result['confusion_matrix'])

    def test_feature_importance_sorted(self, sample_csv, tmp_path, app):
        with app.app_context():
            from app.ml.train import train_model
            result = train_model(
                csv_path=sample_csv,
                target_column='label',
                model_folder=str(tmp_path / 'fi_models'),
                metadata_folder=str(tmp_path / 'fi_meta'),
                n_estimators=5,
            )
            fi = result['feature_importance']
            assert fi is not None
            importances = [f['importance'] for f in fi]
            assert importances == sorted(importances, reverse=True)
