# Phase 1 Technical Specification — Production Foundation

- **Status:** Design approved; implementation requires explicit approval.
- **Date:** 2026-07-29
- **Scope:** configuration, lifecycle, migrations, testing, delivery pipeline,
  observability, API compatibility, and containerized local development.
- **Out of scope:** identity/tenancy, asynchronous ingestion, object storage,
  worker queues, and production infrastructure provisioning.

## Objectives and acceptance criteria

Phase 1 makes the prototype operable without changing product-domain behavior.
It establishes controls inherited by every later module. Completion requires:

1. A fresh environment starts from documented, non-secret configuration.
2. Missing or invalid production configuration fails startup safely.
3. Versioned migrations, not application startup, change schema.
4. Liveness, readiness, and build metadata are stable contracts.
5. Automated checks produce traceable release artifacts.
6. API error/versioning behavior is documented and tested.
7. Requests are diagnosable without logging secrets or customer content.
8. API and frontend run reproducibly in local containers.

## Proposed repository layout

```text
app/
  api/v1/                 # versioned routes and transport schemas
  core/                   # settings, lifecycle, logging, errors, telemetry
  database/               # engine/session setup, models, migration integration
  observability/          # metrics and tracing adapters
  services/               # domain orchestration
alembic/                  # immutable schema revisions
tests/{unit,integration,contract,e2e}/
docker/{api,compose}/
.github/workflows/
docs/
```

Route handlers must not own configuration, database lifecycle, or telemetry.

## Configuration management

### Principles

- A single typed settings model owns configuration; modules do not read process
  environment directly.
- Defaults are safe for local development only. Production values are explicit,
  validated, and fail closed.
- `.env.example` contains names and placeholders only; `.env` stays ignored.
- Settings are redacted in the one structured startup summary.
- Runtime settings are immutable; a configuration change creates a new process.

### Settings contract

| Group | Variables | Validation / behavior |
| --- | --- | --- |
| Runtime | `TRIDENT_ENV`, `TRIDENT_DEBUG`, `TRIDENT_LOG_LEVEL`, `TRIDENT_BUILD_SHA` | Environment is `development`, `test`, `staging`, or `production`. Debug is forbidden in production. |
| HTTP | `TRIDENT_HOST`, `TRIDENT_PORT`, `TRIDENT_ALLOWED_ORIGINS`, `TRIDENT_REQUEST_TIMEOUT_SECONDS` | Origins are explicit outside development; no wildcard with credentials. Timeout is positive and bounded. |
| Database | `TRIDENT_DATABASE_URL`, `TRIDENT_DATABASE_POOL_SIZE`, `TRIDENT_DATABASE_MAX_OVERFLOW`, `TRIDENT_DATABASE_CONNECT_TIMEOUT_SECONDS` | URL is mandatory outside tests; credentials are redacted; pool values are positive. SQLite is development/test only. |
| AI provider | `TRIDENT_OPENAI_API_KEY`, `TRIDENT_OPENAI_CHAT_MODEL`, `TRIDENT_OPENAI_EMBEDDING_MODEL`, `TRIDENT_PROVIDER_TIMEOUT_SECONDS` | Key is mandatory only when capability is enabled; model is explicit; calls have timeout. |
| Storage/index | `TRIDENT_DOCUMENTS_PATH`, `TRIDENT_VECTOR_DB_PATH` | Local paths are development/test only; production rejects them until Phase 3 managed stores. |
| Observability | `TRIDENT_OTEL_ENABLED`, `TRIDENT_OTEL_EXPORTER_OTLP_ENDPOINT`, `TRIDENT_METRICS_ENABLED`, `TRIDENT_SERVICE_NAME` | Name defaults to `trident-api`; exporter is required when tracing is enabled outside development. |

Secret fields use secret types, tests construct settings explicitly, and client
factories receive settings by dependency injection.

### Precedence and change policy

Precedence: process environment, explicitly selected development/test env file,
then safe code default. Production never reads a bundled or mounted `.env`.
`TRIDENT_ENV` is required in deployed environments and application behavior
never infers environment from hostnames. Any setting change includes validation,
documentation, `.env.example` where relevant, and restart/migration impact.
No public endpoint returns configuration; build health may return only safe
release metadata.

