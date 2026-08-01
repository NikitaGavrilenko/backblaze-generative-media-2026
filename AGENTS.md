# Project Instructions

## Language and privacy

- All source code, comments, documentation, UI copy, screenshots, demo scripts,
  repository metadata, and submission materials must be written in English.
- Do not include the developer's location, residency, nationality, university,
  local usernames, or other personal details in public project artifacts unless
  they are explicitly required.
- Do not make false statements about identity, eligibility, ownership, or legal
  compliance.

## Engineering priorities

- Build the smallest working vertical slice before adding optional features.
- The first technical gate is:
  `provider -> Genblaze -> durable storage -> manifest -> verification`.
- Keep Genblaze and provider versions pinned after the first successful run.
- Keep all credentials server-side and out of Git.
- Prefer Pydantic models and structured JSON over free-form parsing.
- Do not add a database, worker queue, multi-agent system, or separate frontend
  deployment until the MVP proves that it needs one.
- Demo fixtures must be clearly labelled as demo data.

