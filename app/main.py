"""ProofStudio FastAPI entrypoint."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.pipeline import DemoPipeline, LivePipeline
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
    demo_pipeline = DemoPipeline(repository)
    live_pipeline = LivePipeline(repository, active_settings)
    pipeline = demo_pipeline if active_settings.demo_mode else live_pipeline

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
        missing_settings = active_settings.live_configuration_errors()
        return HealthResponse(
            status="ok" if active_settings.demo_mode or not missing_settings else "degraded",
            mode="demo" if active_settings.demo_mode else "live",
            genblaze="0.3.8",
            storage="local" if active_settings.demo_mode else "backblaze-b2",
            live_configured=not missing_settings,
            missing_settings=missing_settings,
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
        normalized_key = idempotency_key.strip() if idempotency_key else None
        if normalized_key and len(normalized_key) > 128:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency-Key must be at most 128 characters.",
            )
        try:
            return pipeline.run(brief, normalized_key)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Generation or durable storage failed. Check server logs.",
            ) from exc

    @application.get("/api/runs", response_model=list[GenerationRun])
    def list_runs() -> list[GenerationRun]:
        if not active_settings.demo_mode:
            with suppress(Exception):
                live_pipeline.sync_repository()
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
        if not run.demo_mode:
            return RedirectResponse(
                run.manifest_url,
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            )
        manifest_path = repository.runs_dir / run_id / "manifest.json"
        if not manifest_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manifest not found.",
            )
        return Response(manifest_path.read_text(encoding="utf-8"), media_type="application/json")

    @application.get("/api/storage/{object_key:path}")
    def get_live_object(object_key: str) -> Response:
        """Serve only assets and manifests belonging to recorded live runs."""
        if active_settings.demo_mode:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found.")

        with suppress(Exception):
            live_pipeline.sync_repository()
        allowed_keys = {
            key
            for run in repository.list()
            for key in [
                run.manifest_storage_key,
                *(asset.storage_key for asset in run.assets),
            ]
            if key
        }
        if object_key not in allowed_keys:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found.")

        try:
            body, media_type = live_pipeline.fetch_object(object_key)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Object not found.",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stored object is temporarily unavailable.",
            ) from exc
        return Response(
            body,
            media_type=media_type,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    @application.post(
        "/api/runs/{run_id}/verify",
        response_model=VerificationResult,
    )
    def verify_run(run_id: str) -> VerificationResult:
        run = repository.get(run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
        verifier = demo_pipeline if run.demo_mode else live_pipeline
        return verifier.verify(run)

    return application


app = create_app()
