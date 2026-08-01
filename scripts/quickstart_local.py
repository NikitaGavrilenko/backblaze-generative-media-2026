"""Build and verify a Genblaze manifest without API keys or network calls."""

from __future__ import annotations

import hashlib

from genblaze_core import Manifest, Modality, RunBuilder, StepBuilder, StepStatus


def main() -> None:
    asset_bytes = b"ProofStudio local smoke-test asset"
    asset_sha256 = hashlib.sha256(asset_bytes).hexdigest()

    step = (
        StepBuilder("proofstudio-local", "deterministic-smoke-test")
        .prompt("Create a traceable campaign image.")
        .modality(Modality.IMAGE)
        .params(width=1024, height=1024, demo_mode=True)
        .seed(42)
        .status(StepStatus.SUCCEEDED)
        .asset(
            "file://output/proofstudio-smoke-test.webp",
            "image/webp",
            sha256=asset_sha256,
        )
        .build()
    )
    run = RunBuilder("proofstudio-local-smoke-test").add_step(step).build()
    manifest = Manifest.from_run(run)

    if not manifest.verify():
        raise RuntimeError("Genblaze manifest verification failed.")

    print(f"Run ID: {run.run_id}")
    print(f"Manifest hash: {manifest.canonical_hash}")
    print("Verified: True")


if __name__ == "__main__":
    main()
