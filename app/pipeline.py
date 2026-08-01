"""Genblaze-backed local demo pipeline and integrity verification."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from html import escape
from typing import Protocol
from uuid import uuid4

from genblaze_core import (
    KeyStrategy,
    Manifest,
    Modality,
    ObjectStorageSink,
    Pipeline,
    RunBuilder,
    StepBuilder,
    StepStatus,
)

from app.config import Settings
from app.providers import CloudflareImageProvider
from app.repository import RunRepository
from app.schemas import (
    CampaignBrief,
    GenerationRun,
    MediaAsset,
    RunStatus,
    VerificationResult,
)

DEMO_PROVIDER = "proofstudio-demo"
DEMO_MODEL = "deterministic-svg-1"


class GenerationPipeline(Protocol):
    def run(self, brief: CampaignBrief, idempotency_key: str | None) -> GenerationRun: ...

    def verify(self, run: GenerationRun) -> VerificationResult: ...


class DemoPipeline:
    """Produces transparent local fixtures while exercising Genblaze provenance."""

    def __init__(self, repository: RunRepository, public_data_prefix: str = "/data") -> None:
        self.repository = repository
        self.public_data_prefix = public_data_prefix.rstrip("/")

    @staticmethod
    def _build_prompt(brief: CampaignBrief) -> str:
        return LivePipeline._build_prompt(brief)

    @staticmethod
    def _render_svg(brief: CampaignBrief, variant: int) -> str:
        return LivePipeline._render_svg(brief, variant)

    def run(self, brief: CampaignBrief, idempotency_key: str | None) -> GenerationRun:
        if idempotency_key:
            existing = self.repository.find_by_idempotency_key(idempotency_key)
            if existing:
                return existing

        run_id = str(uuid4())
        created_at = datetime.now(UTC)
        run_dir = self.repository.runs_dir / run_id
        assets_dir = run_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        prompt = self._build_prompt(brief)

        step_builder = (
            StepBuilder(DEMO_PROVIDER, DEMO_MODEL)
            .prompt(prompt)
            .modality(Modality.IMAGE)
            .params(aspect_ratio=brief.aspect_ratio, demo_mode=True, variants=2)
            .seed(42)
            .status(StepStatus.SUCCEEDED)
        )

        assets: list[MediaAsset] = []
        for variant in (1, 2):
            asset_id = str(uuid4())
            storage_key = f"runs/{run_id}/assets/variant-{variant}.svg"
            asset_path = self.repository.data_dir / storage_key
            asset_bytes = self._render_svg(brief, variant).encode("utf-8")
            asset_path.write_bytes(asset_bytes)
            asset_sha256 = hashlib.sha256(asset_bytes).hexdigest()
            asset_url = f"{self.public_data_prefix}/{storage_key}"
            step_builder.asset(
                asset_path.resolve().as_uri(),
                "image/svg+xml",
                sha256=asset_sha256,
            )
            assets.append(
                MediaAsset(
                    id=asset_id,
                    variant=variant,
                    url=asset_url,
                    storage_key=storage_key,
                    mime_type="image/svg+xml",
                    sha256=asset_sha256,
                )
            )

        step = step_builder.build()
        genblaze_run = RunBuilder("proofstudio-demo").add_step(step).build()
        manifest = Manifest.from_run(genblaze_run)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(manifest.to_canonical_json(), encoding="utf-8")
        verified = manifest.verify()
        completed_at = datetime.now(UTC)

        run = GenerationRun(
            id=run_id,
            campaign=brief,
            status=RunStatus.COMPLETED,
            provider=DEMO_PROVIDER,
            model=DEMO_MODEL,
            prompt=prompt,
            manifest_url=f"{self.public_data_prefix}/runs/{run_id}/manifest.json",
            manifest_hash=manifest.canonical_hash,
            verified=verified,
            demo_mode=True,
            assets=assets,
            parameters={
                "aspect_ratio": brief.aspect_ratio,
                "demo_mode": True,
                "seed": 42,
                "variants": 2,
            },
            manifest_storage_key=f"runs/{run_id}/manifest.json",
            idempotency_key=idempotency_key,
            created_at=created_at,
            completed_at=completed_at,
        )
        self.repository.save(run)
        return run

    def verify(self, run: GenerationRun) -> VerificationResult:
        errors: list[str] = []
        manifest_path = self.repository.runs_dir / run.id / "manifest.json"
        if not manifest_path.is_file():
            errors.append("Manifest is missing.")
        else:
            try:
                manifest = Manifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
                if not manifest.verify() or manifest.canonical_hash != run.manifest_hash:
                    errors.append("Manifest failed canonical hash verification.")
            except (OSError, ValueError):
                errors.append("Manifest is invalid.")

        for asset in run.assets:
            asset_path = (self.repository.data_dir / asset.storage_key).resolve()
            if not asset_path.is_relative_to(self.repository.data_dir):
                errors.append(f"Unsafe storage key for asset {asset.id}.")
                continue
            if not asset_path.is_file():
                errors.append(f"Asset {asset.id} is missing.")
                continue
            actual_hash = hashlib.sha256(asset_path.read_bytes()).hexdigest()
            if actual_hash != asset.sha256:
                errors.append(f"Asset {asset.id} failed SHA-256 verification.")

        return VerificationResult(
            run_id=run.id,
            verified=not errors and run.verified,
            checked_assets=len(run.assets),
            errors=errors,
        )


class LivePipeline:
    """Runs Cloudflare Workers AI image generation and persists outputs to B2."""

    def __init__(self, repository: RunRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings
        self._history_synced = False

    def _open_backend(self):
        from genblaze_s3 import S3StorageBackend

        return S3StorageBackend.for_backblaze(
            self.settings.b2_bucket,
            region=self.settings.b2_region,
            key_id=self.settings.b2_key_id,
            app_key=self.settings.b2_app_key,
            public_url_base=self.settings.storage_public_url_base,
            auto_lifecycle=False,
            preflight=True,
        )

    def fetch_object(self, key: str) -> tuple[bytes, str]:
        """Fetch an approved B2 object for delivery through the public app."""
        backend = self._open_backend()
        try:
            metadata = backend.head(key)
            if metadata is None:
                raise FileNotFoundError(key)
            return backend.get(key), metadata.content_type or "application/octet-stream"
        finally:
            backend.close()

    def sync_repository(self) -> None:
        """Hydrate local run history from B2 once per application process."""
        if self._history_synced or self.settings.live_configuration_errors():
            return
        backend = self._open_backend()
        token: str | None = None
        try:
            while True:
                page = backend.list(
                    prefix="proofstudio/app-runs/",
                    continuation_token=token,
                )
                for entry in page.entries:
                    try:
                        run = GenerationRun.model_validate_json(backend.get(entry.key))
                    except (OSError, ValueError):
                        continue
                    self.repository.save(run)
                token = page.next_token
                if token is None:
                    break
            self._history_synced = True
        finally:
            backend.close()

    def _persist_run_history(self, run: GenerationRun) -> None:
        backend = self._open_backend()
        try:
            backend.put(
                f"proofstudio/app-runs/{run.id}.json",
                run.model_dump_json(indent=2).encode("utf-8"),
                content_type="application/json",
            )
        finally:
            backend.close()

    def run(self, brief: CampaignBrief, idempotency_key: str | None) -> GenerationRun:
        if idempotency_key:
            existing = self.repository.find_by_idempotency_key(idempotency_key)
            if existing:
                return existing

        missing = self.settings.live_configuration_errors()
        if missing:
            raise RuntimeError(f"Live mode is missing settings: {', '.join(missing)}")

        created_at = datetime.now(UTC)
        prompt = DemoPipeline._build_prompt(brief)
        model = self.settings.cloudflare_model
        provider = CloudflareImageProvider(
            account_id=self.settings.cloudflare_account_id or "",
            api_token=self.settings.cloudflare_api_token or "",
            timeout=self.settings.generation_timeout_seconds,
        )
        try:
            backend = self._open_backend()
            try:
                sink = ObjectStorageSink(
                    backend,
                    prefix="proofstudio",
                    key_strategy=KeyStrategy.CONTENT_ADDRESSABLE,
                )
                result = (
                    Pipeline("proofstudio-live", project_id="proofstudio", preflight=True)
                    .step(
                        provider,
                        model=model,
                        prompt=prompt,
                        modality=Modality.IMAGE,
                        aspect_ratio=brief.aspect_ratio,
                        number_of_images=2,
                    )
                    .run(
                        sink=sink,
                        fail_fast=True,
                        timeout=self.settings.generation_timeout_seconds,
                        max_retries=0,
                        raise_on_failure=True,
                    )
                )
                assets = [asset for step in result.run.steps for asset in step.assets]
                failed_steps = [
                    step for step in result.run.steps if step.status is StepStatus.FAILED
                ]
                if failed_steps:
                    raise RuntimeError(
                        "The image provider rejected or failed the request. Check server logs."
                    )
                if len(assets) < 2:
                    raise RuntimeError(
                        "The provider completed without two stored image variants."
                    )

                media_assets = [
                    MediaAsset(
                        id=asset.asset_id,
                        variant=index,
                        url=asset.url,
                        storage_key=backend.key_from_url(asset.url) or asset.url,
                        mime_type=asset.media_type,
                        sha256=asset.sha256 or "",
                    )
                    for index, asset in enumerate(assets[:2], start=1)
                ]
                provider_job_ids = [
                    str(request_id)
                    for step in result.run.steps
                    for request_id in (step.provider_payload or {})
                    .get("cloudflare", {})
                    .get("request_ids", [])
                    if request_id
                ]
                manifest_key = sink.manifest_key_for(result.run)
                manifest_url = sink.manifest_url_for(result.run)
            finally:
                backend.close()
        finally:
            provider.close()

        run = GenerationRun(
            id=result.run.run_id,
            campaign=brief,
            status=RunStatus.COMPLETED,
            provider=provider.name,
            model=model,
            prompt=prompt,
            manifest_url=manifest_url,
            manifest_hash=result.manifest.canonical_hash,
            verified=result.manifest.verify(),
            demo_mode=False,
            assets=media_assets,
            parameters={
                "aspect_ratio": brief.aspect_ratio,
                "number_of_images": 2,
            },
            provider_job_ids=provider_job_ids,
            manifest_storage_key=manifest_key,
            idempotency_key=idempotency_key,
            created_at=created_at,
            completed_at=datetime.now(UTC),
        )
        self.repository.save(run)
        self._persist_run_history(run)
        return run

    def verify(self, run: GenerationRun) -> VerificationResult:
        errors: list[str] = []
        missing = self.settings.live_configuration_errors()
        if missing:
            return VerificationResult(
                run_id=run.id,
                verified=False,
                checked_assets=0,
                errors=[f"Live verification is missing settings: {', '.join(missing)}"],
            )

        backend = self._open_backend()
        try:
            if not run.manifest_storage_key:
                errors.append("Manifest storage key is missing.")
            else:
                manifest = Manifest.model_validate_json(
                    backend.get(run.manifest_storage_key).decode("utf-8")
                )
                if not manifest.verify() or manifest.canonical_hash != run.manifest_hash:
                    errors.append("Stored manifest failed canonical hash verification.")

            for asset in run.assets:
                data = backend.get(asset.storage_key)
                if hashlib.sha256(data).hexdigest() != asset.sha256:
                    errors.append(f"Asset {asset.id} failed SHA-256 verification.")
        except Exception:
            errors.append("B2 verification failed. Check server logs and storage configuration.")
        finally:
            backend.close()

        return VerificationResult(
            run_id=run.id,
            verified=not errors,
            checked_assets=len(run.assets),
            errors=errors,
        )

    @staticmethod
    def _build_prompt(brief: CampaignBrief) -> str:
        constraints = ", ".join(brief.visual_constraints) or "none"
        return (
            f"Campaign: {brief.name}. Audience: {brief.audience}. "
            f"Message: {brief.message}. Tone: {brief.tone}. "
            f"Visual constraints: {constraints}. Aspect ratio: {brief.aspect_ratio}."
        )

    @staticmethod
    def _render_svg(brief: CampaignBrief, variant: int) -> str:
        palettes = [
            ("#f4f1e8", "#ff5c35", "#191919"),
            ("#171a26", "#8bea9f", "#f7f7ee"),
        ]
        background, accent, foreground = palettes[variant - 1]
        safe_name = escape(brief.name)
        safe_message = escape(brief.message[:86])
        safe_audience = escape(brief.audience[:72])
        wave_start = 820 if variant == 1 else 900
        wave_control = 620 if variant == 1 else 1080
        return f"""<svg
  xmlns="http://www.w3.org/2000/svg"
  width="1200"
  height="1200"
  viewBox="0 0 1200 1200">
