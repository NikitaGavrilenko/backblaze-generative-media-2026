import base64
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import httpx
import pytest
from genblaze_core import Modality, StepBuilder
from genblaze_core.exceptions import ProviderError

from app.providers.cloudflare import CLOUDFLARE_IMAGE_MODEL, CloudflareImageProvider

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"test-image"


def path_from_file_url(url: str) -> Path:
    return Path(url2pathname(urlparse(url).path))


def build_step(*, count: int = 2, aspect_ratio: str = "4:5"):
    return (
        StepBuilder("cloudflare-workers-ai", CLOUDFLARE_IMAGE_MODEL)
        .prompt("An editorial product photograph")
        .modality(Modality.IMAGE)
        .params(number_of_images=count, aspect_ratio=aspect_ratio)
        .build()
    )


def test_cloudflare_provider_returns_local_assets_without_live_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"success": True, "result": {"image": base64.b64encode(PNG_BYTES).decode()}},
            headers={"cf-ray": "test-ray"},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = CloudflareImageProvider(
        account_id="account-id",
        api_token="secret-token",
        http_client=client,
    )
    temp_dir = provider._temp_dir

    try:
        result = provider.generate(build_step())

        assert len(requests) == 2
        assert len(result.assets) == 2
        assert all(asset.media_type == "image/png" for asset in result.assets)
        assert all(path_from_file_url(asset.url).is_file() for asset in result.assets)
        assert result.provider_payload["cloudflare"]["request_ids"] == ["test-ray", "test-ray"]
        assert all(
            request.headers["authorization"] == "Bearer secret-token" for request in requests
        )
        assert all(
            b'name="width"' in request.content and b"768" in request.content
            for request in requests
        )
        assert all(
            b'name="height"' in request.content and b"960" in request.content
            for request in requests
        )
    finally:
        provider.close()
        client.close()

    assert not temp_dir.exists()


def test_cloudflare_provider_rejects_invalid_response() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"success": True, "result": {}})
        )
    )
    provider = CloudflareImageProvider(
        account_id="account-id",
        api_token="secret-token",
        http_client=client,
    )

    try:
        with pytest.raises(ProviderError, match="without an encoded image"):
            provider.generate(build_step(count=1))
    finally:
        provider.close()
        client.close()
