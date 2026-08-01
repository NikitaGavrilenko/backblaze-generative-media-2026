# ProofStudio — Devpost Submission Draft

> Submission status: **public live technical gate passed and the demo video is
> rendered locally; upload it, add the public URL, and complete the final Devpost
> form before submission.**

Submission deadline: August 3, 2026 at 5:00 PM ET.

## Project name

ProofStudio

## Tagline

Turn campaign briefs into durable, verifiable generative media runs.

## Links

- Working application: <https://proofstudio-h3ds.onrender.com>
- Source repository: <https://github.com/NikitaGavrilenko/backblaze-generative-media-2026>
- Demo video: **[UPLOAD REQUIRED: `submission-assets/video/proofstudio-demo.mp4`]**

## Inspiration

Creative teams increasingly rely on generated media, but the final file often
loses the evidence needed to answer basic questions: Which model created it?
Which prompt and parameters were used? Is the file still identical to the
original output? Will its provider URL still work next week?

ProofStudio treats provenance and durable storage as part of generation rather
than cleanup work performed afterward.

## What it does

ProofStudio accepts a structured campaign brief and produces two image
variants. A single Genblaze pipeline records the provider, model, prompt,
parameters, provider job identifier, asset hashes, and canonical manifest.
Generated media and manifests are persisted to Backblaze B2. The gallery shows
durable URLs and can re-verify both the stored manifest and every asset's
SHA-256 hash.

The application includes a clearly labelled offline Demo Mode. Live Mode is
enabled only when all required server-side B2 and provider settings are
present.

## How we built it

- FastAPI serves the API and compact responsive interface as one deployable
  application.
- Pydantic models validate campaign briefs, run records, health responses, and
  verification results.
- `genblaze-core==0.3.8` orchestrates generation and creates the provenance
  manifest.
- A project-owned Genblaze `SyncProvider` adapter connects Cloudflare Workers AI.
- `genblaze-s3==0.3.6` and `ObjectStorageSink` persist content-addressed assets
  and manifests to Backblaze B2.
- A small JSON run index is mirrored to B2, avoiding a database while allowing
  gallery recovery after an application restart.
- Render configuration keeps all credentials server-side. The local cache may
  be ephemeral because authoritative run records and media are restored from B2.

## Providers and models

- Provider: Cloudflare Workers AI
- Model: `@cf/black-forest-labs/flux-2-klein-4b`
- Generation settings: two image variants; campaign-selected aspect ratio

Verified live gate on August 1, 2026:

- Run ID: `ffa93c15-2044-4e68-afde-fb002d7af042`
- Generated and stored assets: 2
- Canonical manifest hash:
  `eb24129005ef3245778ceac5f0a2c61e6aeb4b515b47d0aa6645a432a96da481`
- Public manifest:
  <https://proofstudio-h3ds.onrender.com/api/storage/proofstudio/manifests/ffa93c15-2044-4e68-afde-fb002d7af042.json>
- Public assets:
  <https://proofstudio-h3ds.onrender.com/api/storage/proofstudio/assets/25/88/2588c9204f83c58f1205af72eab0c4d37a2c356f5026d6a9b965a7ded33072f5.jpg>
  and
  <https://proofstudio-h3ds.onrender.com/api/storage/proofstudio/assets/30/e2/30e2cc2c358c756392a6f58e692cb59c588a1df7e0825968e6f2e32d79d93ee0.jpg>
- B2 asset and manifest verification: passed

## How ProofStudio uses Genblaze

Genblaze is the execution and provenance boundary, not a metadata label added
after generation. The live request is a Genblaze `Pipeline` step using the
project-owned Cloudflare Workers AI provider. `ObjectStorageSink` transfers
outputs to B2, calculates and records content hashes, writes the canonical
manifest, and replaces temporary provider files with durable B2 URLs.

## How ProofStudio uses Backblaze B2

B2 is the durable system of record for generated media, canonical manifests,
and gallery run metadata. Assets use content-addressed keys for deduplication.
The verification endpoint downloads the stored manifest and assets from B2,
checks the canonical manifest hash, and recalculates each asset's SHA-256. The
bucket remains private; a restricted application endpoint exposes only assets
and manifests belonging to recorded runs without leaking B2 credentials.

## Challenges

The difficult part was making retries and storage behavior honest for
quota-backed generation. A provider success followed by a storage failure must
not silently become another request. ProofStudio uses idempotency keys, records
provider request identifiers, and separates Demo Mode from Live Mode so an
offline fixture can never be presented as a real AI output.

## Accomplishments

- One application covers structured input, generation, durable storage,
  provenance display, history, and verification.
- Assets and manifests are tamper-detectable with SHA-256 and Genblaze's
  canonical hash.
- Credentials remain server-side and secret scans run before publication.
- The deterministic demo supports development without provider spend.

## What we learned

Provenance is most useful when it is created inside the pipeline and stored
beside the asset. Durable URLs, explicit failure states, and idempotency are as
important as model quality when generated media becomes part of a real
campaign workflow.

## What's next

- Persist provider submission state before polling for stronger crash recovery.
- Stream generation and storage progress to the interface.
- Add a controlled retry action for partial failures.
- Add a second provider and policy-driven fallback after the single-provider
  technical gate is stable.

## Final evidence checklist

- [x] Public app URL opens without authentication.
- [x] Health response reports fully configured Live Mode.
- [x] Exact provider and model above match the successful run manifest.
- [x] Two public application asset URLs backed by private B2 objects work in an
  incognito browser.
- [x] The application manifest URL works and its hash matches the UI.
- [x] Verification succeeds after a fresh application restart.
- [x] GitHub repository contains setup instructions and no secrets.
- [x] Repository is public, or the private repository grants `b2genblaze`
  contributor access for judging.
- [x] Demo video shows the real app working in under three minutes.
- [ ] Every placeholder in this document has been removed.
