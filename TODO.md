# ProofStudio — Remaining Work

Last updated: August 1, 2026

## 1. Required user setup

These steps require access to external accounts and must be completed by the
project owner.

### Backblaze B2

- [ ] Create or sign in to a Backblaze account.
- [ ] Enable B2 Cloud Storage.
- [ ] Create a dedicated bucket for ProofStudio demo assets.
- [ ] Record the exact bucket name.
- [ ] Record the bucket region from its S3 endpoint.
- [ ] Create a bucket-scoped Application Key.
- [ ] Grant the key read and write access to the ProofStudio bucket.
- [ ] Copy the `keyID` and `applicationKey` when the key is created.

Recommended bucket configuration:

- private bucket access; ProofStudio serves recorded assets through its public
  application endpoint;
- no customer, private, or personally identifiable data;
- no Object Lock for the MVP;
- a dedicated bucket rather than an existing personal bucket.

Official guide:
<https://www.backblaze.com/docs/en/cloud-storage-get-started-with-a-backblaze-integration>

### Media provider

- [ ] Create or sign in to a GMI Cloud account.
- [ ] Create or select an organization.
- [ ] Confirm that image-generation models and credits are available.
- [ ] Open `Organization Settings -> API Keys`.
- [ ] Create an API key with the `ie_model` scope.
- [ ] Copy the API key when it is created.

Official guide:
<https://docs.gmicloud.ai/api-reference/introduction>

If GMI Cloud is unavailable, blocked, or unsuitable, stop before purchasing
credits and select another Genblaze-supported image provider.

### Local environment

- [x] Copy `.env.example` to `.env`.
- [ ] Add the Backblaze and provider credentials to `.env`.
- [ ] Do not send credentials through chat.
- [ ] Do not commit `.env`.
- [ ] Tell the development agent that setup is ready without sharing key values.

Required variables:

```dotenv
B2_KEY_ID=
B2_APP_KEY=
B2_BUCKET=
B2_REGION=
GMI_API_KEY=
```

## 2. Live integration work

Complete after the required credentials are available.

- [x] Install the pinned `genblaze-s3` package.
- [x] Install the pinned `genblaze-gmicloud` package.
- [ ] Validate B2 authentication and bucket access.
- [ ] Validate the provider API key and list available image models.
- [ ] Select one supported image model with acceptable cost and latency.
- [ ] Run one low-cost image generation request.
- [ ] Persist the generated asset through `ObjectStorageSink`.
- [ ] Persist the canonical provenance manifest to B2.
- [ ] Confirm that the application-backed asset URL is durable and publicly
  accessible while the B2 bucket remains private.
- [ ] Verify the asset SHA-256 and Genblaze manifest.
- [ ] Record the working package, provider, and model versions.

Technical gate:

```text
GMI Cloud -> Genblaze -> Backblaze B2 -> manifest -> verification
```

Do not continue to optional features until this gate passes.

## 3. Replace the demo pipeline

- [x] Add a live pipeline implementation behind the existing pipeline interface.
- [x] Keep Demo Mode available as an explicit fallback.
- [x] Configure one live request to generate two image variants from one structured brief.
- [ ] Return honest run statuses while generation is in progress.
- [ ] Save provider job identifiers before polling.
- [ ] Avoid duplicate paid generation after polling or storage failures.
- [x] Preserve the current idempotency behavior.
- [x] Store campaign metadata and run history in B2.
- [x] Load previous runs after application restart.
- [x] Display durable B2 asset URLs in the gallery.
- [x] Display provider, model, prompt, parameters, hashes, and manifest links.

## 4. Reliability and tests

- [ ] Test an invalid provider key.
- [ ] Test an invalid B2 key.
- [ ] Test provider timeout behavior.
- [ ] Test provider success followed by B2 upload failure.
- [ ] Test a missing or inaccessible provider output URL.
- [x] Test a repeated request with the same idempotency key.
- [x] Test a modified asset that fails SHA-256 verification.
- [x] Ensure application responses never contain API keys or authorization headers.
- [ ] Add bounded retries only for temporary failures.
- [ ] Add a visible partial-failure state.

## 5. Product and interface

- [ ] Replace demo SVG fixtures with live generated images.
- [ ] Add visible `generating`, `storing`, `completed`, and `failed` states.
- [ ] Add a retry action for failed runs.
- [x] Add a clear distinction between Demo Mode and Live Mode.
- [ ] Confirm that the updated main workflow works on a mobile-sized screen.
- [x] Keep all UI copy and public artifacts in English.
- [x] Remove any unnecessary personal information from public artifacts.

Deferred until the core flow is stable:

- automated brand scoring;
- multiple providers and provider fallback;
- video or audio generation;
- semantic search;
- campaign ZIP exports;
- authentication and multi-tenant workspaces.

## 6. Deployment and release

- [x] Select a deployment platform that supports Python 3.11+ (Render).
- [x] Configure secret placeholders through the deployment platform, not source files.
- [ ] Deploy the FastAPI application.
- [ ] Verify the application from a private/incognito browser session.
- [ ] Confirm that generated files remain available after application restart.
- [x] Add a health check for the app and live provider/storage configuration.
- [x] Review Git history for accidentally committed secrets.
- [x] Create a clean initial commit.
- [x] Push the repository to GitHub.

## 7. Demo and documentation

- [ ] Update the README with the actual provider and model.
- [x] Document the B2 object layout implemented by the live pipeline.
- [x] Add an architecture diagram.
- [ ] Save one successful pre-generated demo run.
- [ ] Save one controlled failure example.
- [x] Write a demo script shorter than three minutes.
- [ ] Record the real working application.
- [ ] Capture screenshots of generation, provenance, history, and verification.
- [ ] Ensure every claimed feature is visible and implemented.
- [ ] Keep all documentation and demo materials in English.

## Current verified state

- [x] Git repository initialized.
- [x] Python environment created with `uv`.
- [x] `genblaze-core==0.3.8` installed and pinned.
- [x] Optional integrations pinned to `genblaze-s3==0.3.6` and
  `genblaze-gmicloud==0.3.5`.
- [x] Local Genblaze manifest smoke test passes.
- [x] FastAPI API implemented.
- [x] Responsive web interface implemented.
- [x] Structured campaign brief validation implemented.
- [x] Two clearly labelled local demo assets are generated.
- [x] Local JSON run history implemented.
- [x] Idempotency behavior implemented.
- [x] SHA-256 tamper detection implemented.
- [x] Browser flow checked without console errors.
- [x] Lint passes.
- [x] Eight automated tests pass after live-mode and manifest verification coverage.
- [x] GitHub Actions passes on the public repository.
- [x] Public project artifacts contain no Cyrillic text.
