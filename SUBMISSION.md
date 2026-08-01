# ProofStudio — Devpost Submission Draft

> Submission status: **live technical gate passed; not ready to submit until
> the deployment and video placeholders are replaced.**

Submission deadline: August 3, 2026 at 5:00 PM ET.

## Project name

ProofStudio

## Tagline

Turn campaign briefs into durable, verifiable generative media runs.

## Links

- Working application: **[REQUIRED: public deployment URL]**
- Source repository: <https://github.com/NikitaGavrilenko/backblaze-generative-media-2026>
- Demo video: **[REQUIRED: public video URL, approximately three minutes]**

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

- Run ID: `67c1cbf8-1e4a-4297-aac0-59adbc3cb666`
- Generated and stored assets: 2
- Canonical manifest hash:
  `e782450187968d1a0c010ca1115944bb528c2cb7612fc60d42ba466c361853f0`
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

- [ ] Public app URL opens without authentication.
- [ ] Health response reports fully configured Live Mode.
- [x] Exact provider and model above match the successful run manifest.
- [ ] Two public application asset URLs backed by private B2 objects work in an
  incognito browser.
- [ ] The application manifest URL works and its hash matches the UI.
- [ ] Verification succeeds after a fresh application restart.
- [ ] GitHub repository contains setup instructions and no secrets.
- [ ] Repository is public, or the private repository grants `b2genblaze`
  contributor access for judging.
- [ ] Demo video shows the real app working in approximately three minutes.
- [ ] Every placeholder in this document has been removed.
