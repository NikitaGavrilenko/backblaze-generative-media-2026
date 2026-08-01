# ProofStudio

ProofStudio turns a structured campaign brief into traceable generative media
runs. Genblaze orchestrates generation and provenance, while Backblaze B2 is the
durable system of record for assets and manifests.

## Current status

The project is in the technical-spike phase. The first gate is a verified
end-to-end run:

```text
provider -> Genblaze -> Backblaze B2 -> provenance manifest -> SHA-256 verification
```

Do not build optional product features until this path works.

See [TODO.md](TODO.md) for the current implementation checklist and required
external account setup.

## MVP

- Create a campaign from a structured brief.
- Generate two image variants through one Genblaze provider.
- Store assets and provenance manifests in Backblaze B2.
- Display run status, durable asset URLs, provider, model, parameters, and hashes.
- Verify manifest integrity.
- Retry a failed run without silently creating duplicate paid generations.
- Browse previous runs after a page reload.

## Architecture

```text
Browser
  |
  v
FastAPI application
  |-- campaign and run API
  |-- compact server-rendered web UI
  |-- run repository
  `-- Genblaze pipeline
          |-- one image provider
          `-- ObjectStorageSink
                    |
                    v
              Backblaze B2
              |-- assets
              `-- manifests
```

The MVP intentionally uses one deployable application. A separate frontend,
database, worker queue, and multiple providers are deferred until the core flow
is stable.

## Local setup

Requirements:

- Python 3.11, 3.12, or 3.13
- `uv`

```powershell
uv sync --extra dev
Copy-Item .env.example .env
uv run python scripts/quickstart_local.py
```

The local quickstart uses no API keys and makes no external generation calls. It
only verifies that the installed Genblaze version can build and validate a
canonical provenance manifest.

## Credentials

Real generation and B2 persistence will require:

- a bucket-scoped Backblaze B2 application key;
- one supported media provider API key.

Never commit `.env` or expose credentials in browser code, logs, screenshots, or
demo materials.

## Development

```powershell
uv run ruff check .
uv run pytest
uv run uvicorn app.main:app --reload
```

## Scope deliberately deferred

- automated brand scoring;
- multiple providers and fallback chains;
- video and audio generation;
- semantic search;
- ZIP campaign exports;
- thumbnails and cost analytics;
- authentication, billing, RBAC, and multi-tenant workspaces.
