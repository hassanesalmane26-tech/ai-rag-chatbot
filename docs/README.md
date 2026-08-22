# TRIDENT Documentation

This directory is the source of truth for durable technical decisions. Documents
are updated before significant implementation changes are made.

| Document | Purpose |
| --- | --- |
| [Product Vision](product-vision.md) | Official long-term product destination, competitive ambition, editions, economics, Founder ownership and ecosystem principles. |
| [Architecture](architecture/target-architecture.md) | Current baseline, target architecture, and system boundaries. |
| [GENESIS blueprint](architecture/trident-genesis-blueprint.md) | Implemented Workspace-centric GENESIS product reference. |
| [Decision records](decisions/README.md) | Immutable reasoning for material technical choices. |
| [Roadmap](roadmap.md) | Sequenced delivery plan and exit criteria. |
| [Rules Bible](rules-bible.md) | Non-negotiable platform rules. |
| [Engineering standards](engineering-standards.md) | Build, test, API, and delivery expectations. |
| [Deployment architecture](deployment-architecture.md) | Production topology and operating model. |
| [Security baseline](security-baseline.md) | Threat posture and mandatory controls. |
| [Phase 1 specification](phases/phase-1-production-foundation.md) | Detailed production-foundation design; not implementation authorization. |
| [Sprint 1 stabilization](phases/sprint-1-stabilization.md) | Verification scope and intentionally deferred GENESIS work. |
| [Sprint 2 visual system](phases/sprint-2-visual-system.md) | Reusable visual identity, motion, and accessibility architecture. |
| [Sprint 6 Documents Engine](phases/sprint-6-documents.md) | Workspace-scoped document interaction and state architecture. |
| [Sprint 7 backend foundation](phases/sprint-7-backend-foundation.md) | Configuration, lifecycle, errors, and non-destructive migration baseline. |
| [Sprint 7 durable ingestion](phases/sprint-7-durable-ingestion.md) | Recoverable and idempotent Knowledge lifecycle. |
| [Sprint 8 Memory](phases/sprint-8-memory.md) | Explicit bounded Workspace Memory. |
| [Sprint 9 Modules](phases/sprint-9-modules.md) | Declarative Workspace module composition. |
| [Sprint 10 polish](phases/sprint-10-polish.md) | Final UX, accessibility and resilience hardening. |
| [GENESIS completion](phases/genesis-completion.md) | Migration, runtime and release-boundary record. |
| [Genesis v1.0.0 freeze](releases/trident-genesis-v1.0.0.md) | Immutable baseline and release boundary. |
| [TRIDENT AI release candidate](releases/trident-ai-release-candidate.md) | Current release-facing scope, invariants and acceptance boundary. |
| [TRIDENT AI transition](architecture/trident-ai-transition.md) | Additive Identity and edition evolution architecture. |
| [Sprint AI-0](phases/sprint-ai-0.md) | Freeze, publication and security-preparation record. |
| [Sprint AI-1](phases/sprint-ai-1.md) | Provider-neutral Identity and staged Workspace tenancy. |
| [Sprint AI-2](phases/sprint-ai-2.md) | Verified OIDC and systematic tenant authorization. |
| [Sprint AI-3](phases/sprint-ai-3.md) | Authorization Code + PKCE, secure sessions and Workspace entry. |
| [Sprint AI-4](phases/sprint-ai-4.md) | Immutable audit, API contracts, entitlements, quotas and abuse controls. |
| [AI-0 edge hardening plan](operations/ai0-edge-hardening.md) | Production artifact, headers, TLS and supervisor transition. |
| [Owner production closure](operations/owner-production-closure.md) | Exact OIDC, TLS, runtime, Organization and Founder activation procedure. |

## Documentation rule

An implementation that changes a service boundary, persistence model, security
posture, deployment topology, or public API must have its rationale recorded in
an ADR before the change is merged.
