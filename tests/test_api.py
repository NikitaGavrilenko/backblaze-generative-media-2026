from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.pipeline import DemoPipeline
from app.schemas import CampaignBrief


def build_client(tmp_path: Path) -> TestClient:
    app = create_app(Settings(_env_file=None, data_dir=tmp_path, demo_mode=True))
    return TestClient(app)


def test_health(tmp_path: Path) -> None:
    response = build_client(tmp_path).get("/api/health")

    assert response.status_code == 200
    assert response.json()["genblaze"] == "0.3.8"
    assert response.json()["mode"] == "demo"


def test_homepage_uses_runtime_storage_copy(tmp_path: Path) -> None:
    response = build_client(tmp_path).get("/")

    assert response.status_code == 200
    assert 'id="mode-note"' in response.text
    assert 'id="storage-indicator"' in response.text
    assert "integration pending credentials" not in response.text
    assert "Backblaze B2 is the next integration gate" not in response.text


def test_live_mode_reports_missing_configuration(tmp_path: Path) -> None:
    app = create_app(Settings(_env_file=None, data_dir=tmp_path, demo_mode=False))
    client = TestClient(app)

    health = client.get("/api/health")
    created = client.post(
        "/api/runs",
        json={
            "name": "Live launch",
            "audience": "Creative teams",
            "message": "Generate a traceable campaign.",
            "tone": "Editorial",
        },
    )

    assert health.json()["status"] == "degraded"
    assert "CLOUDFLARE_API_TOKEN" in health.json()["missing_settings"]
    assert created.status_code == 503


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


def test_private_b2_proxy_only_serves_recorded_objects(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        app_base_url="https://proofstudio.example",
        data_dir=tmp_path,
        demo_mode=False,
        b2_key_id="key-id",
        b2_app_key="app-key",
        b2_bucket="bucket",
        b2_region="us-west-004",
        cloudflare_account_id="account-id",
        cloudflare_api_token="api-token",
    )
    app = create_app(settings)
    demo_run = DemoPipeline(app.state.repository).run(
        CampaignBrief(
            name="Private storage",
            audience="Hackathon judges",
            message="Serve durable media without making the bucket public.",
            tone="Editorial",
        ),
        "private-proxy-test",
    )
    storage_key = "proofstudio/assets/aa/example.png"
    live_run = demo_run.model_copy(
        update={
            "demo_mode": False,
            "assets": [
                demo_run.assets[0].model_copy(
                    update={"storage_key": storage_key, "mime_type": "image/png"}
                )
            ],
            "manifest_storage_key": "proofstudio/manifests/example.json",
        }
    )
    app.state.repository.save(live_run)
    monkeypatch.setattr(app.state.pipeline, "sync_repository", lambda: None)
    monkeypatch.setattr(
        app.state.pipeline,
        "fetch_object",
        lambda key: (b"stored-image", "image/png"),
    )
    client = TestClient(app)

    stored = client.get(f"/api/storage/{storage_key}")
    unrecorded = client.get("/api/storage/proofstudio/app-runs/private.json")

    assert settings.storage_public_url_base == "https://proofstudio.example/api/storage"
    assert "B2_PUBLIC_URL_BASE" not in settings.live_configuration_errors()
    assert stored.status_code == 200
    assert stored.content == b"stored-image"
    assert stored.headers["content-type"] == "image/png"
    assert unrecorded.status_code == 404
