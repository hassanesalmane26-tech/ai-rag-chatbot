# TRIDENT AI

TRIDENT is a Workspace-centric AI Operating System. TRIDENT AI evolves
additively from the frozen Genesis baseline with Workspace Home,
Conversations, Knowledge, explicit Memory and a declarative module composition
boundary. The immutable Genesis release is tagged
`trident-genesis-v1.0.0`.

The backend uses FastAPI, SQLAlchemy, PostgreSQL, Alembic and Chroma. The client
uses React and Vite. See [project documentation](docs/README.md) for architecture,
decisions, migration safety and phase records.

TRIDENT AI includes provider-neutral OIDC verification, sessions and
Organization/Workspace authorization. The current deployment has no real OIDC
issuer or TLS configuration and is therefore not approved for public use with
sensitive data. See [the security baseline](docs/security-baseline.md) for the
exact deployment boundary.