<rect width="1200" height="1200" fill="{background}"/>
<circle
  cx="{180 if variant == 1 else 1020}"
  cy="180"
  r="260"
  fill="{accent}"
  opacity=".92"/>
<path
  d="M0 {wave_start} Q600 {wave_control} 1200 760 V1200 H0Z"
  fill="{accent}"
  opacity=".18"/>
<text
  x="90"
  y="100"
  fill="{foreground}"
  font-family="Arial, sans-serif"
  font-size="28"
  letter-spacing="5">PROOFSTUDIO / DEMO VARIANT {variant}</text>
<text
  x="90"
  y="500"
  fill="{foreground}"
  font-family="Arial, sans-serif"
  font-size="82"
  font-weight="700">{safe_name}</text>
<foreignObject x="90" y="555" width="920" height="220">
  <div
    xmlns="http://www.w3.org/1999/xhtml"
    style="font: 48px Arial, sans-serif; color: {foreground}; line-height: 1.2">
    {safe_message}
  </div>
</foreignObject>
<text
  x="90"
  y="1080"
  fill="{foreground}"
  font-family="Arial, sans-serif"
  font-size="26">For {safe_audience}</text>
<text
  x="90"
  y="1130"
  fill="{foreground}"
  font-family="Arial, sans-serif"
  font-size="20">Local fixture — no AI generation call was made</text>
</svg>"""
