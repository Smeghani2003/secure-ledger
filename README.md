# SecureLedger

A security-first personal finance aggregator. Connects to banks via **Plaid**, stores access tokens **encrypted at rest**, and runs on a clean modern stack: **FastAPI + Postgres + Redis + React/TypeScript**.

> Portfolio project — designed to demonstrate identity, access governance, and secure data handling on a contemporary Python + TypeScript stack.

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

## What's in this repo (Week 1 scope)

- Signup / login / refresh / `/me` (JWT)
- Plaid Link token endpoint
- Plaid public-token exchange with **encrypted-at-rest** access-token storage
- Accounts list endpoint (read-only stub for Week 2 sync)
- React frontend with login, signup, and dashboard pages
- docker-compose with Postgres + Redis + backend + frontend
- GitHub Actions CI: ruff + mypy + pytest (backend); eslint + tsc + vite build (frontend)

Week 2 adds: account & transaction sync, dashboard with transactions and spending charts, public deploy to Fly.io.

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

## Security model (TL;DR — see SECURITY.md, coming Week 2)

- Passwords: bcrypt, never logged.
- JWTs: 15-min access tokens; 30-day refresh tokens; type-tagged.
- Plaid access tokens: never stored in plaintext. Fernet-encrypted in `plaid_items.access_token_ciphertext` with `encryption_key_version` for rotation.
- CORS: only configured origins.
- Input validation: every request through Pydantic.
- (V2) Rate limiting in Redis, audit log middleware, RBAC for households, OIDC self-hosted auth.

## Status

| Area | Status |
|---|---|
| Auth (JWT) | ✅ Week 1 |
| Plaid link / exchange | ✅ Week 1 |
| Accounts/transactions sync | 🚧 Week 2 |
| Categorization (Claude) | 🚧 Week 2 |
| Spending reports | 🚧 Week 2 |
| Public deploy (Fly.io) | 🚧 Week 2 |
| RBAC + audit log | 📋 V2 |
| Self-hosted OIDC | 📋 V2 |

## License

MIT — see [LICENSE](./LICENSE).