## Application lifecycle and health

### Lifecycle

FastAPI lifespan is the sole owner of startup/shutdown. Importing the app must
not make network calls, create schema, or initialize irreversible resources.
Startup: validate settings; configure structured telemetry/correlation; construct
client factories; run bounded readiness checks; then accept traffic. Shutdown:
stop accepting work, honor graceful termination, close pools/exporters, and
record a final event. Migrations and index rebuilds never run in lifecycle hooks.

### Endpoint contract

Operational endpoints are private-network or edge-protected and return neither
secret nor customer data.

| Endpoint | Success | Failure semantics | Consumer |
| --- | --- | --- | --- |
| `GET /health/live` | `200 {"status":"ok"}` | Does not probe dependencies. | Container restart decision. |
| `GET /health/ready` | `200 {"status":"ready","checks":{...}}` | `503` if settings or a required dependency is unavailable; only safe check states. | Load balancer/deployment gate. |
| `GET /health/build` | `200` with service, environment, build SHA, API version, migration revision | `503` only if metadata is unavailable. | Support diagnosis. |

Initial required readiness checks are configuration and relational database.
AI/vector dependencies are optional capability checks so a provider outage does
not cause a restart loop; affected routes return controlled dependency errors.

### Error contract

All product failures use this versioned safe envelope:

```json
{"error":{"code":"DEPENDENCY_UNAVAILABLE","message":"The requested capability is temporarily unavailable.","request_id":"01J..."}}
```

Codes are stable and machine-readable. Details are limited to validation errors;
they never expose stack traces, provider responses, credentials, prompts, or
document content. A global handler logs the internal cause under the request ID.

## Database migration strategy

### Tooling and ownership

Adopt Alembic with SQLAlchemy metadata. Revisions are version-controlled and
immutable. Application startup never creates schema; a singleton deployment job
using the release image runs migrations. The relational database is authoritative
and vector state is derived, outside relational migrations.

### Revision rules

- Revisions have ordered IDs, descriptive names, owner, and ADR/issue reference
  when architectural.
- Each has `upgrade` and, where safe, `downgrade`; irreversible operations state
  recovery and require backup evidence.
- Destructive work uses expand–migrate–contract: compatible structures,
  dual-read/write as required, resumable verified backfill, later removal.
- Revisions are deterministic, clean-environment repeatable, and make no
  external API calls.
- Database-specific locks, timeouts, and batch policy are documented before
  large-data operations.

### Deployment and tests

Build/scan immutable image, back up when risk requires it, run `upgrade head` as
a time-bounded singleton job, verify revision/readiness, then roll compatible
API instances. Prefer application rollback retaining expanded schema. Restore
data rather than blindly downgrade destructive changes. CI upgrades a clean
supported database to head, validates schema and representative flow, and also
tests upgrade from the prior release when one exists.

## Testing strategy

| Layer | Purpose | Dependencies | Examples |
| --- | --- | --- | --- |
| Unit | Pure domain/platform rules | Fakes only | settings validation, error mapping, correlation |
| Integration | Component boundaries | ephemeral DB, fake provider | sessions, migrations, readiness, validation |
| Contract | Public API drift | generated OpenAPI baseline | paths, envelopes, status codes |
| End-to-end | Composed critical flows | local stack, fake AI provider | startup, health, chat, documents |
| Security regression | Prevent known disclosure | isolated test data | no debug trace or secret leakage |

Tests are deterministic and parallel-safe. Network access is denied by default
in unit/integration tests; time, UUIDs, settings, provider clients, and sessions
are injectable. CI establishes a non-decreasing coverage baseline, but critical
paths always need explicit tests. Fixtures are synthetic; production content,
keys, and database dumps never enter source control or CI artifacts.

## CI/CD architecture

### CI

Every pull request and protected-branch push runs:

```text
checkout -> dependency integrity + secret scan -> lint/format -> unit tests
         -> integration + migration tests -> frontend checks -> OpenAPI contract
         -> image build -> image/dependency scan -> reports + provenance
```

Jobs are independently cacheable but fail closed. Action versions are pinned by
digest/trusted release policy; PR jobs have no deployment secrets. Required gates
are lint/format, tests, migration checks, secret/dependency scans, image build,
and review. Emergency bypasses are documented, approved, and time-bound.

