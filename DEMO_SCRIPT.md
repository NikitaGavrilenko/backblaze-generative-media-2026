# ProofStudio — Demo Script

Target length: 2 minutes 40 seconds. Record the real deployed application in a
private/incognito browser window. Do not show dashboards, API keys, environment
variables, browser autofill, or personal account details.

## 0:00–0:20 — The problem

> Generated campaign assets often arrive as temporary links with no durable
> record of the model, prompt, parameters, or original file hash. ProofStudio
> makes that evidence part of the generation workflow.

Show the ProofStudio landing page and the Live Mode indicator.

## 0:20–0:50 — Structured brief

Show the campaign name, audience, message, tone, constraints, and aspect ratio.

> The input is structured and validated before any external generation begins. One
> idempotency key represents this request, preventing accidental duplicate
> generation from repeated submissions.

Submit the brief once.

## 0:50–1:30 — Real generation and durable output

Wait for the two real image variants to appear.

> Genblaze sends the request to FLUX.2 klein 4B through Cloudflare Workers AI.
> Its storage sink transfers both outputs to Backblaze B2, replaces temporary
> provider URLs with durable B2 URLs, calculates SHA-256 hashes, and writes the
> canonical provenance manifest.

Show both assets, provider, model, parameters, provider job ID, and manifest
hash. Open one asset and the manifest in new tabs to demonstrate durable URLs.

## 1:30–2:05 — Verification

Click **Verify assets**.

> Verification downloads the stored evidence from B2, checks the canonical
> manifest hash, recalculates each asset's SHA-256, and reports whether the
> stored files still match the original generation run.

Pause on the Verified result.

## 2:05–2:30 — Durable history

Refresh the page or restart the application before recording this segment, then
show the run in Previous Runs.

> B2 also stores the gallery metadata, so ProofStudio can rebuild its local run
> index after a restart without adding a database or worker queue.

## 2:30–2:40 — Close

> ProofStudio turns a campaign brief into two useful assets and a durable chain
> of evidence: provider, Genblaze, Backblaze B2, manifest, and verification.

End on the verified gallery view and project name.
