"""Public API schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class RunStatus(StrEnum):
    QUEUED = "queued"
    GENERATING = "generating"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"


class CampaignBrief(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    audience: str = Field(min_length=2, max_length=240)
    message: str = Field(min_length=3, max_length=500)
    tone: str = Field(min_length=2, max_length=120)
    visual_constraints: list[str] = Field(default_factory=list, max_length=12)
    aspect_ratio: str = Field(default="1:1", pattern=r"^(1:1|4:5|16:9|9:16)$")

    @field_validator("visual_constraints")
    @classmethod
    def normalize_constraints(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(normalized))


class MediaAsset(BaseModel):
    id: str
    variant: int
    url: str
    storage_key: str
    mime_type: str
    sha256: str


class GenerationRun(BaseModel):
    id: str
    campaign: CampaignBrief
    status: RunStatus
    provider: str
    model: str
    prompt: str
    manifest_url: str
    manifest_hash: str
    verified: bool
    demo_mode: bool
    assets: list[MediaAsset]
    parameters: dict[str, object] = Field(default_factory=dict)
    provider_job_ids: list[str] = Field(default_factory=list)
    manifest_storage_key: str | None = None
    idempotency_key: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None


class VerificationResult(BaseModel):
    run_id: str
    verified: bool
    checked_assets: int
    errors: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    mode: str
    genblaze: str
    storage: str
    live_configured: bool
    missing_settings: list[str] = Field(default_factory=list)
