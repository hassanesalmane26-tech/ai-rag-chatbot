# Deployment Architecture

## Target topology

Production deploys immutable API and worker images into separate workloads.
Traffic passes through a managed TLS edge with WAF and rate limits. Private
workloads access managed relational storage, object storage, a vector database,
and a durable queue using least-privilege workload identities. Secrets are
supplied by a secret manager at runtime.

```text
Internet -> CDN/WAF -> load balancer -> API replicas -> DB / object store
                                            |             vector database
                                            -> durable queue -> worker replicas
```

## Environment policy

Development, staging, and production are isolated accounts/projects with
separate credentials and data. Production access is audited and time-bound.
Configuration is validated at startup; no production default permits debug mode
or local persistence.

## Reliability policy

Deployments use migrations, health checks, rolling or canary rollout, and a
documented rollback. Backups cover relational metadata and object content;
vector indexes are recreated from approved source records. Define RPO/RTO before
production launch and test restoration at least quarterly.

`/health/live` proves process liveness. `/health/ready` additionally requires
database connectivity, the exact Alembic head and accessible original storage.
`/health/build` exposes non-secret build/revision identity. Run `python -m
app.operations.preflight` against each staged release before traffic.

The browser runtime must use immutable `frontend/dist`, never `vite dev`. The
owner must point the edge at the approved artifact, configure SPA fallback and
headers/CSP, validate Nginx configuration, then reload through the authorized
operational process. Repository work does not autonomously alter those units.

## Observability

Use correlated request IDs across API, jobs, provider calls, and audit events.
Collect structured logs, metrics, traces, dashboards, and alerts for availability,
latency, queue depth, ingestion failures, provider errors, authorization denials,
and cost/usage anomalies.
