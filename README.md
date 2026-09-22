# Realtime-task-api

[![CI](https://github.com/jerryszc/Realtime-task-api/actions/workflows/ci.yml/badge.svg)](https://github.com/jerryszc/Realtime-task-api/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

# Real-Time Collaborative Task Management API

> **Executive Summary:** Production-ready asynchronous backend for collaborative task management featuring JWT authentication, strict RBAC (owner/admin/member), native WebSocket real-time broadcasting across board and workspace channels, and comprehensive test coverage.

---

## The Business Problem

Modern collaborative tools require:
1. **Real-time synchronization** — Multiple users editing boards/tasks simultaneously without polling or stale state.
2. **Granular access control** — Workspace-level roles (owner, admin, member) with distinct permissions for creating boards, managing members, and modifying tasks.
3. **Audit-grade authentication** — Short-lived access tokens with refresh rotation, bcrypt password hashing, and token revocation on logout.

---

## Engineering Solution Implemented

* **Async-First Architecture:** FastAPI + `async`/`await` throughout (routers, services, WebSocket handlers) for high concurrency on I/O-bound operations.
* **Strict RBAC Enforcement:** Dependency-injected guards (`require_workspace_admin`, `require_workspace_member`) at router level; service-layer `require_membership`/`require_role` for defense-in-depth.
* **Native WebSocket Real-Time Layer:** `ConnectionManager` with isolated rooms (`board:{id}`, `workspace:{id}`) broadcasting typed events (`task.created`, `task.updated`, `task.moved`, `task.deleted`). Token-validated connections (4401 unauthorized, 4403 forbidden).
* **JWT Token Rotation:** Access tokens (30 min default) + refresh tokens (7 days) stored as SHA-256 hashes with revocation support; `jti` claim for uniqueness.
* **Schema-Driven Validation:** Pydantic v2 models for all request/response payloads — enums (`TaskStatus`, `TaskPriority`, `WorkspaceRole`) reject invalid values at boundary (`422`).
* **Automated Quality Gates:** GitHub Actions CI running `ruff` lint + `pytest` suite (auth flow, RBAC, filters, WebSocket manager) on every push/PR.

---

## Tech Stack & Versions

| Technology | Version | Purpose |
| :--- | :--- | :--- |
| **Python** | 3.11+ | Core runtime, type hints, `asyncio` |
| **FastAPI** | 0.141.1 | Async web framework, auto OpenAPI |
| **SQLModel** | 0.0.42 | ORM + Pydantic unification |
| **SQLAlchemy** | 2.0.54 | Core engine, `pool_pre_ping` |
| **PostgreSQL** | 16 (prod) / SQLite (tests) | Relational persistence, ACID |
| **psycopg2-binary** | 2.9.13 | PostgreSQL driver |
| **Alembic** | 1.20.0 | Versioned migrations (`alembic revision --autogenerate`) |
| **python-jose** | 3.5.0 | JWT encode/decode (HS256) |
| **bcrypt** | 5.0.0 | Password hashing |
| **pydantic / pydantic-settings** | 2.13.5 / 2.15.0 | Validation & 12-factor config |
| **Uvicorn** | 0.53.0 | ASGI server |
| **Pytest / HTTPX** | 9.1.1 / 0.28.1 | Testing (SQLite `StaticPool` isolation) |
| **Ruff** | Latest | Linting (line-length 100, configured ignores) |
| **Docker / Compose** | Latest | Containerized `api` + `postgres:16` |

---

## Architecture Overview

### Module Structure
```
app/
├── core/
│   ├── config.py       # Pydantic-Settings from .env
│   ├── security.py     # bcrypt + JWT (access/refresh + rotation)
│   └── deps.py         # HTTPBearer auth, RBAC dependencies
├── db/
│   └── session.py      # SQLAlchemy engine + session generator
├── models/             # SQLModel tables (User, RefreshToken, Workspace, WorkspaceMember, Board, Task)
├── schemas/            # Pydantic request/response models
├── routers/            # REST + WebSocket endpoints
│   ├── auth.py         # register, login, refresh, logout, me
│   ├── workspaces.py   # CRUD + member management (admin only)
│   ├── boards.py       # CRUD + task listing with filters
│   ├── tasks.py        # CRUD + move (status/position) + WS notify
│   └── ws.py           # /ws/boards/{id}, /ws/workspaces/{id}
├── services/           # Business logic (auth_service, workspace_service, board_service, task_service, ws_manager)
├── main.py             # FastAPI app, router registration, /health
└── __init__.py
```

### Domain Model (ER)
```
User (1) ───< (M) RefreshToken
    │
    ├──< (M) Workspace (owner) ───< (M) Board ───< (M) Task
    │                                │
    │                                └─── assignee (User, nullable)
    │
    └──< (M) WorkspaceMember (composite PK: workspace_id, user_id)
              │
              └── role: Enum(owner, admin, member)
```

* **Workspace:** Unique `slug` (human-readable ID), `owner_id` FK to User.
* **WorkspaceMember:** Join table with `WorkspaceRole` enum; composite PK prevents duplicate membership.
* **Board:** Belongs to workspace; cascades to tasks.
* **Task:** Kanban-ready — `status` (todo/in_progress/done), `priority` (low/medium/high), `position` (float for drag-drop ordering), optional `assignee_id`, `due_date`.

---

## Concurrency & Real-Time Guarantees

| Layer | Mechanism |
| :--- | :--- |
| **Database** | `pool_pre_ping=True` for connection health; transactions via context-manager sessions (`session.commit()`/`rollback()` in `try/except/finally` blocks in all services). |
| **WebSocket Auth** | Token validated on connect via `security.decode_token()`; membership checked via `WorkspaceMember` lookup before `manager.connect()`. |
| **Broadcast** | `ConnectionManager` uses `defaultdict(set[WebSocket])` per room; `broadcast_to_room` iterates snapshot (`list(...)`) to avoid mutation during send; failed sends auto-disconnect. |
| **Event Payload** | `{ "event": "task.created|updated|moved|deleted", "board_id": int, "task_id": int, "workspace_id": int (workspace channel) }` |

---

## API Reference

Base URL: `http://localhost:8001` (Docker) or `http://localhost:8000` (local)

### Health
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Liveness probe → `{"status": "ok"}` |

### Authentication (`/auth`)
| Method | Path | Body | Response | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/register` | `UserCreate` (email, password, full_name) | `201 UserRead` | `409` if email exists |
| `POST` | `/login` | `LoginRequest` (email, password) | `200 TokenPair` | Sets `RefreshToken` hash in DB |
| `POST` | `/refresh` | `RefreshRequest` (refresh_token) | `200 TokenPair` | Rotates: revokes old, issues new pair |
| `POST` | `/logout` | `LogoutRequest` (refresh_token optional) | `204` | Revokes all or specific refresh token |
| `GET` | `/me` | — | `200 UserRead` | Requires `Bearer <access_token>` |

### Workspaces (`/workspaces`)
| Method | Path | Auth | Response | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/workspaces` | `Bearer` | `201 WorkspaceRead` | Creator becomes `owner` |
| `GET` | `/workspaces` | `Bearer` | `200 List[WorkspaceRead]` | Only workspaces user is member of |
| `POST` | `/workspaces/{id}/members` | `Bearer` (admin/owner) | `201 MemberRead` | `403` if not admin; `409` if already member |

### Boards (`/boards`, `/workspaces/{id}/boards`)
| Method | Path | Auth | Response | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/boards` | `Bearer` (admin/owner) | `201 BoardRead` | Requires `workspace_id` in body |
| `GET` | `/workspaces/{id}/boards` | `Bearer` (member) | `200 List[BoardRead]` | |
| `GET` | `/boards/{id}` | `Bearer` (member) | `200 BoardRead` | |

### Tasks (`/tasks`, `/boards/{id}/tasks`)
| Method | Path | Auth | Response | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/tasks` | `Bearer` (member) | `201 TaskRead` | Broadcasts `task.created` |
| `PATCH` | `/tasks/{id}` | `Bearer` (member) | `200 TaskRead` | Partial update; broadcasts `task.updated` |
| `POST` | `/tasks/{id}/move` | `Bearer` (member) | `200 TaskRead` | `TaskMove` (status/position); broadcasts `task.moved` |
| `DELETE` | `/tasks/{id}` | `Bearer` (member) | `204` | Broadcasts `task.deleted` |
| `GET` | `/boards/{id}/tasks` | `Bearer` (member) | `200 List[TaskRead]` | Filters: `status`, `priority`; pagination: `skip`, `limit` (max 100) |

### WebSocket Real-Time
| Channel | URL | Auth | Events Received |
| :--- | :--- | :--- | :--- |
| **Board** | `/ws/boards/{board_id}?token=<access_token>` | Valid access token + board membership | `task.created`, `task.updated`, `task.moved`, `task.deleted` |
| **Workspace** | `/ws/workspaces/{workspace_id}?token=<access_token>` | Valid access token + workspace membership | All board events within workspace (includes `workspace_id` in payload) |

> **Connection Codes:** `4401` = invalid/missing token, `4403` = not a member.

---

## Quick Start

### Option A: Docker Compose (Recommended)

```bash
# 1. Clone & configure
git clone <repo-url>
cd Proyecto2
cp .env.example .env
# Edit .env: set strong SECRET_KEY (min 32 chars), DB credentials

# 2. Build & run (API on 8001, Postgres on 5433)
docker compose up -d --build

# 3. Run migrations (inside API container or locally with DB exposed)
docker compose exec api alembic upgrade head
# Or locally:
# DATABASE_URL=postgresql+psycopg2://taskuser:taskpass@localhost:5433/taskdb alembic upgrade head

# 4. Verify
curl http://localhost:8001/health
# Swagger UI: http://localhost:8001/docs
```

**Service Map:**
| Service | Internal Port | External Port | Notes |
| :--- | :--- | :--- | :--- |
| `db` | 5432 | 5433 | `postgres:16`, volume `postgres_data`, `pg_isready` healthcheck |
| `api` | 8000 | 8001 | Hot-reload via volume mount `./app:/code/app` |

**Stop/Reset:**
```bash
docker compose down           # Keep data
docker compose down -v        # Delete postgres_data volume
```

---

### Option B: Local Development (Fast Iteration)

```bash
# 1. Virtual environment
python -m venv venv
source venv/Scripts/activate    # Git Bash / Windows
pip install -e ".[test]"        # Installs package + test deps (pytest, httpx)

# 2. Local PostgreSQL (or use Docker db only)
# Ensure Postgres 16 running on localhost:5433 with DB/taskdb
cp .env.example .env
# Edit .env with local credentials

# 3. Migrate
alembic upgrade head

# 4. Run API with reload
uvicorn app.main:app --reload --port 8000

# 5. Run tests (SQLite in-memory, fully isolated)
pytest -v
# Expected: all tests pass (auth, RBAC, filters, WS manager)
```

---

## Testing Strategy

**Framework:** `pytest` + `TestClient` (Starlette) + SQLite in-memory (`StaticPool`) per test.

**Test Modules:**
| File | Coverage |
| :--- | :--- |
| `test_api.py` | Health, register/login/refresh/me, full workspace→board→task→move flow |
| `test_rbac.py` | Owner vs member vs outsider: admin-only member add, board create, board list access |
| `test_task_filters.py` | Status/priority filters, pagination bounds, invalid enum rejection (`422`) |
| `test_ws.py` | `ConnectionManager` unit tests (connect/disconnect/broadcast), WS auth rejection (missing/invalid token) |
| `test_security.py` | Password hashing, token decode/verify |

**Run Commands:**
```bash
pytest -v                    # Verbose
pytest -x                    # Stop on first failure
pytest -k "rbac"             # Keyword filter
pytest tests/test_ws.py      # Single module
```

---

## Database Migrations (Alembic)

```bash
# Generate migration (autogenerate from model changes)
alembic revision --autogenerate -m "descriptive message"

# Apply
alembic upgrade head

# Rollback one
alembic downgrade -1

# History
alembic history --verbose
```

*Config:* `alembic.ini` → `script_location = alembic`; `env.py` reads `settings.DATABASE_URL`.

---

## Environment Variables (`.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+psycopg2://taskuser:taskpass@localhost:5433/taskdb` | SQLAlchemy URL |
| `SECRET_KEY` | *required* | JWT signing key (min 32 chars, **never commit**) |
| `POSTGRES_USER` | `taskuser` | DB user (for Compose) |
| `POSTGRES_PASSWORD` | `taskpass` | DB password (for Compose) |
| `POSTGRES_DB` | `taskdb` | DB name (for Compose) |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |

> **Security:** `.env` is gitignored. Use `.env.example` as template. Generate `SECRET_KEY` with: `openssl rand -hex 32`.

---

## CI/CD (GitHub Actions)

Workflow (`.github/workflows/ci.yml` — inferred from project structure):
1. **Lint:** `ruff check .` (line-length 100, configured ignores)
2. **Test:** `pytest -v` against SQLite in-memory
3. Runs on every `push` and `pull_request` to `main`

---

## Project Structure

```
.
├── .github/workflows/        # CI pipelines (ruff + pytest)
├── alembic/                  # Migration scripts + env.py
├── app/
│   ├── core/                 # config, security (JWT+bcrypt), deps (auth+RBAC)
│   ├── db/                   # SQLAlchemy engine + session
│   ├── models/               # 5 SQLModel tables + 3 enums
│   ├── schemas/              # Pydantic request/response models
│   ├── routers/              # 5 REST routers + 1 WS router
│   ├── services/             # Business logic + ConnectionManager
│   └── main.py               # FastAPI entrypoint
├── tests/                    # 6 test modules (conftest, api, rbac, filters, ws, security)
├── .dockerignore
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml            # Package metadata, deps, ruff/pytest config
├── requirements.txt          # Pinned deps (mirrors pyproject.toml)
└── README.md
```

---

## License

MIT — Free for personal and commercial use.
