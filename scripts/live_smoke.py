"""Run the paid end-to-end technical gate after explicit confirmation."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.config import Settings
from app.pipeline import LivePipeline
from app.repository import RunRepository
from app.schemas import CampaignBrief


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm-paid-run",
        action="store_true",
        help="Confirm that one provider request producing two image variants may incur cost.",
    )
    args = parser.parse_args()
    if not args.confirm_paid_run:
        raise SystemExit("Refusing paid generation without --confirm-paid-run.")

    settings = Settings(demo_mode=False)
    pipeline = LivePipeline(RunRepository(Path("data/live-smoke")), settings)
    run = pipeline.run(
        CampaignBrief(
            name="ProofStudio Launch",
            audience="Creative and marketing teams",
            message="Every generated asset should remain traceable and verifiable.",
            tone="Confident, modern, editorial",
            visual_constraints=["Clear focal point", "No embedded text", "Premium lighting"],
            aspect_ratio="1:1",
        ),
        "proofstudio-live-smoke-v1",
    )
    verification = pipeline.verify(run)
    if not verification.verified:
        raise SystemExit(f"Verification failed: {'; '.join(verification.errors)}")
    print(f"Run ID: {run.id}")
    print(f"Provider/model: {run.provider} / {run.model}")
    print(f"Assets: {len(run.assets)}")
    print(f"Manifest: {run.manifest_url}")
    print(f"Manifest hash: {run.manifest_hash}")
    print("B2 asset and manifest verification: OK")


if __name__ == "__main__":
    main()
