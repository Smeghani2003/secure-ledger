# SecureLedger — Setup Runbook

A step-by-step record of every command run to take this project from empty folder to running stack, with an explanation of what each command does and why.

Run all commands from the project root: `~/Documents/Projects/secure-ledger`.

---

## 1. Local environment configuration

### 1.1 Create a local `.env` from the template

```bash
cp .env.example .env
```

**What it does:** copies `.env.example` to a new file named `.env`.

**Why:** The repo ships with `.env.example` — a template that documents which environment variables exist, with placeholder values. The real `.env` is the file the application actually reads at startup, and it contains real secrets. `.env` is listed in `.gitignore`, so it's never committed; `.env.example` is committed so other developers know what they need to fill in.

**Result:** Two files now exist at the project root: `.env.example` (template, committed) and `.env` (your local secrets, ignored by git).

---

### 1.2 Generate a JWT secret

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

**What it does:** uses Python's standard library to print a cryptographically random 64-byte string, URL-safe base64 encoded (~86 characters).

**Why:** The backend signs JWT access and refresh tokens using HMAC-SHA256, which requires a long, random secret. If the secret is short, predictable, or shared, an attacker could forge valid tokens and bypass authentication. `secrets.token_urlsafe(64)` is the recommended way to generate one in Python — it's pulled from the OS entropy pool and is safe for cryptographic use.

**Action after running:** copy the output, open `.env`, and replace the placeholder after `JWT_SECRET_KEY=`.

---

### 1.3 Generate a Fernet encryption key

```bash
python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

**What it does:** generates 32 random bytes and encodes them as URL-safe base64 — exactly the format Fernet expects (44 characters ending in `=`).

**Why:** Plaid access tokens are highly sensitive — anyone holding one can pull a user's bank transactions. We don't store them in plaintext; we encrypt them at rest using **Fernet** (AES-128-CBC + HMAC-SHA256). Fernet needs a 32-byte symmetric key. The `cryptography` library has `Fernet.generate_key()` for this, but the standard library can produce the same shape with no extra dependency.

**Action after running:** copy the output, open `.env`, and replace the placeholder after `FERNET_KEY=`.

**Note on key rotation:** the `plaid_items` table has an `encryption_key_version` column. If we rotate this key in the future, old rows stay readable under the old key while new rows are encrypted under the new one — that's the design intent for a real-world V2.

---

### 1.4 Get Plaid sandbox credentials

1. Sign up at [plaid.com](https://plaid.com), verify your email.
2. From dashboard.plaid.com, go to **Developers → Keys** (sidebar): [dashboard.plaid.com/developers/keys](https://dashboard.plaid.com/developers/keys).
3. Copy your `client_id` and the **Sandbox secret**.

**Why:** Plaid is the bank-aggregation provider. The `client_id` identifies our application; the secret authenticates our backend's API calls. Sandbox mode lets us link fake banks (with fake credentials `user_good` / `pass_good`) without needing real banking partnerships, which is exactly what we want for development.

**Action:** paste them into `.env`:

```
PLAID_CLIENT_ID=<your client_id>
PLAID_SECRET=<your sandbox secret>
```

---

## 2. Push to GitHub

### 2.1 Initialize the local git repo

```bash
git init
```

**What it does:** creates a hidden `.git/` folder in the project root, turning the directory into a git repository. From this point on, git can track changes to every file.

---

### 2.2 Rename the default branch to `main`

```bash
git branch -M main
```

**What it does:** renames the current branch (which `git init` defaults to `master` on older git versions) to `main`. The `-M` flag forces the rename.

**Why:** `main` is the modern convention and the default branch name on GitHub.

---

### 2.3 Stage all files

```bash
git add .
```

**What it does:** adds every non-ignored file under the current directory to the staging area, ready to be committed. The `.` means "everything from here down."

**Why we don't worry about secrets:** `.gitignore` already excludes `.env`, `node_modules/`, `__pycache__/`, `.venv/`, and similar. Run `git status` first to confirm `.env` is NOT in the list of staged files.

---

### 2.4 Create the initial commit

```bash
git commit -m "Initial scaffold: FastAPI + React/TS + Postgres + Plaid sandbox"
```

**What it does:** snapshots the staged files into a permanent commit on the local `main` branch, with the message in quotes as the commit description.

**Why a descriptive message:** future-you (and any reviewer) reads commit messages to understand what changed and why. "Initial commit" is uninformative; saying what's in the scaffold is useful.

---

### 2.5 Link the local repo to GitHub

```bash
git remote add origin git@github.com:Smeghani2003/secure-ledger.git
```

**What it does:** registers a remote named `origin` pointing at the GitHub repo. `origin` is the conventional name for "the main remote we push to."

---

### 2.6 Switch from SSH to HTTPS (because SSH wasn't configured)

```bash
git remote set-url origin https://github.com/Smeghani2003/secure-ledger.git
```

**What it does:** changes the URL of the existing `origin` remote from SSH (`git@github.com:...`) to HTTPS (`https://github.com/...`).

**Why:** the SSH push failed with `Permission denied (publickey)`. That means GitHub doesn't recognize an SSH key for this machine. Rather than generate one, the fastest workaround is to switch to HTTPS, which authenticates with a GitHub Personal Access Token (PAT). macOS Keychain caches the token after the first push so you don't have to enter it again.

---

### 2.7 Push to GitHub

```bash
git push -u origin main
```

**What it does:** uploads your local `main` branch to the `origin` remote and sets it as the upstream. The `-u` flag means future `git push` and `git pull` commands without arguments will default to this remote/branch pair.

**Authentication:** prompts for username (your GitHub handle) and password (your **Personal Access Token**, not your real GitHub password — GitHub disabled password auth for git operations).

