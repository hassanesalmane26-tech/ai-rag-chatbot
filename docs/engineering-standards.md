# Engineering Standards

## Delivery

Every change has a stated scope, tests proportionate to risk, and documentation
updates when behavior, contracts, or operations change. Pull requests should be
small, reviewable, and include rollback notes for data or deployment changes.

## Python and API

- Use typed Pydantic request/response models and explicit HTTP error contracts.
- Keep route handlers thin; place domain logic behind module interfaces.
- Use dependency injection for configuration, clients, sessions, and clocks.
- Validate all input, set timeouts for outbound calls, and map internal errors
  to safe public responses.
- Maintain OpenAPI as an API contract; introduce breaking changes only through
  a new API version and a published deprecation window.

## Data

- Manage schema exclusively through migrations.
- Use UTC timestamps and immutable identifiers.
- Define retention, deletion, and backup behavior for every data class.
- Test migrations and authorization predicates.

## Testing and quality gates

Required layers as applicable: unit tests, API/integration tests, migration
tests, security/authorization tests, and end-to-end critical-path tests.
CI must format/lint, test, scan dependencies/secrets, and build deployable
artifacts. AI features also require evaluation fixtures and regression thresholds.

## Frontend

The browser is untrusted. It may manage presentation state but cannot enforce
authorization or hold provider credentials. API failures, loading states, and
accessibility are first-class behavior.
