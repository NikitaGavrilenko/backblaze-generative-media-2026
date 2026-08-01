"""Genblaze image provider backed by Cloudflare Workers AI."""

from __future__ import annotations

import base64
import binascii
import shutil
import tempfile
from pathlib import Path
from typing import Any

import httpx
from genblaze_core import Asset, Modality, Step
from genblaze_core.exceptions import ProviderError
from genblaze_core.providers import (
    ModelRegistry,
    ModelSpec,
    ParamSurface,
    ProviderCapabilities,
    SyncProvider,
)
from genblaze_core.runnable.config import RunnableConfig

CLOUDFLARE_IMAGE_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
_DIMENSIONS = {
    "1:1": (1024, 1024),
    "4:5": (768, 960),
    "16:9": (1024, 576),
    "9:16": (576, 1024),
}


class CloudflareImageProvider(SyncProvider):
    """Generate image variants through the Cloudflare Workers AI REST API."""

    name = "cloudflare-workers-ai"

    def __init__(
        self,
        *,
        account_id: str,
        api_token: str,
        timeout: float = 120,
        http_client: httpx.Client | None = None,
    ) -> None:
        super().__init__()
        self.account_id = account_id
        self.api_token = api_token
        self._client = http_client or httpx.Client(timeout=timeout)
        self._owns_client = http_client is None
        self._temp_dir = Path(tempfile.mkdtemp(prefix="proofstudio-cloudflare-"))

    @classmethod
    def create_registry(cls) -> ModelRegistry:
        registry = ModelRegistry()
        registry.register(
            ModelSpec(
                model_id=CLOUDFLARE_IMAGE_MODEL,
                modality=Modality.IMAGE,
                **ParamSurface.for_modality(Modality.IMAGE)
                .extend("number_of_images")
                .build(),
            )
        )
        return registry

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_modalities=[Modality.IMAGE],
            supported_inputs=["text"],
            models=[CLOUDFLARE_IMAGE_MODEL],
            output_formats=["image/jpeg", "image/png"],
        )

    def generate(self, step: Step, config: RunnableConfig | None = None) -> Step:
        del config
        if step.model != CLOUDFLARE_IMAGE_MODEL:
            raise ProviderError(f"Unsupported Cloudflare image model: {step.model}")

        count = int(step.params.get("number_of_images", 1))
        if count < 1 or count > 4:
            raise ProviderError("Cloudflare image variant count must be between 1 and 4.")
        width, height = _DIMENSIONS.get(str(step.params.get("aspect_ratio", "1:1")), (1024, 1024))

        request_ids: list[str] = []
        for variant in range(1, count + 1):
            image_bytes, media_type, request_id = self._generate_one(
                prompt=step.prompt,
                width=width,
                height=height,
            )
            suffix = ".png" if media_type == "image/png" else ".jpg"
            output_path = self._temp_dir / f"{step.step_id}-{variant}{suffix}"
            output_path.write_bytes(image_bytes)
            step.assets.append(Asset(url=output_path.resolve().as_uri(), media_type=media_type))
            if request_id:
                request_ids.append(request_id)

        step.provider_payload = {
            "cloudflare": {
                "model": CLOUDFLARE_IMAGE_MODEL,
                "request_ids": request_ids,
            }
        }
        return step

    def _generate_one(self, *, prompt: str, width: int, height: int) -> tuple[bytes, str, str]:
        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{self.account_id}/ai/run/{CLOUDFLARE_IMAGE_MODEL}"
        )
        try:
            response = self._client.post(
                url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                files={
                    "prompt": (None, prompt),
                    "width": (None, str(width)),
                    "height": (None, str(height)),
                },
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            result = payload.get("result") or payload
            encoded = result.get("image") if isinstance(result, dict) else None
            if not isinstance(encoded, str) or not encoded:
                raise ProviderError("Cloudflare completed without an encoded image.")
            image_bytes = base64.b64decode(encoded, validate=True)
        except ProviderError:
            raise
        except (binascii.Error, ValueError) as exc:
            raise ProviderError("Cloudflare returned an invalid image payload.") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Cloudflare image request failed: {exc}") from exc

        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            media_type = "image/png"
        elif image_bytes.startswith(b"\xff\xd8\xff"):
            media_type = "image/jpeg"
        else:
            raise ProviderError("Cloudflare returned an unsupported image format.")
        return image_bytes, media_type, response.headers.get("cf-ray", "")

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
        shutil.rmtree(self._temp_dir, ignore_errors=True)
