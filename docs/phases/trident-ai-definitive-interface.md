# TRIDENT AI — Definitive Interface Pass

Status: implementation complete; pending founder visual validation.

## Rework scope

The interface continues to evolve additively from TRIDENT AI V1.0.0 Gold. It
keeps the existing session, Workspace context, declarative lazy module registry, service
boundaries, APIs, and business behavior.

- Large desktop: persistent system rail, central Intelligent Workspace, and a
  secondary context rail using real overview and sanitized activity data.
- Laptop and tablet: the context rail reflows into the main document instead of
  squeezing a three-column composition.
- Product entry: an authorized Workspace opens Nova first; Overview remains
  available as a secondary module through the system navigation.
- Mobile: a compact header and focus-managed system drawer expose every real
  module, the five most recent server-returned conversations and Workspace
  controls. Selecting a conversation delegates to the existing Nova detail
  loader. Nova does not duplicate that history as a horizontal tab strip on
  phones, preserving the sanctuary height. The persistent module bottom bar is
  removed so the safe-area bottom edge belongs to Nova's always-available
  composer.
- Visual environment: CSS-generated stars, mist, a distant moon, atmospheric
  depth, brighter cloud banks, two abstract celestial-city silhouette planes,
  a sanctuary, a central light axis, constellation traces, foreground
  architecture, horizons, orbits, glows, and bounded particles; the canonical
  reference image is never imported by the runtime.
- Nova scene: a dedicated orbital Core establishes the central hierarchy;
  contextual prompts remain real input shortcuts, the signature composer keeps
  the existing send lifecycle, and active conversations reduce environmental
  contrast instead of removing the shared world.
- Large-screen Nova: at 1440 px and above, a conditionally mounted context rail
  presents only server-returned overview counts and sanitized recent activity.
  It remains unmounted below that breakpoint, avoiding decorative mobile API
  traffic and preserving the central Nova surface.
- Accessibility: command, Workspace, and onboarding dialogs share focus
  containment, Escape handling, initial focus, and focus restoration.

## Data truth and boundaries

The contextual rail displays only server-returned Workspace overview counts,
sanitized Workspace activity, and the active Workspace context. Artefacts remain
zero when no artifact persistence exists. No model count, agent state, memory
capacity, uptime, notification, project, or automation state is invented.

This pass adds no endpoint, schema, persistence path, entitlement, or client-side
authorization rule. OIDC Authorization Code + PKCE, opaque sessions, CSRF,
Founder isolation, and database-authoritative tenant checks remain unchanged.

## Acceptance matrix

The responsive rules explicitly cover portrait mobile below 768 px, low-height
landscape phones through 950 px, compact-rail tablets from 768 through 1024 px,
standard desktop/laptop through 1439 px, and the contextual large-screen shell
at 1440 px and above. Mobile Nova owns an internal message scroller and a
safe-area-aware composer; drawers and command surfaces are bounded by `100dvh`.
The mobile Nova grid has one explicit content row so its composer reaches the
actual safe-area edge rather than ending above an unused implicit grid row.
Tablet Nova removes the redundant conversation column and delegates history to
the existing system drawer, preserving the conversation lifecycle while giving
the sanctuary the full available width.
Decorative motion is CSS-only, low-amplitude and reduced-motion aware. Physical
device keyboard behavior, Safari dynamic viewport transitions and final visual
acceptance remain founder review activities.
