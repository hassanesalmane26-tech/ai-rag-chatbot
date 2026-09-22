# Nova images and spatial experience

## Product contract

Nova is the interaction surface of the existing Intelligent Workspace, not a
second chat system. Explicit French/English image-creation requests enter the
same durable image queue as the composer image mode. Explicit edits referring
to an image use the latest completed image in that conversation. Other text
continues through the existing conversation/RAG/Memory pipeline. The image
composer lets the user refine the prompt, attach a PNG/JPEG/WebP, choose square,
landscape (3:2) or portrait (2:3), modify a result or prepare a new variant.
There are no fabricated percentages, model selectors or edition features.

## Persistence and authorization

Migration `0011_workspace_images` adds **one** task/artifact table. Each row links
Workspace, conversation, originating user, both durable messages, optional
parent image, prompt, ratio, timestamps, attempts, status and private object
keys. Provider/model metadata remains server-side. Workspace membership remains
authoritative for every read and mutation. Only the originating user may retry
or cancel a job; Founder edition access never bypasses this boundary.

Public contracts (all under `/api/v1/workspaces/{workspace_id}`):

| Route | Contract |
| --- | --- |
| `GET /images/capability` | Actual configuration availability, supported ratios/size limit |
| `POST /conversations/{id}/images` | Multipart prompt, request_key, aspect_ratio, optional image or source_id; 202 + queued record |
| `GET /images` | Authorized paginated records; optional conversation_id |
| `GET /images/{id}/content` | Completed PNG only, authenticated, private/no-store, nosniff |
| `POST /images/{id}/retry` | Explicit retry of failed task, at most three provider attempts |
| `POST /images/{id}/cancel` | Cancellation only before claim; generating tasks cannot be cancelled |

The existing message endpoint accepts an optional `request_key`. Image intent
returns the normal persisted user/assistant message contract plus task metadata;
the provider is never awaited by the HTTP message request.

## Worker and provider boundaries

`ImageGenerationProvider`, `ImageGenerationRequest` and `ImageGenerationResult`
are provider-neutral. Only `app/images/provider.py` imports the OpenAI SDK.
The adapter uses the server-side Images generate/edit API, configurable model,
one PNG result and an explicit timeout. Reference:
[official Images guide](https://developers.openai.com/api/docs/guides/image-generation).

The application lifespan starts a bounded in-process worker **only when enabled
and configured**. SQL atomic queued→generating claims coordinate multiple API
processes; each process handles at most one provider call at a time. Tasks
survive process restart. No extra queue, systemd unit or vendor storage service
is introduced. Workspace enqueue locks cap pending work at three; existing
server-side hourly quota/Founder policy is reused, not replaced by a paywall.

Lifecycle: queued→generating→completed/failed; queued→cancelled;
failed→queued only by explicit authorized retry before three attempts. A claim
older than ten minutes becomes failed, never automatically rebilled. The SDK
also has automatic retries disabled. A timeout is ambiguous: a user-requested
retry may make a new billed provider request. Requests reuse conversation +
request-key uniqueness and a prompt/input fingerprint; conflicting reuse is 409.

The worker rechecks active user/membership before calling the provider. Uploads
are decoded with a pixel/byte limit and re-encoded as PNG without metadata;
SVG, HTML, animated/invalid rasters and decompression bombs are rejected. Output
is validated through the same raster boundary. There is no arbitrary URL fetch
or client-selected object path. These images do **not** enter Knowledge/RAG and
do not bypass the document scanner lifecycle.

`LocalObjectStorage` is reused. By default images live in
`TRIDENT_DOCUMENTS_PATH/nova-images`, outside immutable releases/web roots;
`TRIDENT_IMAGES_PATH` can set an explicit durable path. Records and source/result
objects are retained, including cancelled/failed records for diagnosis. There
is no unapproved automatic retention deletion or fake delete control. Backup
must include both database and this private object directory.

## Configuration

- `TRIDENT_IMAGE_PROVIDER=disabled` (default) or `openai`.
- Existing backend `TRIDENT_OPENAI_API_KEY` / `OPENAI_API_KEY`; never a VITE value.
- `TRIDENT_IMAGE_MODEL=gpt-image-1` default, configurable server-side.
- `TRIDENT_IMAGE_TIMEOUT_SECONDS=180`, range 10–300 seconds.
- Optional `TRIDENT_IMAGES_PATH` (otherwise existing durable document root).

Missing credentials or disabled provider reports configuration-required and
rejects creation without persisting a false success. Chat and existing artifacts
remain usable. Capability/configuration does not prove provider account/model
eligibility: real generation must be tested after authorized activation.

## Rendering contract

`celestial.css` owns the Nova layout and effects tokens. Superseded Nova rules
were removed from legacy sheets rather than stacked under further overrides.
The illustrated world uses six decorative nodes; mobile atmosphere is static.
Scrolling content is painted normally: no content-visibility hiding, full-card
opacity reveal or scrolling backdrop blur. A small Core shadow and desktop
transform/opacity breathing retain identity. Reduced motion disables motion.

Conversation owns the viewport; only history scrolls. System drawer is available
on all sizes and context rail is optional on wide desktop. Markdown excludes
raw HTML and external image loads. `visualViewport` resizing adjusts the shell
only while editing on coarse-pointer devices, with rAF coalescing and cleanup.

Image polling stops at terminal states. Authorized blob fetching is deferred
until the image card is near view, while its prompt/status and reserved image
dimensions remain present. Blob URLs are revoked on unmount/scope change.

## Verification limits

Unit/API/migration tests use temporary databases and deterministic providers.
Browser tests intercept every API request and prohibit external requests.
They validate layout and interactions, **not** production authentication,
provider billing, Safari keyboard hardware behavior or 60 FPS. Founder iPhone
validation remains required.
