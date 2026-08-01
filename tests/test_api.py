from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def build_client(tmp_path: Path) -> TestClient:
    app = create_app(Settings(data_dir=tmp_path, demo_mode=True))
    return TestClient(app)


def test_health(tmp_path: Path) -> None:
    response = build_client(tmp_path).get("/api/health")

    assert response.status_code == 200
    assert response.json()["genblaze"] == "0.3.8"


def test_create_and_verify_run(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    payload = {
        "name": "Lumen Launch",
        "audience": "Independent creative teams",
        "message": "Make every generated asset accountable.",
        "tone": "Confident and editorial",
        "visual_constraints": ["Clear typography"],
        "aspect_ratio": "1:1",
    }

    created = client.post(
        "/api/runs",
        headers={"Idempotency-Key": "api-test"},
        json=payload,
    )
    verified = client.post(f"/api/runs/{created.json()['id']}/verify")

    assert created.status_code == 201
    assert created.json()["verified"] is True
    assert len(created.json()["assets"]) == 2
    assert verified.status_code == 200
    assert verified.json()["verified"] is True


def test_rejects_invalid_brief(tmp_path: Path) -> None:
    response = build_client(tmp_path).post(
        "/api/runs",
        json={
            "name": "",
            "audience": "A",
            "message": "",
            "tone": "",
            "aspect_ratio": "3:2",
        },
    )

    assert response.status_code == 422
