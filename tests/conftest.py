"""
OmniShield AI — Test Configuration and Fixtures
"""
import os
import pytest
import pandas as pd
import numpy as np

from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """Create application for testing."""
    os.environ["FLASK_ENV"] = "testing"
    flask_app = create_app("testing")
    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    os.makedirs(flask_app.config.get("UPLOAD_FOLDER", "/tmp/omnishield_test"), exist_ok=True)
    os.makedirs(flask_app.config.get("MODEL_FOLDER", "/tmp/omnishield_models"), exist_ok=True)
    os.makedirs(flask_app.config.get("MODEL_METADATA_FOLDER", "/tmp/omnishield_metadata"), exist_ok=True)
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()



@pytest.fixture
def sample_csv(tmp_path):
    """Create a small sample CSV for ML tests."""
    np.random.seed(42)
    n = 200
    df = pd.DataFrame({
        "duration": np.random.randint(0, 100, n),
        "src_bytes": np.random.randint(0, 10000, n),
        "dst_bytes": np.random.randint(0, 10000, n),
        "protocol_type": np.random.choice(["tcp", "udp", "icmp"], n),
        "service": np.random.choice(["http", "ftp", "smtp", "ssh"], n),
        "flag": np.random.choice(["SF", "S0", "REJ"], n),
        "land": np.random.randint(0, 2, n),
        "wrong_fragment": np.random.randint(0, 3, n),
        "label": np.random.choice(["normal", "dos", "probe"], n, p=[0.5, 0.3, 0.2]),
    })
    path = tmp_path / "test_dataset.csv"
    df.to_csv(path, index=False)
    return str(path)
