# TRIDENT AI contributor guidance

## Product and reference boundaries

- Treat the authorized Intelligent Workspace as the product's primary surface. Nova is one Workspace module, alongside Knowledge, Memory, Files, Artifacts, Activity, Command, and Settings.
- Preserve the existing TRIDENT visual identity and responsive system. Use `docs/vision/TRIDENT_DEFINITIVE_INTERFACE_REFERENCE.md` and its approved reference asset as visual guidance; do not invent product capabilities to imitate a mockup.
- Read `docs/TRIDENT_POST_GOLD_ROADMAP.md`, `docs/engineering-standards.md`, and relevant architecture/ADR documents before material changes.
- `docs/releases/trident-ai-v1.0.0.md` and tag `trident-ai-v1.0.0` identify Gold v1.0.0. The repository contains `docs/rules-bible.md`, but it does not identify itself as the canonical TRIDENT Bible v3.0. Do not claim that the canonical v3.0 document is present or invent its contents; flag the gap in reviews that need it.
- Prefer additive, scoped changes. Do not reconstruct the application or expand into PRO/NOVA-only capabilities ahead of the roadmap.

## Architecture and security

- The frontend is React/Vite and consumes versioned APIs through `frontend/src/services/api.js`. The backend is a FastAPI modular monolith. Preserve module boundaries and use existing contracts before proposing new ones.
- The server is authoritative for identity, authorization, tenancy, entitlements, and provider access. Never use frontend state as an authorization control.
- Keep Workspace/tenant scope explicit. Do not import another module's persistence internals or access databases/providers directly from the browser.
- Never inspect, print, copy, commit, or bundle secrets, credentials, production data, or private runtime files. Do not connect to production or VPS hosts from development tasks.
- Do not run deployments, migrations against shared systems, service changes, or provider calls unless a separate task explicitly authorizes them.
- Keep failures visible and fail closed. Do not fabricate metrics, availability, status, or generated content. Treat loading, empty, error, and unavailable states distinctly.
- Preserve accessibility, keyboard behavior, reduced-motion support, responsive layouts, and the approved visual language.

## Change and validation workflow

- Inspect `git status` before editing. Do not overwrite or stage unrelated/pre-existing work. Work on a dedicated feature branch; never push directly to `main` or `trident-ai`.
- Keep pull requests small and reviewable. Include the user-visible behavior, tests, risks, and rollback notes. Never enable automatic merge or describe a change as Founder Approved.
- Frontend checks: `npm test`, `npm run lint`, and `npm run build` from `frontend/` when dependencies are available. Add targeted tests for changed contracts and keep them in the package test script.
- Backend checks when backend code changes: run the relevant unit/integration suite, compile checks, dependency checks, and migrations only against disposable test databases configured by the project CI.
- Always run `git diff --check` and inspect the final diff and staged path list before committing.
- CI is defined in `.github/workflows/quality.yml`; it tests and builds but does not authorize or perform production deployment.

## Canonical references currently available

- Post-Gold roadmap: `docs/TRIDENT_POST_GOLD_ROADMAP.md`.
- Gold release record: `docs/releases/trident-ai-v1.0.0.md`; immutable tag: `trident-ai-v1.0.0`.
- Rules summary: `docs/rules-bible.md` (version/canonical status not established in this repository).
- Architecture: `docs/architecture/target-architecture.md`, `docs/architecture/trident-ai-transition.md`, and `docs/decisions/`.
- Approved visual reference: `docs/vision/TRIDENT_DEFINITIVE_INTERFACE_REFERENCE.md` and `docs/vision/assets/trident-definitive-interface-reference.png`.
