# Real-Time Collaborative Task Management API

API colaborativa de gestion de tareas en tiempo real: workspaces con RBAC (`owner/admin/member`), boards Kanban, tasks con paginacion/filtros y notificaciones WebSocket por board y workspace. Auth JWT (`access_token` + `refresh_token`, `bcrypt`, esquema `HTTPBearer`).

## Stack
- FastAPI + SQLModel + Pydantic Settings
- PostgreSQL 16 + Alembic (solo `revision --autogenerate`, prohibido DDL manual)
- Docker + Docker Compose (volumen `postgres_data`, red `internal`, healthchecks)
- WebSockets (rooms `board:{id}` / `workspace:{id}`, eventos `task.created/updated/moved/deleted`)
- Pytest + Httpx (SQLite aislada en memoria)
- GitHub Actions (lint `ruff` + `pytest` en cada push/PR)

## Instalacion y ejecucion rapida con Docker (Git Bash, paths `/`)
```
cp .env.example .env
docker compose up -d --build
docker compose ps
DATABASE_URL=postgresql+psycopg2://taskuser:taskpass@localhost:5433/taskdb alembic upgrade head
```
- API: `http://localhost:8001` · Docs: `http://localhost:8001/docs` · DB host: `localhost:5433`
- Uso: `POST /auth/register` -> `POST /auth/login` -> en Swagger `Authorize` pegar el `access_token` como `Bearer` -> `POST /workspaces` -> `POST /workspaces/{id}/members` (solo `owner/admin`) -> `POST /boards` (solo `owner/admin`) -> `POST /tasks` -> `POST /tasks/{id}/move`.
- Filtros: `GET /boards/{id}/tasks?skip=0&limit=50&status=done&priority=high`.
- WS: `/ws/boards/{board_id}?token=<access>` y `/ws/workspaces/{workspace_id}?token=<access>`.

## Ejecutar la suite de pruebas (`pytest`)
```
pip install -e ".[test]"
python -m pytest tests -v
```
Cubre autenticacion, workspaces/miembros/RBAC (`403`), tableros, paginacion/filtros y validacion de enums con `422` (`priority=urgent`, `status=archived`), `ConnectionManager` y rechazo WS sin token.

## Variables de entorno
Ver `.env.example` (plantilla sin credenciales reales): `DATABASE_URL`, `SECRET_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`. El `.env` real esta ignorado por git.
