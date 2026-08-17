# ADR 0015 — Workspace-scoped AI orchestration and trust

Status: Accepted (AI-6)

## Decision

Model invocation is behind `ModelProvider`; the OpenAI SDK is an adapter, not a
domain dependency. Orchestration receives an already-authorized Workspace ID,
bounded history, explicit memory and Workspace-filtered retrieval sources.
Knowledge and Memory are delimited as untrusted data and never become system
instructions. Only retrieved sources with matching Workspace metadata produce
citations. Provider request IDs may be propagated internally, without logging
prompts, document text or message bodies.

Generation failure keeps the user turn durable and returns a controlled 503.
Provider selection, fallback and richer evaluation remain policy extensions;
they must not weaken tenant filtering or silently change trust boundaries.

## Consequences

TRIDENT can add model providers without coupling Workspace services to an SDK.
Prompt size is bounded and citations remain traceable. The current evaluation
fixtures verify injection separation and citation behavior but do not replace a
red-team corpus or external model-quality evaluation.
