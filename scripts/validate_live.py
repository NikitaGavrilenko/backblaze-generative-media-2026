"""Validate live credentials without starting a generation request."""

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
        public_url_base=settings.storage_public_url_base,
        auto_lifecycle=False,
        preflight=True,
    )
    try:
        backend.list(prefix="proofstudio/", max_keys=1)
    finally:
        backend.close()
    print("Backblaze B2 authentication: OK")

    response = httpx.get(
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{settings.cloudflare_account_id}/ai/models/search",
        params={"search": settings.cloudflare_model},
        headers={"Authorization": f"Bearer {settings.cloudflare_api_token}"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    model_names = [item.get("name") for item in payload.get("result", [])]
    if settings.cloudflare_model not in model_names:
        raise SystemExit("CLOUDFLARE_MODEL is not available to this account.")
    print(f"Cloudflare Workers AI authentication: OK ({settings.cloudflare_model})")
    print("No generation request was made and no Neurons were consumed.")


if __name__ == "__main__":
    main()
