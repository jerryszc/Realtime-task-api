# Realtime Task API — Collaborative Boards over WebSockets

**[Versión en español →](README.md)**

Collaborative Kanban-style board API with real-time updates over WebSockets, room-scoped
isolation, three-role RBAC and refresh tokens stored as hashes.

[![CI](https://github.com/jerryszc/Realtime-task-api/actions/workflows/ci.yml/badge.svg)](https://github.com/jerryszc/Realtime-task-api/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-009688.svg)](https://fastapi.tiangolo.com/)
[![MyPy strict](https://img.shields.io/badge/mypy-strict%20%7C%20passed-brightgreen.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-11%20passing%20%7C%20coverage%20gate%2070%25-brightgreen.svg)](tests)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Stack:** Python 3.11 · FastAPI · WebSockets · SQLModel · PostgreSQL 16 · Alembic · bcrypt · PyJWT (python-jose) · Pytest · Ruff · MyPy strict · Docker

---

## The business problem

In a collaborative work tool, storing the task is not the problem: the problem is that
people collide over it. These four failures dominate the real cost of the product.

### 1. Two people start the same task because neither knows the other did

| Behaviour | Consequence |
| :--- | :--- |
| The board only refreshes when the page reloads | A colleague moved a task to "In progress" ten minutes ago. You open it, set it to "In progress" too, and you both work on it. An hour of duplicated work, wasted |
| Polling every few seconds | 12 requests per user per minute, most returning "nothing changed". With 50 users that is 600 requests/minute of which 95% is discarded. The database pays the cost of traffic that carries no information |

**What this service does:** when a task is created, updated, moved or deleted, the server
**pushes** the event to the open connections on that board. No reload, no polling, and
network traffic scales with actual changes rather than with the number of people watching
the screen.

### 2. Data leaking between tenants in a multi-tenant application

A SaaS management product where 40 people hang off the same workspace. A mistake in the
broadcast means company A receives company B's movements: not a visible bug, but a data
leak that destroys trust in the product and can cost the customer.

**What this service does:** connections live in named **rooms**, not on a single global bus.
Each board and each workspace is a separate room, and an event is only broadcast inside the
matching room.

### 3. A WebSocket connection is a back door into authorisation

This is the easiest security mistake to introduce and the hardest to detect. A WebSocket is
a long-lived connection: **if it is accepted without verification, the request rides on
process state**, and the authorisation checked at handshake time stops applying. The user
keeps receiving events from that resource even after their permission is revoked or they are
removed from the workspace.

**What this service does:** authorisation is checked **at the handshake**, before accepting
the connection, against the token supplied in the query string (browsers do not allow
custom headers in `new WebSocket()`).

```python
@router.websocket("/ws/boards/{board_id}")
async def board_ws(websocket: WebSocket, board_id: int, token: str | None = None) -> None:
    if not token:
        await websocket.close(code=4401)   # no credentials
        return
    ...                                        # board membership check
        await websocket.close(code=4403)   # no permission
    await manager.connect(board_id, websocket)
```

**The close codes are non-standard on purpose.** 4401 and 4403 sit in the private range
(`4000-4999`) defined by RFC 6455, so the client can tell "your credentials expired" apart
from "you lack permission" and from a normal network close, and react differently to each:
reauthenticate, request access, or reconnect. With the generic 1005 code there would be no
way to know what happened.

---

## Verifiable impact

**11 tests** across 5 modules, with a **70% coverage gate** set in `addopts`, so CI fails if
coverage drops below that threshold.

| Behaviour | Test that proves it |
| :--- | :--- |
| The register → login → refresh cycle works | `test_register_login_refresh` |
| The full workspace → board → task flow works | `test_workspace_board_task_flow` |
| A member without admin permission gets the expected rejection | `test_member_rbac_admin_only` |
| A connection with no token is rejected | `test_ws_rejects_missing_token` |
| A connection with an invalid token is rejected | `test_ws_rejects_invalid_token` |
| The manager keeps board and workspace rooms separate | `test_manager_board_and_workspace_rooms` |
| An invalid enum in a filter is rejected with 422 | `test_invalid_enum_rejected_422` |
| Task pagination and filters work | `test_pagination_and_filters` |
| The password hash round-trips | `test_password_hashing` |
| The token signs and verifies correctly | `test_token_roundtrip` |

**The cost of this test suite, stated plainly:** 11 tests are functionally solid but
quantitatively the smallest of the four projects. It is the first place I would extend if I
kept working on this.

---

## Architecture

```
app/
├── main.py                  # Routers + WebSockets
├── core/
│   ├── config.py            # Pydantic Settings
│   ├── security.py          # bcrypt + JWT (python-jose)
│   └── deps.py              # get_current_user
├── db/
│   └── session.py           # Engine and per-request session
├── models/
│   ├── user.py              # User, RefreshToken
│   ├── workspace.py         # Workspace, WorkspaceMember, WorkspaceRole
│   ├── board.py             # Board
│   └── task.py              # Task, TaskStatus, TaskPriority
├── schemas/                 # Request/response contracts
├── routers/
│   ├── auth.py              # register, login, refresh, logout, me
│   ├── workspaces.py        # Create and list workspaces
│   ├── boards.py            # Create, list, detail, tasks
│   ├── tasks.py             # CRUD + move
│   └── ws.py                # Handshake and rooms
└── services/
    ├── auth_service.py      # Login, refresh, logout
    ├── board_service.py
    ├── task_service.py
    ├── workspace_service.py
    └── ws_manager.py        # ConnectionManager
```

**The connection manager** keeps rooms as a `defaultdict(set)` of WebSockets keyed by room
name. Keys are derived with an explicit prefix, so a board with `id = 1` and a workspace
with `id = 1` **never** share a room:

```python
self.rooms: dict[str, set[WebSocket]] = defaultdict(set)

def board_room(board_id: int) -> str:
    return f"board:{board_id}"

def workspace_room(workspace_id: int) -> str:
    return f"workspace:{workspace_id}"
```

That prefix is the tenant isolation boundary. It is one line of code that prevents a
cross-customer data leak.

**Broadcasting is hierarchical:** a task change notifies the board and, additionally, the
workspace that contains it, so someone watching the team board receives it too.

---

## Data model

**6 tables** and 2 enums.

| Table | Key fields |
| :--- | :--- |
| `user` | `email`, `hashed_password` (bcrypt), `full_name` |
| `refresh_token` | `token_hash` (SHA-256, UNIQUE, index), `user_id`, `expires_at`, `revoked` |
| `workspace` | `name`, `owner_id` (FK) |
| `workspace_member` | `workspace_id`, `user_id`, `role` (`owner`/`admin`/`member`) |
| `board` | `name`, `workspace_id` (FK) |
| `task` | `title`, `description`, `board_id` (FK), `status`, `priority`, `position`, `assignee_id` |

**Enums:** `TaskStatus` (`todo` / `in_progress` / `done`) and `TaskPriority`
(`low` / `medium` / `high`).

**`position` as a decimal.** Ordering columns in a Kanban are not indexed as integers
because moving a card from the start to the end would force renumbering everything else. A
decimal value allows inserting between two positions without touching the rest.

---

## API

### Authentication
| Method | Path | Description |
| :--- | :--- | :--- |
| POST | `/auth/register` | Create account (201) |
| POST | `/auth/login` | Returns access + refresh |
| POST | `/auth/refresh` | Rotates the refresh token |
| POST | `/auth/logout` | Revokes refresh tokens (204) |
| GET | `/auth/me` | Authenticated user |

### Workspaces and boards
| Method | Path | Description |
| :--- | :--- | :--- |
| POST | `/workspaces` | Create workspace (201) |
| GET | `/workspaces` | List the user's workspaces |
| POST | `/boards` | Create board (201) |
| GET | `/workspaces/{workspace_id}/boards` | Boards in a workspace |
| GET | `/boards/{board_id}` | Board detail |
| GET | `/boards/{board_id}/tasks` | Board tasks, with filters and pagination |

### Tasks
| Method | Path | Description |
| :--- | :--- | :--- |
| POST | `/tasks` | Create task (201), broadcasts `task.created` |
| PATCH | `/tasks/{id}` | Update, broadcasts `task.updated` |
| POST | `/tasks/{id}/move` | Move between columns, broadcasts `task.moved` |
| DELETE | `/tasks/{id}` | Delete, broadcasts `task.deleted` |

### WebSockets
| Path | Description |
| :--- | :--- |
| `/ws/boards/{board_id}?token=<JWT>` | Board room. Closes 4401 with no token, 4403 without permission |
| `/ws/workspaces/{workspace_id}?token=<JWT>` | Workspace room, same rules |

**The four emitted events**

```json
{"event": "task.moved", "board_id": 7, "task_id": 42}
{"event": "task.moved", "board_id": 7, "task_id": 42, "workspace_id": 3}
```

The first reaches the board room; the second, the workspace room.

**JavaScript client**

```javascript
const ws = new WebSocket(
  `ws://localhost:8000/ws/boards/7?token=${accessToken}`
);

ws.onmessage = (e) => {
  const { event, task_id } = JSON.parse(e.data);
  if (event === "task.moved") reloadColumn();
};

ws.onclose = (e) => {
  if (e.code === 4401) reauthenticate();   // credentials expired
  if (e.code === 4403) requestAccess();    // no permission
};
```

---

## Authorisation

Three roles per workspace, in `WorkspaceRole`:

| Role | Permissions |
| :--- | :--- |
| `owner` | Full control of the workspace, including ownership |
| `admin` | Manages the workspace's boards and tasks |
| `member` | Works on tasks; does not administer structure |

RBAC is checked at two points: on the HTTP endpoints and **again at the WebSocket
handshake**. The duplication is intentional, because they are two distinct entry paths, and
validating only one leaves the other open.

---

## Security

**Passwords:** `bcrypt` with a `gensalt()`-generated salt.

**Refresh tokens: SHA-256, never plaintext.** This is the point that matters most and the
one most often forgotten. Storing the refresh token as-is in the database means a database
leak hands over session tokens that are **valid and usable**. Here only the digest is
stored:

```python
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
```

That SHA-256 is acceptable here while bcrypt is not comes down to the nature of the value:
a password is chosen by a person and can be brute-forced, so it needs a **slow** algorithm;
a refresh token is generated by the server with full entropy, so there is no dictionary to
try and a **fast** hash is enough to ensure a database read cannot be used to authenticate.

**Access tokens:** 30 minutes, JWT HS256 via `python-jose`.
**Refresh tokens:** 7 days, rotated on every use, with a `revoked` flag.
**Logout revokes** all of the user's refresh tokens, or only the supplied one.

---

## Tests

**11 tests** across 5 modules.

| Module | Tests | Covers |
| :--- | :--- | :--- |
| `test_api.py` | 3 | Health, register/login/refresh, workspace → board → task flow |
| `test_ws.py` | 3 | Board and workspace rooms, rejection with no token, rejection with invalid token |
| `test_security.py` | 2 | Password hashing, token round-trip |
| `test_task_filters.py` | 2 | Pagination and filters, invalid enum rejected with 422 |
| `test_rbac.py` | 1 | A member cannot perform admin actions |

```bash
pytest                                    # applies the 70% gate automatically
pytest --cov=app --cov-report=term-missing
pytest -k "ws or rbac"                    # WebSockets and permissions only
```

**The tests use in-memory SQLite** (`sqlite://` with `StaticPool`), with no external
services and no migrations. That is what keeps the suite fast, but it carries a cost worth
stating: behaviour is validated against SQLite, not PostgreSQL.

---

## Continuous integration

`.github/workflows/ci.yml` defines **4 jobs** in parallel plus a failure aggregator.

| Job | What it does |
| :--- | :--- |
| **Lint** | `ruff check .` and `ruff format --check .` |
| **Typecheck** | `mypy app` with `strict = true` |
| **Tests** | `pytest` with coverage and the 70% gate |
| **Docker Build & Smoke Test** | Builds the image, brings up compose and checks `/health` on port **8001** |
| **Notify on Failure** | `needs: [lint, typecheck, test, docker]` |

Unlike the SSO project, this CI does **not** start PostgreSQL or Redis: the workflow states
explicitly that the tests require no services or migrations, while the smoke test does verify
that the image boots and responds.

**Configuration:** Ruff with `line-length = 100`; MyPy with `strict = true`; the 70%
coverage gate in `addopts` in `pyproject.toml`.

---

## Quick start

**Requirements:** Docker Desktop running.

```bash
# 1. Clone and enter
git clone https://github.com/jerryszc/Realtime-task-api.git
cd Realtime-task-api

# 2. Configure
cp .env.example .env
#   First thing: change SECRET_KEY

# 3. Bring up
docker compose up --build -d

# 4. Verify
curl http://localhost:8001/health

# 5. Docs
#    http://localhost:8001/docs
```

> The default port in Docker Compose is **8001**, to avoid clashing with another local
> service on 8000.

```bash
docker compose down
docker compose down -v
```

### Local development without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic current
```

---

## Environment variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | `change-me-in-env` | **Change in production.** JWT signing key |
| `ALGORITHM` | `HS256` | Signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@db:5432/realtime` | PostgreSQL connection |

---

## Scope and limitations

- **Tests run on in-memory SQLite**, not PostgreSQL. Behaviour is verified, but not the
  production database's behaviour.
- **The `ConnectionManager` is in-memory and per-process.** With multiple replicas, a
  client connected to replica A does not receive events emitted on replica B. The natural
  next step is a bus (Redis Pub/Sub or similar) behind the same interface.
- **No automatic token renewal on the WebSocket.** Because the connection is long-lived, a
  30-minute token expires while the socket stays open; reconnecting with a new token is
  what resolves this, and automatic renewal is not implemented.
- **No cursor pagination**: pagination is `skip`/`limit`.

---

## License

MIT — free for commercial and educational use. See [LICENSE](LICENSE).
