# ADR 0005: Standardize structured and OpenTelemetry-compatible telemetry

- **Status:** Partially accepted — structured logging and request correlation implemented
- **Date:** 2026-07-29
- **Owner:** TRIDENT architecture

## Context

The prototype lacks request correlation, health contracts, and privacy-aware
telemetry rules.

## Decision

Use structured logs, stable request IDs, metrics, and OpenTelemetry-compatible
traces with explicit redaction and bounded-cardinality rules.

## Consequences

Diagnostics remain platform-neutral and safer. New features must include
instrumentation and cannot log prompts or customer content by default.

Metrics, distributed traces and an OTLP exporter remain TRIDENT AI delivery
work; the Genesis implementation covers privacy-safe JSON logs and request IDs.
