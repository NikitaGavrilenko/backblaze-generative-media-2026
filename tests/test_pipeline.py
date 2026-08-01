from pathlib import Path

from app.pipeline import DemoPipeline
from app.repository import RunRepository
from app.schemas import CampaignBrief


def sample_brief() -> CampaignBrief:
    return CampaignBrief(
        name="Lumen Launch",
        audience="Independent creative teams",
        message="Make every generated asset accountable.",
        tone="Confident and editorial",
        visual_constraints=["No stock-photo look", "Clear typography"],
        aspect_ratio="1:1",
    )


def test_demo_pipeline_creates_verified_run(tmp_path: Path) -> None:
    repository = RunRepository(tmp_path)
    pipeline = DemoPipeline(repository)

    run = pipeline.run(sample_brief(), "stable-request")

    assert run.verified is True
    assert len(run.assets) == 2
    assert all((tmp_path / asset.storage_key).is_file() for asset in run.assets)
    assert pipeline.verify(run).verified is True


def test_idempotency_key_returns_existing_run(tmp_path: Path) -> None:
    repository = RunRepository(tmp_path)
    pipeline = DemoPipeline(repository)

    first = pipeline.run(sample_brief(), "stable-request")
    second = pipeline.run(sample_brief(), "stable-request")

    assert first.id == second.id
    assert len(repository.list()) == 1


def test_verification_detects_modified_asset(tmp_path: Path) -> None:
    repository = RunRepository(tmp_path)
    pipeline = DemoPipeline(repository)
    run = pipeline.run(sample_brief(), None)
    asset_path = tmp_path / run.assets[0].storage_key
    asset_path.write_text("tampered", encoding="utf-8")

    result = pipeline.verify(run)

    assert result.verified is False
    assert "failed SHA-256 verification" in result.errors[0]


def test_verification_detects_modified_manifest(tmp_path: Path) -> None:
    repository = RunRepository(tmp_path)
    pipeline = DemoPipeline(repository)
    run = pipeline.run(sample_brief(), None)
    manifest_path = tmp_path / "runs" / run.id / "manifest.json"
    manifest_path.write_text('{"tampered": true}', encoding="utf-8")

    result = pipeline.verify(run)

    assert result.verified is False
    assert "Manifest is invalid" in result.errors[0]
