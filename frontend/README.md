# TRIDENT AI frontend

The TRIDENT AI client is a React/Vite experience centered on the active
Workspace. Nova, Knowledge and Memory are composed through the declarative
module registry; Organization and Workspace authorization remains
database-authoritative on the backend.

## Local quality gates

```bash
npm run lint
npm test
npm run build
```

The browser is not an authorization boundary. It consumes only server-authored
session, Organization and Workspace context and never stores OIDC credentials.

Created by Salmane Hassan

A TRIDENT Project
