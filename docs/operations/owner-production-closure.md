# TRIDENT AI owner production closure

This runbook is the smallest remaining privileged/external procedure. It never
rewrites Genesis, creates an identity from an email, or treats a client claim as
authorization. Replace bracketed values only with owner-approved values.

## 1. Required owner inputs

- `DOMAIN`: the production hostname whose DNS and certificate the owner controls.
- OIDC issuer URL, API audience and public client ID. The current standards
  adapter uses Authorization Code + PKCE without a client secret, so the
  registration must allow a **public client**. A provider requiring a
  confidential-client secret needs a reviewed adapter extension before launch.
- Provider registration:
  - redirect URI: `https://DOMAIN/api/v1/session/callback`;
  - post-logout URI: `https://DOMAIN/`;
  - scopes: `openid profile`;
  - response/grant: Authorization Code with PKCE `S256`;
  - ID-token claims: `iss`, `aud`, `sub`, `iat`, `exp`, `nonce`;
  - asymmetric signing algorithm from the explicit allowlist (default `RS256`).
- The real OIDC `subject` after the creator's first successful login.
- A durable owner-controlled approval reference for Organization claim and a
  separate reference for Founder entitlement assignment.
- Service account/group and final immutable release root.

Issuer discovery must publish matching `issuer`, HTTPS authorization/token/JWKS
endpoints and optionally an HTTPS end-session endpoint. `TRIDENT_OIDC_AUDIENCE`
is the audience for bearer API credentials; ID tokens are independently checked
against `TRIDENT_OIDC_CLIENT_ID`.

## 2. Build and stage

Run from a clean `trident-ai` checkout at the approved SHA:

```bash
git fetch origin
git switch trident-ai
git pull --ff-only origin trident-ai
npm ci --prefix frontend
npm run build --prefix frontend
venv/bin/python -m app.operations.artifacts frontend/dist > /tmp/trident-frontend-manifest.json
venv/bin/python -m app.operations.preflight
```

The browser uses the relative `/api` default. Do not set a secret or OIDC token
in a `VITE_*` variable. Copy the tested source and `frontend/dist` into an
immutable release directory; keep `.env`, PostgreSQL, originals and Chroma out
of the web root. Preserve current runtime data paths in the production
EnvironmentFile.

## 3. DNS and TLS

Create an `A` record for `DOMAIN` pointing to `93.127.139.131`. Add `AAAA` only
if IPv6 routing is explicitly configured. Wait until public DNS resolves to the
expected address.

Render `deploy/nginx/trident-ai-http-bootstrap.conf.template`, install it through
the authorized privileged process, run `nginx -t`, then reload Nginx. With the
ACME webroot present, issue the certificate for the exact domain:

```bash
sudo install -d -m 0755 /var/www/letsencrypt
sudo certbot certonly --webroot -w /var/www/letsencrypt -d "$TRIDENT_DOMAIN"
sudo certbot renew --dry-run
```

Render `deploy/nginx/trident-ai.conf.template` with the exact domain and release
root. Validate and reload. Verify HTTPS, assets, SPA fallback, `/api/health/*`,
OIDC redirect and absence of 502 before enabling HSTS. No WebSocket is currently
required; API proxy timeouts cover the synchronous message path.

Rollback: retain the previous Nginx site and release directory, restore the
previous enabled-site symlink, run `nginx -t`, reload, and leave database/data
untouched. Never rollback schema by destructive downgrade.

## 4. Runtime environment and services

Create `/etc/trident/trident-ai.env` mode `0600`, owned by the service identity,
from `.env.example`. At minimum set the real database URL, absolute existing
document/vector paths, build SHA, domain-derived redirect URIs, OIDC values and
backend AI provider credential. Use:

```text
TRIDENT_ENV=production
TRIDENT_DEBUG=false
TRIDENT_SECURITY_MODE=oidc
TRIDENT_SESSION_COOKIE_SECURE=true
TRIDENT_CORS_ALLOWED_ORIGINS=
```

Same-origin production needs no CORS origin. Render the two systemd templates
with the approved service user/group and release root. After backup, schema
inspection and dry review, run `alembic upgrade head` as a one-shot task. Start
the backend unit and verify local live/ready/build before switching traffic.
Only then stop the known tmux backend. Start the Knowledge worker after its
access to the same originals/vector paths is verified. Stop/disable Vite only
after Nginx serves the immutable frontend successfully.

Expected backend command:

```bash
RELEASE_ROOT/venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 --proxy-headers \
  --forwarded-allow-ips=127.0.0.1
```

## 5. Controlled Organization and Founder claims

First complete a real browser login. The verified callback creates the internal
User and persisted `(issuer, subject)` mapping but grants no Membership. Set the
values without placing the subject in shell history:

```bash
export TRIDENT_OIDC_ISSUER='https://OWNER-APPROVED-ISSUER'
read -r -p 'Verified OIDC subject: ' TRIDENT_OIDC_SUBJECT
export TRIDENT_LEGACY_ORG='00000000-0000-4000-8000-000000000001'
```

Run the read-only Organization readiness check, then the controlled one-time
claim:

```bash
venv/bin/python -m app.tenancy.bootstrap \
  --issuer "$TRIDENT_OIDC_ISSUER" --subject "$TRIDENT_OIDC_SUBJECT"

venv/bin/python -m app.tenancy.bootstrap \
  --issuer "$TRIDENT_OIDC_ISSUER" --subject "$TRIDENT_OIDC_SUBJECT" \
  --apply --approval-reference 'OWNER-ORG-APPROVAL-[REFERENCE]'
```

Verify the `owner` Membership and immutable `organization.legacy_claimed` event.
Then dry-run and assign the reserved entitlement:

```bash
venv/bin/python -m app.governance.founder \
  --issuer "$TRIDENT_OIDC_ISSUER" --subject "$TRIDENT_OIDC_SUBJECT" \
  --organization-id "$TRIDENT_LEGACY_ORG"

venv/bin/python -m app.governance.founder \
  --issuer "$TRIDENT_OIDC_ISSUER" --subject "$TRIDENT_OIDC_SUBJECT" \
  --organization-id "$TRIDENT_LEGACY_ORG" --apply \
  --approval-reference 'OWNER-FOUNDER-APPROVAL-[REFERENCE]'
```

Verify exactly one active `ecosystem.full_access=1` grant with source `founder`,
no expiry, plus `founder.entitlement_granted` in the immutable audit chain.
Logout/login again to refresh the entry context. Re-running either apply command
for the same owner is idempotent; conflicting identities fail closed.

## 6. Closure checks

```bash
curl --fail "https://$TRIDENT_DOMAIN/api/health/live"
curl --fail "https://$TRIDENT_DOMAIN/api/health/ready"
curl --fail "https://$TRIDENT_DOMAIN/api/health/build"
curl -I "https://$TRIDENT_DOMAIN/"
systemctl --no-pager --full status trident-backend trident-knowledge-worker nginx
```

Confirm OpenAPI is absent in production, unauthenticated business API returns
401 rather than data, authenticated entry selects only the claimed Organization,
cross-Workspace tests remain green, certificate renewal is scheduled, and logs
contain request IDs but no tokens or document content. Only after these checks
may the owner authorize the separate final release/tag operation.
