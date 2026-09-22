# Spatial experience / Nova images release gate

This supplements, not replaces, `owner-production-closure.md`. Preparation is
unprivileged. It must not run the previous frontend-only release script for this
combined frontend/backend change. No production migration or switch is included
in the preparation command.

## Exact revision and build

After lint, frontend/backend tests, browser fixtures and diff-check pass, commit
and push only this implementation on `trident-ai`. Run:

```bash
bash /home/administrator/ai-rag-chatbot/scripts/prepare_spatial_release.sh
```

It requires HEAD = origin/trident-ai, clean tracked files, the existing production
frontend environment file and retained rollback release
`4223cc2a4e7629283b1310e14a412db419baec6b`. It archives only committed source,
installs locked frontend dependencies in `/tmp`, builds with only the existing
public production frontend variables, strips inherited VITE preview variables,
checks the compiled mobile blur override, and creates a checksummed read-only
archive with source, frontend/dist, SHA and
asset manifest. No environment file is copied. `visual-review/`, browser
fixtures' output, secrets, local preview scripts and node_modules are excluded.
The archive directory is printed; the eventual immutable destination is
`/var/www/trident-ai/releases/<SHA>` and is **not** created by preparation.

## Controlled production gate — not executed during implementation

Use the existing runbook's privileged backup/staging/service/edge sequence.
Do not change DNS, Cloudflare, OAuth, Supabase, firewall or Founder provisioning.

1. Preserve the active frontend release, both available/enabled Nginx paths
   and their symlink topology outside Nginx include directories. Record the
   running backend revision, command, working directory and runtime data paths;
   preserve that source and dependency environment as well. Frontend rollback
   alone is insufficient when the schema/backend change.
2. Back up the database consistently using its actual configured engine and
   verify the backup before any migration. Include private documents, vectors
   and images (default document-root/nova-images) without serving them publicly.
   Do not print the production database URL or provider credential.
3. Stage the exact archive and install the pinned backend dependencies through
   the existing release procedure. `Pillow==12.3.0` is newly required. Do not
   serve source, environment files, originals or private images from the web root.
4. With the writer services controlled as in the existing runbook, apply only
   `0011_workspace_images` after confirming the production baseline is
   `0010_document_lifecycle`. The migration creates one new table and indexes;
   it does not rewrite existing records. Start the matching backend before
   directing traffic to the new frontend. Verify live/ready/build and the
   schema revision. No new systemd unit, external worker or queue is needed.
5. Keep `TRIDENT_IMAGE_PROVIDER=disabled` for the initial release acceptance
   window. This is the default, not an environment mutation performed here.
   Do not activate paid generation or introduce a key automatically. Activation
   requires an authorized backend credential/model, durable writable image
   storage, billing approval and a real provider smoke test.
6. Follow the existing Nginx test/reload switch; never leave backup vhosts in
   sites-enabled. Bound retries until the served index matches the **new**
   manifest, then request those exact JS/CSS assets. Check live/ready/build,
   unauthenticated 401 boundaries and normal OIDC redirect without logging tokens.
   Founder login then exercises Workspace, Nova, Knowledge, Memory, Files,
   Activity, Settings and Artifacts on an authorized account. SPA route HTTP 200
   is not proof of authenticated module behavior. Review logs for 5xx.

## Rollback boundary

Previous backend readiness requires schema 0010. Generic downgrade is therefore
not a safe rollback command and is refused. Before image activation, after
stopping writers and taking a verified backup, the release operator can reverse
**only an empty image table** using the new release's Alembic code:

```bash
venv/bin/python -m alembic -x allow_empty_image_downgrade=yes downgrade 0010_document_lifecycle
```

This explicit gate checks that the image table contains zero rows, then removes
only that table. Local tests prove existing Workspace rows survive. With even
one artifact it fails closed. Do not downgrade further or delete user creations
to force rollback. Once images have been activated and persisted, retain the
schema/data and prepare a compatible forward fix; any exceptional database
restore needs separate authorization and a preservation plan for later writes.
Restore the recorded backend source/runtime and previous frontend root, validate
Nginx, then reload and repeat health/assets/auth smoke checks. Never delete the
rollback release as part of deployment.

## Evidence and remaining acceptance

- Frontend unit/regression suites, API isolation/provider/migration tests and
  Chromium/WebKit fixtures are run locally, without production authentication.
- `frontend/tests/spatial-browser.mjs` supports phone, tablet and wide desktop;
  `TRIDENT_PLAYWRIGHT_MODULE` may point to an existing Playwright installation.
  All API calls are deterministic fixtures; external requests are blocked.
- Real iPhone Safari keyboard, safe areas during toolbar movement, perceived
  scroll fluidity, authenticated production flows and real billed image output
  remain separate acceptance checks. No FPS number or Founder approval is implied.

Founder visual validation: PENDING
