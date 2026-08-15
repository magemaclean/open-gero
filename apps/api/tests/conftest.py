import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_opengero.db")
os.environ.setdefault("SECRET_KEY", "test-secret")

from opengero.config import get_settings

get_settings.cache_clear()
settings = get_settings()
settings.datasets_dir = Path(__file__).resolve().parents[3] / "data" / "datasets"
settings.targets_dir = Path(__file__).resolve().parents[3] / "data" / "targets"
settings.storage_dir = Path("./data/runtime-test")

import pytest
from fastapi.testclient import TestClient

from opengero.db import Base, engine, SessionLocal
from opengero.main import create_app
from opengero.seed import seed_all


@pytest.fixture(scope="session")
def client():
    db_path = Path("test_opengero.db")
    if db_path.exists():
        db_path.unlink()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
    app = create_app()
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    resp = client.post("/api/auth/login", json={"email": "demo@opengero.local", "password": "demo12345"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