### Artifacts and delivery

Build one non-root API image per commit from a pinned base-image digest. Label it
with source revision, build time, and dependency-lock identity; generate SBOM,
scan, sign/attest, and promote the exact digest—never rebuild per environment.

```text
signed digest -> development deploy + smoke -> staging deploy + migration/checks
              -> approved production promotion + migration + monitored rollout
```

Deployment manifests are reviewed/versioned; secrets are not. Production requires
the staged digest, approval, migration/backup checks, readiness validation, and
monitored rollout. Auto-rollback applies only where schema compatibility exists.
Release metadata includes SHA, app/API version, migration revision, digest,
environment, and deployment time.

## Observability and logging

Accept W3C trace context only from trusted infrastructure; otherwise create trace
and request IDs. Return `X-Request-ID` and propagate it to database/provider and
future queue calls. Client IDs are validated and never authorization signals.

Deployed logs are JSON with `timestamp`, `level`, `service`, `environment`,
`build_sha`, `request_id`, `trace_id`, `route`, `method`, `status_code`,
`duration_ms`, and `event_name`. Do not log authorization headers, cookies,
keys, passwords, database URLs, prompts, chat messages, retrieved/uploaded
content, or raw provider responses. Protected exception logs may include stack
traces under the request ID.

Initial metrics: HTTP counts/duration/in-flight by route template/status; process
start/build data; database failures/pool use; dependency calls/duration/failures;
health state transitions; and error counts by stable code. Labels have bounded
cardinality and never contain IDs, user input, filenames, URLs, or messages.
Create OpenTelemetry-compatible spans for request, DB, and provider calls.
Initial alerts cover readiness failure, 5xx rate, latency saturation, DB failure,
and provider failure rate; each has a runbook before production launch.

## API versioning and compatibility

Product endpoints move under `/api/v1`; health stays outside the namespace.
Unversioned prototype routes are not a long-term contract. Introduce v1 first,
optionally retain development aliases for an announced period, then remove at a
documented breaking release. The frontend uses the versioned base path.

- Additive fields/endpoints are non-breaking.
- Removing/renaming fields, semantics, status codes, auth, validation, or
  pagination is breaking: create `/v2` and publish deprecation guidance.
- Clients ignore unknown response fields; invalid input uses the error envelope.
- CI compares generated OpenAPI to an approved baseline and rejects unversioned
  breaking changes.

| Current | v1 target | Note |
| --- | --- | --- |
| `POST /chat` | `POST /api/v1/chat` | Phase 2 adds workspace scope. |
| `POST /upload` | `POST /api/v1/documents` | Phase 3 makes ingestion asynchronous. |
| `GET /documents` | `GET /api/v1/documents` | Phase 2 adds authorization/pagination. |
| `DELETE /documents/{filename}` | eventual ID-based deletion | Filename is not a durable ID; Phase 3 requires migration path. |

## Containerization plan

Build a multi-stage, minimal, non-root API image from a pinned Python/base-image
digest. Final image has runtime dependencies only, no `.env`, local documents,
vector DB, source-control metadata, tests, or credentials. Use a read-only root
filesystem where possible and explicit temporary writable mounts. The production
process is an ASGI server using runtime environment/secrets and handling SIGTERM
within a finite graceful period. Probes use separate live/readiness endpoints.

Local compose runs API, frontend, and supported relational DB. Bind mounts/hot
reload are development-only; DB uses a named local volume, document/vector state
is explicitly disposable, and ports default to localhost. Migrations are an
explicit compose step. Compose is not production orchestration; Phase 5 defines
managed infrastructure. CI starts the image with non-secret test settings,
probes health, verifies non-root execution, and checks image labels.

## Implementation order and design questions

Implementation, if later approved: approve ADRs; add test harness/injection
seams; add typed settings/lifecycle/health/telemetry; introduce Alembic and
remove startup schema mutation; add v1 routes/OpenAPI/error envelope; then add
containers, compose, CI, and release metadata. Each implementation change needs
its corresponding configuration, runbook, and API documentation first.

Open decisions before implementation: production database and hosting platform;
CI provider/registry; SLOs, telemetry retention, RPO/RTO/on-call; and any
external-client transition period for unversioned endpoints.
