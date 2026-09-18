"""
OmniShield AI — API Tests
Tests all endpoints for success/error cases, validation, empty DB states.
"""
import json
import pytest


class TestDashboard:
    def test_dashboard_empty_db(self, client):
        res = client.get('/api/dashboard')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['success'] is True
        assert data['data']['total_activities'] == 0
        assert data['data']['has_data'] is False
        assert data['data']['security_score'] == 100

    def test_dashboard_has_data_field(self, client):
        res = client.get('/api/dashboard')
        data = json.loads(res.data)
        required_keys = [
            'total_activities', 'normal_count', 'suspicious_count',
            'attack_count', 'security_score', 'threat_level',
            'recent_alerts', 'recent_activities', 'attack_trend',
        ]
        for k in required_keys:
            assert k in data['data'], f"Missing key: {k}"


class TestAnalyze:
    def test_analyze_no_model(self, client):
        res = client.post('/api/analyze', json={'duration': 1})
        assert res.status_code == 503
        data = json.loads(res.data)
        assert data['success'] is False
        assert data['error']['code'] == 'MODEL_UNAVAILABLE'

    def test_analyze_empty_body(self, client):
        res = client.post('/api/analyze', data='', content_type='application/json')
        assert res.status_code == 400

    def test_model_features_no_model(self, client):
        res = client.get('/api/model/features')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['data']['model_loaded'] is False
        assert data['data']['features'] == []


class TestActivities:
    def test_list_activities_empty(self, client):
        res = client.get('/api/activities')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['data']['total'] == 0
        assert data['data']['activities'] == []

    def test_list_activities_pagination(self, client):
        res = client.get('/api/activities?page=1&per_page=5')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert 'page' in data['data']
        assert 'per_page' in data['data']

    def test_list_activities_invalid_date(self, client):
        res = client.get('/api/activities?date_from=not-a-date')
        assert res.status_code == 400

    def test_get_activity_not_found(self, client):
        res = client.get('/api/activities/99999')
        assert res.status_code == 404

    def test_list_activities_filters(self, client):
        for pred in ['normal', 'attack', 'suspicious']:
            res = client.get(f'/api/activities?prediction={pred}')
            assert res.status_code == 200


class TestAlerts:
    def test_list_alerts_empty(self, client):
        res = client.get('/api/alerts')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['data']['total'] == 0
        assert 'unread_count' in data['data']

    def test_patch_alert_not_found(self, client):
        res = client.patch('/api/alerts/99999', json={'status': 'ACKNOWLEDGED'})
        assert res.status_code == 404

    def test_patch_alert_missing_status(self, client):
        res = client.patch('/api/alerts/1', json={})
        assert res.status_code == 400

    def test_patch_alert_invalid_status(self, client):
        res = client.patch('/api/alerts/1', json={'status': 'INVALID_STATUS'})
        # Either 400 (validation) or 404 (not found) is acceptable
        assert res.status_code in (400, 404)


class TestAnalytics:
    def test_analytics_empty(self, client):
        res = client.get('/api/analytics')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['data']['has_data'] is False

    def test_analytics_days_param(self, client):
        for days in [7, 30, 90]:
            res = client.get(f'/api/analytics?days={days}')
            assert res.status_code == 200
            assert json.loads(res.data)['data']['period_days'] == days


class TestDatasets:
    def test_list_datasets_empty(self, client):
        res = client.get('/api/datasets')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['data']['datasets'] == []

    def test_upload_no_file(self, client):
        res = client.post('/api/dataset/upload')
        assert res.status_code == 400

    def test_upload_invalid_extension(self, client):
        from io import BytesIO
        data = {'file': (BytesIO(b'test data'), 'test.txt')}
        res = client.post('/api/dataset/upload', data=data, content_type='multipart/form-data')
        assert res.status_code == 400

    def test_train_missing_fields(self, client):
        res = client.post('/api/dataset/train', json={})
        assert res.status_code == 400

    def test_train_dataset_not_found(self, client):
        res = client.post('/api/dataset/train', json={'dataset_id': 99999, 'target_column': 'label'})
        assert res.status_code == 404


class TestModels:
    def test_model_info_no_model(self, client):
        res = client.get('/api/model/info')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['data']['loaded'] is False

    def test_model_performance_no_model(self, client):
        res = client.get('/api/model/performance')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['data']['has_model'] is False

    def test_list_models(self, client):
        res = client.get('/api/models')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert 'models' in data['data']

    def test_model_status_not_found(self, client):
        res = client.get('/api/model/status/99999')
        assert res.status_code == 404


class TestReports:
    def test_generate_summary_report(self, client):
        res = client.post('/api/report/generate', json={'type': 'summary'})
        assert res.status_code == 200
        data = json.loads(res.data)
        assert 'summary' in data['data']
        assert 'alerts' in data['data']

    def test_generate_detailed_report(self, client):
        res = client.post('/api/report/generate', json={'type': 'detailed'})
        assert res.status_code == 200

    def test_generate_invalid_type(self, client):
        res = client.post('/api/report/generate', json={'type': 'invalid'})
        assert res.status_code == 400


class TestErrorHandling:
    def test_standard_success_format(self, client):
        res = client.get('/api/dashboard')
        data = json.loads(res.data)
        assert 'success' in data
        assert 'data' in data
        assert data['success'] is True

    def test_standard_error_format(self, client):
        res = client.get('/api/activities/99999')
        data = json.loads(res.data)
        assert 'success' in data
        assert data['success'] is False
        assert 'error' in data
        assert 'code' in data['error']
        assert 'message' in data['error']
