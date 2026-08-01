"""ProofStudio FastAPI entrypoint."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.pipeline import DemoPipeline
from app.repository import RunRepository
from app.schemas import (
    CampaignBrief,
    GenerationRun,
    HealthResponse,
    VerificationResult,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "app" / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    data_dir = active_settings.data_dir
    if not data_dir.is_absolute():
        data_dir = ROOT_DIR / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    repository = RunRepository(data_dir)
    pipeline = DemoPipeline(repository)

    application = FastAPI(
        title="ProofStudio",
        version="0.1.0",
        description="Traceable generative media workflows with Genblaze and Backblaze B2.",
    )
    application.state.settings = active_settings
    application.state.repository = repository
    application.state.pipeline = pipeline

    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    application.mount("/data", StaticFiles(directory=data_dir), name="data")

    @application.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @application.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            mode="demo" if active_settings.demo_mode else "live",
            genblaze="0.3.8",
            storage="local",
        )

    @application.post(
        "/api/runs",
        response_model=GenerationRun,
        status_code=status.HTTP_201_CREATED,
    )
    def create_run(
        brief: CampaignBrief,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> GenerationRun:
        if not active_settings.demo_mode:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Live pipeline is not configured yet.",
            )
        normalized_key = idempotency_key.strip() if idempotency_key else None
        if normalized_key and len(normalized_key) > 128:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency-Key must be at most 128 characters.",
            )
        return pipeline.run(brief, normalized_key)

    @application.get("/api/runs", response_model=list[GenerationRun])
    def list_runs() -> list[GenerationRun]:
        return repository.list()

    @application.get("/api/runs/{run_id}", response_model=GenerationRun)
    def get_run(run_id: str) -> GenerationRun:
        run = repository.get(run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
        return run

    @application.get("/api/runs/{run_id}/manifest")
    def get_manifest(run_id: str) -> Response:
        run = repository.get(run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
        manifest_path = repository.runs_dir / run_id / "manifest.json"
        if not manifest_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manifest not found.",
            )
        return Response(manifest_path.read_text(encoding="utf-8"), media_type="application/json")

    @application.post(
        "/api/runs/{run_id}/verify",
        response_model=VerificationResult,
    )
    def verify_run(run_id: str) -> VerificationResult:
        run = repository.get(run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
        return pipeline.verify(run)

    return application


app = create_app()

