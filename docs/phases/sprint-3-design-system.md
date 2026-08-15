# TRIDENT Genesis — Sprint 3 Design System

## Purpose

Sprint 3 formalizes the validated Sprint 2 visual language without changing product domains. The Workspace remains the visual center; Conversations and Knowledge remain feature modules.

## Layering

```text
tokens → foundations → motion → primitives → layout → feature composition
```

`styles/tokens.css` owns reference and semantic values. Compatibility aliases keep existing feature composition stable while future AI, PRO, and NOVA modules adopt semantic names directly.

## Shared primitives

- `GlassPanel`: common glass surface shell; elevated mode is reserved for focal surfaces.
- `Button`: primary and secondary action behavior, including focus, disabled, pressed and touch sizing.
- `IconButton`: compact accessible control shell.
- `MetricCard`: Workspace overview metric composition.
- `TridentMark` and `VisualEnvironment`: shared brand primitives, never tied to Workspace business state.

## Responsive contract

- Desktop: above 900px.
- Tablet: 761px–900px.
- Mobile navigation/layout transition: 560px–760px.
- Compact mobile: 390px and below.

At mobile widths, the Workspace hero is a single-column flow and content reserves space for the safe-area-aware bottom navigation.

## Non-negotiable constraints

- No backend or API coupling in the Design System.
- `WorkspaceContext` and workspace boundaries remain unchanged.
- Decorative motion must use composited properties when possible and honour `prefers-reduced-motion`.
- Glass hierarchy must differentiate structural, elevated, interactive and selected surfaces.
- New modules must consume semantic tokens and primitives before adding feature-local visual values.
