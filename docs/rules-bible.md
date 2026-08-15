# TRIDENT Rules Bible

1. Documentation and an ADR precede material architectural change.
2. Tenant boundaries are explicit in data, authorization, logs, and tests.
3. Secrets never enter source control, browser bundles, logs, prompts, or error
   responses.
4. The relational database is authoritative; indexes and caches are rebuildable
   derivatives.
5. Original files use durable object storage; local disk is development-only.
6. Long-running or failure-prone work runs asynchronously and is idempotent.
7. Public APIs are versioned, validated, and backward-compatible by policy.
8. Every AI request has a traceable model, prompt version, retrieval set, and
   policy outcome, subject to privacy controls.
9. Authorization happens server-side before any data access or provider call.
10. Observability is designed in: structured logs, metrics, traces, audit
    events, and actionable alerts.
11. Schema changes use reviewed, reversible migrations; application startup
    never mutates production schema.
12. Dependencies, infrastructure, and permissions are least-privilege and
    regularly reviewed.
13. Each change carries proportionate automated tests and operational rollback
    considerations.
14. No platform module may import another module's persistence internals.
