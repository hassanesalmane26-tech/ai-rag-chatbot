# Sprint 2 — TRIDENT Visual System

## Intent

The Workspace is the hero surface of TRIDENT GENESIS. The visual system creates
depth and identity without introducing product state, API dependencies, or
backend coupling.

## Architecture

- `VisualEnvironment` is a fixed, `aria-hidden` decorative layer placed behind
  the application shell. It owns the grid, diffuse orbs, and a bounded set of
  six particles.
- `TridentMark` is the reusable brand mark used by navigation and header.
- CSS design tokens in `styles/theme.css` define color, translucency, depth,
  spacing, motion, and easing. Product components consume semantic classes
  rather than visual constants.
- Workspace, Conversations, and Knowledge remain independent product modules;
  visual surfaces do not own their data or behavior.

## Performance and accessibility

Animation uses transform and opacity only. The background has no event handler,
no parallax listener, and no timer-driven React state. `prefers-reduced-motion`
reduces every animation and transition to a near-instant static state. Header
controls not available in GENESIS remain disabled and labelled as unavailable.

## Evolution

TRIDENT AI, PRO, and NOVA can add semantic surface variants or module-specific
accents through tokens. They must not duplicate the background or embed visual
logic in domain modules.
