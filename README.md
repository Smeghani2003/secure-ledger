# SecureLedger

A security-first personal finance aggregator. Connects to banks via **Plaid**, stores access tokens **encrypted at rest**, and runs on a clean modern stack: **FastAPI + Postgres + React/TypeScript**.

🔗 **Live demo:** [secureledger.fly.dev](https://secureledger.fly.dev) — sign up with any email and a 12+ character password, then click **Link a bank** and use Plaid sandbox creds `user_good` / `pass_good`.

> Portfolio project — designed to demonstrate identity, access governance, and secure data handling on a contemporary Python + TypeScript stack. Deployed on Fly.io with managed Postgres.

---

## Architecture

```
[React/TS SPA]  ──HTTPS──▶  [FastAPI service]
                                │
                                ├── Auth middleware (JWT)
                                ├── Plaid integration (sandbox)
                                └── Crypto service (Fernet)
                                        │
                              [Postgres]  [Redis]  [Plaid]
```

- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2
- **Auth**: JWT access + refresh tokens; password hashing with bcrypt
- **Crypto**: Plaid access tokens encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256)
- **DB**: Postgres 16
- **Cache / rate limiting**: Redis 7
- **Frontend**: React 18, TypeScript, Vite, Tailwind, TanStack Query, react-plaid-link
- **Bank data**: Plaid sandbox

## What's in this repo

**Auth & user management**
- Signup / login / refresh / `/me` with JWT access (15min) + refresh (30day) tokens
- Passwords hashed with bcrypt + manual SHA-256 prehash (sidesteps bcrypt's 72-byte limit without truncation; same approach Django and Supabase use)

**Plaid integration**
- Link token creation and public-token exchange against Plaid sandbox
- Plaid access tokens **encrypted at rest** with Fernet (AES-128-CBC + HMAC-SHA256), with `encryption_key_version` column for future key rotation
- Accounts + transactions sync via Plaid's cursor-based `/transactions/sync` — first call returns the historical window, subsequent calls return only what changed since the persisted cursor
- Idempotent upserts: handles Plaid's `added` / `modified` / `removed` transaction lists correctly; safe to call repeatedly

**Frontend**
- React 18 + TypeScript + Vite + Tailwind
- TanStack Query for server-state caching, React Router for navigation
- Plaid Link integration via `react-plaid-link`

**Dev infrastructure**
- docker-compose: Postgres 16 + Redis 7 + backend + frontend, all wired up with healthchecks
- Alembic migrations checked in, applied automatically on backend start
- GitHub Actions CI: `ruff` + `mypy --strict` + `pytest` (backend); `eslint` + `tsc --noEmit` + `vite build` (frontend)
- Full setup runbook in [SETUP.md](./SETUP.md)

## Quick start

### 1. Clone

```bash
git clone git@github.com:Smeghani2003/secure-ledger.git
cd secure-ledger
```

### 2. Configure env

```bash
cp .env.example .env

# Generate a JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
# Paste into JWT_SECRET_KEY=

# Generate a Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Paste into FERNET_KEY=

# Add your Plaid sandbox keys from dashboard.plaid.com → Team Settings → Keys
# PLAID_CLIENT_ID=...
# PLAID_SECRET=...   (use the SANDBOX one)
```

### 3. Run

```bash
docker compose up --build
```

- API: http://localhost:8000 (docs at /docs)
- App: http://localhost:5173

### 4. Try it

1. Open http://localhost:5173
2. Create an account (password ≥ 12 chars)
3. Click **Link a bank**
4. In Plaid Link: pick any sandbox institution, then sign in with `user_good` / `pass_good`
5. You'll land back on the dashboard. Account sync arrives in Week 2.

## Local development without Docker

Backend:

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install uv
uv pip install -e ".[dev]"
# Make sure Postgres and Redis are running and DATABASE_URL/REDIS_URL point at them
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
pnpm install
pnpm dev
```

## Tests

```bash
# Backend
cd backend && pytest -v

# Frontend
cd frontend && pnpm tsc --noEmit && pnpm lint && pnpm build
```

## API surface

Interactive docs at `http://localhost:8000/docs` (Swagger UI) once the stack is running.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/auth/signup` | — | Create account, returns access + refresh JWTs |
| `POST` | `/api/auth/login` | — | Returns access + refresh JWTs on valid credentials |
| `POST` | `/api/auth/refresh` | refresh JWT | Mint a new access token from a refresh token |
| `GET` | `/api/auth/me` | access JWT | Current user profile |
| `POST` | `/api/plaid/link-token` | access JWT | Create a Plaid Link token for the SPA |
| `POST` | `/api/plaid/exchange` | access JWT | Exchange a public token; encrypts and stores the access token |
| `POST` | `/api/plaid/sync` | access JWT | Pull accounts + transaction deltas for every linked bank |
| `GET` | `/api/accounts` | access JWT | List the current user's accounts with balances |
| `GET` | `/healthz` | — | Liveness probe |

## Security model

This is the headline feature of the project — the design choices below are deliberate and justifiable in an interview.

**Password storage.** Bcrypt with a manual SHA-256 prehash. Bcrypt has a hard 72-byte input limit and (in 4.x) raises rather than truncates; SHA-256 prehashing produces a fixed 32-byte digest, base64-encoded to 44 printable bytes — well under the limit, with no entropy loss and no truncation collisions. Passwords are never logged.

**JWT design.** Access tokens are 15 minutes; refresh tokens are 30 days. Both are HS256-signed and tagged with a `type` claim (`access` or `refresh`); the decoder rejects tokens of the wrong type, so a refresh token can never be used as an access token even if leaked.

**Plaid access tokens at rest.** A Plaid access token, once issued, persists for the lifetime of the linked institution and grants ongoing read access to the user's financial data. We never store it in plaintext. On exchange, the token is encrypted with **Fernet** (AES-128-CBC + HMAC-SHA256) and stored as `plaid_items.access_token_ciphertext`. The `encryption_key_version` column tags every row with the key it was encrypted under, so future key rotation can re-encrypt rows incrementally without downtime.

**Verify the encryption claim** with a quick `psql` query:

```sql
SELECT institution_name, encryption_key_version, length(access_token_ciphertext) AS bytes
FROM plaid_items;
```

You'll see the institution name in cleartext (it's not sensitive) and only the byte length of the ciphertext — Postgres has the encrypted blob, but it's meaningless without the Fernet key from the `.env`. Dump the database, you can't replay the token.

**Other defenses.** CORS allowlist (configured origins only), Pydantic v2 validates every request body, all secrets read from environment (never committed), `.gitignore` blocks `.env` from being committed.

**V2 hardening (not yet built).** Redis-backed rate limiting on auth endpoints, audit log middleware, RBAC for shared households, and self-hosted OIDC to remove the dependency on a single JWT secret.

## Status

| Area | Status |
|---|---|
| Auth (signup / login / refresh / `/me`) | ✅ Done |
| Plaid Link + token exchange | ✅ Done |
| Encrypted-at-rest access tokens | ✅ Done |
| Accounts + transactions sync (`POST /api/plaid/sync`) | ✅ Done |
| Auto-sync on link + manual refresh button | ✅ Done |
| Dashboard: balances, transactions list, spend chart | ✅ Done |
| Public deploy (Fly.io + managed Postgres) | ✅ Done |
| AI transaction categorization (Claude) | 📋 V2 |
| RBAC + households + audit log | 📋 V2 |
| Self-hosted OIDC | 📋 V2 |

## License

MIT — see [LICENSE](./LICENSE).
