# TRIDENT AI

TRIDENT is a Workspace-centric AI Operating System. TRIDENT AI V1.0.0 combines a
Workspace Home, Nova, Knowledge, explicit Memory, Files, Artifacts, Activity,
Settings and a Workspace command surface behind a declarative module boundary.
It evolves additively from the immutable historical baseline tagged
`trident-genesis-v1.0.0`.

The backend uses FastAPI, SQLAlchemy, PostgreSQL, Alembic and Chroma. The client
uses React and Vite. See [project documentation](docs/README.md) for architecture,
decisions, migration safety and phase records.

TRIDENT AI includes production OIDC Authorization Code with PKCE, opaque
sessions, CSRF enforcement, personal Organization/Workspace onboarding and
database-authoritative tenant authorization. Runtime deployment configuration
remains owner-controlled and is intentionally outside repository release work.
See [the security baseline](docs/security-baseline.md) for the exact boundary.
