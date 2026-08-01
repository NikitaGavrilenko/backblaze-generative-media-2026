"""Validate live credentials without starting a paid generation request."""

from __future__ import annotations

import httpx

from app.config import Settings


def main() -> None:
    settings = Settings()
    missing = settings.live_configuration_errors()
    if missing:
        raise SystemExit(f"Missing settings: {', '.join(missing)}")

    from genblaze_s3 import S3StorageBackend

    backend = S3StorageBackend.for_backblaze(
        settings.b2_bucket,
        region=settings.b2_region,
        key_id=settings.b2_key_id,
        app_key=settings.b2_app_key,
        public_url_base=settings.b2_public_url_base,
        auto_lifecycle=False,
        preflight=True,
    )
    try:
        backend.list(prefix="proofstudio/", max_keys=1)
    finally:
        backend.close()
    print("Backblaze B2 authentication: OK")

    response = httpx.get(
        "https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey/models",
        headers={"Authorization": f"Bearer {settings.gmi_api_key}"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    model_ids = payload.get("model_ids", payload if isinstance(payload, list) else [])
    if settings.gmi_model not in model_ids:
        raise SystemExit("GMI_MODEL is not present in the models available to this API key.")
    print(f"GMI Cloud authentication and model access: OK ({settings.gmi_model})")
    print("No paid generation request was made.")


if __name__ == "__main__":
    main()