---

## 3. Docker setup

### 3.1 Install Docker Desktop

Downloaded from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/), installed, and verified:

```bash
docker --version
docker compose version
```

**Why Docker:** SecureLedger has four moving parts (Postgres, Redis, FastAPI backend, React frontend). Running each one natively requires installing Postgres, Redis, Python 3.12, Node 20+, and managing them separately. Docker Compose runs all four in isolated containers from a single `docker-compose.yml` file, with one command. The same setup works on every machine.

---

### 3.2 Grant Docker access to the Documents folder

System Settings → Privacy & Security → Files & Folders → enable **Documents Folder** under Docker.

**Why:** `docker-compose.yml` uses **bind mounts** (`volumes: - ./backend:/app`) to expose your local source code to the running containers. This is what gives you live reload — when you edit a file in `~/Documents/Projects/secure-ledger/backend/`, the container sees the change immediately. Without filesystem permission, bind mounts fail and the containers can't start.

---

## 4. Bring the stack up

### 4.1 Start Postgres and Redis in the background

```bash
docker compose up -d db redis
```

**Breakdown:**
- `docker compose up` — start services defined in `docker-compose.yml`.
- `-d` (detached) — run them in the background and return your terminal immediately.
- `db redis` — only start these two services, not the whole stack.

**Why this order:** the backend can't run migrations until Postgres is up and accepting connections. Starting `db` and `redis` first, then doing migrations, then starting the application services, is the cleanest sequence.

---

### 4.2 Confirm services are healthy

```bash
docker compose ps
```

**What it does:** lists all running services for this project, with their status and exposed ports.

**What to look for:** `db` and `redis` should both show `running` or `healthy` (the Postgres healthcheck takes 5–10 seconds after the container starts).

---

### 4.3 Generate the initial database migration

```bash
docker compose run --rm backend alembic revision --autogenerate -m "init schema"
```

**Breakdown:**
- `docker compose run` — start a one-off container based on the `backend` service.
- `--rm` — delete the container after the command finishes (otherwise stopped containers pile up).
- `backend` — which service from `docker-compose.yml` to use.
- `alembic revision --autogenerate -m "init schema"` — Alembic command that compares your SQLAlchemy models against the current database schema and writes a Python migration file containing the diff.

**Why we don't ship the migration in git:** the first migration must reflect the live schema, which requires Postgres to be running. Running it once locally generates `backend/alembic/versions/<hash>_init_schema.py` — that file should then be committed and become part of the repo for the next developer.

---

### 4.4 Apply the migration

```bash
docker compose run --rm backend alembic upgrade head
```

**What it does:** runs every pending migration up to the latest one (`head`). On a fresh database, this creates the `users`, `plaid_items`, `accounts`, and `transactions` tables.

**Why a separate command:** Alembic separates "describe a change" (`revision`) from "apply a change" (`upgrade`). This lets you review the generated SQL before running it against a real database — important once you have production data.

---

### 4.5 Bring up the full stack

```bash
docker compose up
```

**What it does:** starts all four services (`db`, `redis`, `backend`, `frontend`) and **streams their logs to your terminal**. Stays in the foreground until you press Ctrl+C.

**Why no `-d` this time:** during development, you want to watch logs to catch errors as they happen. Once the app is stable you can run with `-d` and use `docker compose logs -f backend` to tail just one service.

**What "ready" looks like in the logs:**
- `db | LOG: database system is ready to accept connections`
- `redis | Ready to accept connections`
- `backend | INFO: Uvicorn running on http://0.0.0.0:8000`
- `frontend | VITE ready in XXX ms` and `Local: http://localhost:5173/`

---

### 4.6 Smoke test

In a new terminal tab (Cmd+T):

```bash
curl http://localhost:8000/healthz
```

**Expected output:** `{"status":"ok"}`

**Why:** confirms the backend is responding before you open the browser. If this fails, the issue is in the backend; if it succeeds and the browser still doesn't work, the issue is in the frontend or CORS.

Then in the browser:
- http://localhost:8000/docs — interactive Swagger UI showing all API endpoints.
- http://localhost:5173 — the React app sign-up page.

---

## 5. Cheat sheet — common day-to-day commands

| Command | What it does |
|---|---|
| `docker compose up` | Start everything in the foreground (logs visible). |
| `docker compose up -d` | Start everything in the background. |
| `docker compose down` | Stop and remove all containers (data in named volumes persists). |
| `docker compose down -v` | Stop containers AND wipe Postgres data. Use to reset everything. |
| `docker compose logs -f backend` | Tail logs for just the backend service. |
| `docker compose ps` | Show status of all services. |
| `docker compose restart backend` | Restart a single service after changes. |
| `docker compose exec backend bash` | Drop into a shell inside the running backend container. |
| `docker compose run --rm backend pytest` | Run the test suite. |
| `docker compose run --rm backend alembic revision --autogenerate -m "<msg>"` | Generate a new migration after model changes. |
| `docker compose run --rm backend alembic upgrade head` | Apply pending migrations. |
| `git status` | See what's changed locally. |
| `git add .` | Stage all changes. |
| `git commit -m "msg"` | Snapshot staged changes. |
| `git push` | Upload commits to GitHub. |

---

## 6. Generated artifacts to commit

After step 4.3 finishes, a new file appears at:

```
backend/alembic/versions/<hash>_init_schema.py
```

Commit it:

```bash
git add backend/alembic/versions/
git commit -m "Add initial Alembic migration"
git push
```

This is what makes your schema reproducible — anyone cloning the repo runs `docker compose run --rm backend alembic upgrade head` and gets the same tables.
