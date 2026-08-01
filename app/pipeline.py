"""Genblaze-backed local demo pipeline and integrity verification."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from html import escape
from uuid import uuid4

from genblaze_core import Manifest, Modality, RunBuilder, StepBuilder, StepStatus

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


class DemoPipeline:
    """Produces transparent local fixtures while exercising Genblaze provenance."""

    def __init__(self, repository: RunRepository, public_data_prefix: str = "/data") -> None:
        self.repository = repository
        self.public_data_prefix = public_data_prefix.rstrip("/")

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
            idempotency_key=idempotency_key,
            created_at=created_at,
            completed_at=completed_at,
        )
        self.repository.save(run)
        return run

    def verify(self, run: GenerationRun) -> VerificationResult:
        errors: list[str] = []
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
