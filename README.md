# Real-Time Collaborative Task Management API

A modern, production-ready backend built with FastAPI for collaborative task management, optimized with asynchronous architecture, Role-Based Access Control (RBAC), real-time WebSockets, and automated testing.

---

## Tech Stack & Architecture

- **Framework:** FastAPI with asynchronous request handling.
- **Database & ORM:** PostgreSQL 16 managed via SQLModel / SQLAlchemy with Alembic migrations (`revision --autogenerate`, strict prohibition of manual DDL).
- **Real-Time Layer:** Native WebSockets with independent rooms (`board:{id}` and `workspace:{id}`) and event broadcasting (`task.created/updated/moved/deleted`) managed by a custom `ConnectionManager`.
- **Security & Auth:** JWT authentication (`access_token`, `refresh_token`), bcrypt encryption, and `HTTPBearer`.
- **Access Control:** Strict RBAC based on roles (`owner`, `admin`, `member`).
- **Testing & Quality:** Pytest, HTTPX (with isolated in-memory SQLite for testing), and Pydantic schema validation.
- **CI/CD Pipeline:** Automated GitHub Actions workflows running code linters (`ruff`) and integration test suites (`pytest`) on every push/PR.

---

## Installation & Quick Start (Docker)

Make sure you have Docker and Docker Compose installed on your system.

1. **Configure environment variables:**

   Create your `.env` file based on the example template (`.env.example`):

   ```bash
   cp .env.example .env
   ```

2. **Start the containers:**

   ```bash
   docker compose up -d --build
   ```

3. **Check container status:**

   ```bash
   docker compose ps
   ```

4. **Apply database migrations:**

   ```bash
   DATABASE_URL=postgresql+psycopg2://taskuser:taskpass@localhost:5433/taskdb alembic upgrade head
   ```

- **Database Host & Port:** `localhost:5433` (internal network isolation)
- **API Base URL:** `http://localhost:8001`
- **Interactive Documentation (Swagger UI):** `http://localhost:8001/docs`

---

## Swagger Usage Guide

### Authentication

1. Execute `POST /auth/register` to register and `POST /auth/login` to log in.
2. Copy your `access_token`, click the **Authorize** button in Swagger, and paste it as `Bearer <access_token>`.

### Structure & Permissions

1. Create workspaces (`POST /workspaces`) and add members assigning roles (`POST /workspaces/{id}/members`) under strict RBAC validation (`owner`/`admin`).
2. Create boards (`POST /boards`) and manage tasks (`POST /tasks`, `POST /tasks/{id}/move`).

### Filtering & Pagination

Query tasks applying advanced filters by status and priority:

```http
GET /boards/{id}/tasks?skip=0&limit=50&status=done&priority=high
```

> Invalid enum values (e.g. `status=archived`, `priority=urgent`) are rejected with `422`.

### WebSockets (Real-Time)

Connect to real-time channels passing your access token as a query parameter (connections without valid tokens are rejected):

- Board channel: `/ws/boards/{board_id}?token=<access_token>`
- Workspace channel: `/ws/workspaces/{workspace_id}?token=<access_token>`

---

## Running the Test Suite (Pytest)

To run unit and integration tests locally:

```bash
pip install -e ".[test]"
python -m pytest tests -v
```

The comprehensive test suite covers authentication, workspace/member/RBAC flows, boards, pagination, advanced filters, enum validation (`403` and `422`, e.g. `priority=urgent` or `status=archived`), and WebSocket stability via `ConnectionManager`.

---

## Environment Variables

The project requires an `.env` file (which is strictly ignored by Git). Use `.env.example` as a reference:

- `DATABASE_URL`
- `SECRET_KEY`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
