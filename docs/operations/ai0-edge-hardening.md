# AI-0 edge and runtime hardening plan

## Observed development topology

At the Genesis freeze, Nginx listens on public HTTP port 80, proxies `/` to a
Vite development server on `127.0.0.1:10032`, and proxies `/api/` to FastAPI on
`127.0.0.1:8000`. The frontend systemd unit runs Vite. The backend systemd unit
is inactive while a manually supervised backend process owns port 8000.

This topology keeps the approved demo reachable but is not a production release
topology. Internet scan attempts are already visible in the frontend service
logs. AI-0 does not hide this condition behind fake authentication.

## Privileged transition required

The deployment owner must perform the following as one reviewed, reversible
change when privileged access and a maintenance window are available:

1. copy the validated `frontend/dist` output to an immutable release directory
   outside the source checkout;
2. serve that directory directly from Nginx with SPA `try_files` behavior;
3. keep only `/api/` proxied to FastAPI;
4. add, test and retain at minimum:
   - `X-Content-Type-Options: nosniff`;
   - `X-Frame-Options: DENY` (or an equivalent CSP `frame-ancestors` policy);
   - `Referrer-Policy: strict-origin-when-cross-origin`;
   - an explicit `Permissions-Policy`;
5. set an upload body limit compatible with the documented 20 MiB product
   limit while leaving FastAPI validation authoritative;
6. run `nginx -t`, reload rather than restart, then verify the landing page,
   static assets, API proxy and absence of 502 responses;
7. stop and disable the public Vite service only after static delivery passes;
8. return the backend to its systemd unit after stopping only the known manual
   process, then verify liveness and readiness.

Do not copy `.env`, Workspace originals or vector files into the web root.

## TLS activation

TLS waits for an owner-approved domain. After DNS is confirmed, issue a
certificate for that exact hostname, redirect HTTP to HTTPS, restrict protocols
and ciphers to the deployment policy, enable HSTS only after HTTPS is verified,
and test renewal. Never issue a certificate for an invented hostname or enable
HSTS on the current IP-only demo pre-emptively.

## Current access boundary

Until this transition plus AI-1/AI-2 is complete, the public address is a
non-sensitive development/demo endpoint. `/api/v1` remains anonymous by design
and must contain no private user or customer data.
