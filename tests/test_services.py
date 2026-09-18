"""
OmniShield AI — Service Layer Tests
Tests risk scoring, alert generation, security score determinism.
"""
import pytest


class TestRiskService:
    def test_risk_score_normal_is_zero(self, app):
        with app.app_context():
            from app.services.risk import compute_risk_score
            score = compute_risk_score('normal', None, 1.0, None, {})
            assert score == 0.0

    def test_risk_score_range(self, app):
        with app.app_context():
            from app.services.risk import compute_risk_score
            for pred, attack, conf in [
                ('attack', 'dos', 0.9),
                ('attack', 'u2r', 1.0),
                ('suspicious', None, 0.5),
                ('attack', 'probe', 0.3),
            ]:
                score = compute_risk_score(pred, attack, conf, None, {})
                assert 0.0 <= score <= 100.0, f"Score {score} out of range for {pred}/{attack}"

    def test_risk_score_deterministic(self, app):
        with app.app_context():
            from app.services.risk import compute_risk_score
            s1 = compute_risk_score('attack', 'dos', 0.9, 0.8, {'src_bytes': 500})
            s2 = compute_risk_score('attack', 'dos', 0.9, 0.8, {'src_bytes': 500})
            assert s1 == s2

    def test_attack_higher_risk_than_normal(self, app):
        with app.app_context():
            from app.services.risk import compute_risk_score
            normal_risk = compute_risk_score('normal', None, 0.95, None, {})
            attack_risk = compute_risk_score('attack', 'dos', 0.95, None, {})
            assert attack_risk > normal_risk

    def test_severity_classification(self, app):
        with app.app_context():
            from app.services.risk import classify_severity
            assert classify_severity(90) == 'CRITICAL'
            assert classify_severity(70) == 'HIGH'
            assert classify_severity(45) == 'MEDIUM'
            assert classify_severity(15) == 'LOW'
            assert classify_severity(5) == 'INFO'


class TestExplanationService:
    def test_explanation_not_random(self, app):
        with app.app_context():
            from app.services.explanation import generate_explanation
            kwargs = dict(
                prediction='attack', attack_type='dos', confidence=0.9,
                risk_score=75.0, severity='HIGH', anomaly_score=None,
                class_probabilities={'normal': 0.1, 'dos': 0.9},
                raw_features={'src_bytes': 1000},
                model_feature_importance=[{'feature': 'src_bytes', 'importance': 0.5}],
                feature_names=['src_bytes'],
            )
            e1 = generate_explanation(**kwargs)
            e2 = generate_explanation(**kwargs)
            assert e1['summary'] == e2['summary']

    def test_explanation_normal_has_no_attack_type(self, app):
        with app.app_context():
            from app.services.explanation import generate_explanation
            e = generate_explanation(
                prediction='normal', attack_type=None, confidence=0.95,
                risk_score=0.0, severity='INFO', anomaly_score=None,
                class_probabilities=None, raw_features={},
                model_feature_importance=None, feature_names=[],
            )
            assert 'NORMAL' in e['summary'].upper() or 'normal' in e['summary'].lower()

    def test_explanation_has_required_keys(self, app):
        with app.app_context():
            from app.services.explanation import generate_explanation
            e = generate_explanation(
                prediction='attack', attack_type='probe', confidence=0.7,
                risk_score=50.0, severity='MEDIUM', anomaly_score=0.3,
                class_probabilities={'probe': 0.7, 'normal': 0.3},
                raw_features={}, model_feature_importance=[], feature_names=[],
            )
            assert 'summary' in e
            assert 'key_factors' in e
            assert 'top_features' in e
            assert isinstance(e['key_factors'], list)


class TestAlertService:
    def test_no_alerts_for_low_risk_normal(self, app, db):
        with app.app_context():
            from app.models.activity import Activity
            from app.services.alerts import generate_alerts_for_activity
            from app.extensions import db as db_obj
            activity = Activity(
                prediction='normal', risk_score=5.0, severity='INFO',
                confidence=0.95, source='192.168.1.1',
            )
            db_obj.session.add(activity)
            db_obj.session.commit()
            alerts = generate_alerts_for_activity(activity)
            assert len(alerts) == 0

    def test_alert_generated_for_attack(self, app, db):
        with app.app_context():
            from app.models.activity import Activity
            from app.services.alerts import generate_alerts_for_activity
            from app.extensions import db as db_obj
            activity = Activity(
                prediction='attack', attack_type='dos',
                risk_score=75.0, severity='HIGH', confidence=0.9,
                source='10.0.0.1',
            )
            db_obj.session.add(activity)
            db_obj.session.commit()
            alerts = generate_alerts_for_activity(activity)
            assert len(alerts) >= 1
            assert any('Attack' in a.title or 'attack' in a.title.lower() for a in alerts)

    def test_alert_activity_id_set(self, app, db):
        with app.app_context():
            from app.models.activity import Activity
            from app.services.alerts import generate_alerts_for_activity
            from app.extensions import db as db_obj
            activity = Activity(
                prediction='attack', attack_type='probe',
                risk_score=80.0, severity='CRITICAL', confidence=0.85,
            )
            db_obj.session.add(activity)
            db_obj.session.commit()
            alerts = generate_alerts_for_activity(activity)
            for alert in alerts:
                assert alert.activity_id == activity.id


class TestDashboardService:
    def test_security_score_100_on_empty_db(self, app, db):
        with app.app_context():
            from app.services.dashboard import get_dashboard_data
            data = get_dashboard_data()
            assert data['security_score'] == 100
            assert data['has_data'] is False

    def test_security_score_decreases_with_attacks(self, app, db):
        with app.app_context():
            from app.models.activity import Activity
            from app.services.dashboard import get_dashboard_data
            from app.extensions import db as db_obj
            # Add some attack activities
            for _ in range(5):
                a = Activity(prediction='attack', attack_type='dos', risk_score=80.0, severity='HIGH')
                db_obj.session.add(a)
            db_obj.session.commit()
            data = get_dashboard_data()
            assert data['security_score'] < 100
            assert data['has_data'] is True
