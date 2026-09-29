# Realtime Task API — Collaborative Boards over WebSockets

**[English version →](README.en.md)**

API colaborativa de tableros tipo Kanban con actualizaciones en tiempo real por WebSocket,
aislamiento por sala, RBAC de tres roles y refresh tokens almacenados como hash.

[![CI](https://github.com/jerryszc/Realtime-task-api/actions/workflows/ci.yml/badge.svg)](https://github.com/jerryszc/Realtime-task-api/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-009688.svg)](https://fastapi.tiangolo.com/)
[![MyPy strict](https://img.shields.io/badge/mypy-strict%20%7C%20passed-brightgreen.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-11%20passing%20%7C%20coverage%20gate%2070%25-brightgreen.svg)](tests)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Stack:** Python 3.11 · FastAPI · WebSockets · SQLModel · PostgreSQL 16 · Alembic · bcrypt · PyJWT (python-jose) · Pytest · Ruff · MyPy strict · Docker

---

## El problema empresarial

En una herramienta de trabajo colaborativo, el problema no es guardar la tarea: es que las
personas conflictúen sobre ella. Estas cuatro fallas dominan el costo real del producto.

### 1. Dos personas toman la misma tarea porque no saben que el otro la tomó

| Comportamiento | Consecuencia |
| :--- | :--- |
| El tablero solo se actualiza al recargar la página | Un compañero mueve una tarea a "En curso" hace diez minutos. Tú la abres, la cambias a "En curso" también, y trabajáis los dos sobre lo mismo. Una hora de trabajo duplicada que se pierde |
| Polling cada pocos segundos | 12 peticiones por usuario por minuto que en su mayoría devuelven "nada ha cambiado". Con 50 usuarios son 600 peticiones/minute de las cuales un 95% se descarta. La base de datos paga el coste de una tráfico que no aporta información |

**Lo que hace este servicio:** cuando una tarea se crea, se actualiza, se mueve o se
elimina, el servidor **empuja** el evento a las conexiones abiertas de ese tablero. No hay
recarga, no hay polling, y el tráfico de red es proporcional a los cambios reales, no al
número de usuarios mirando la pantalla.

### 2. Fuga de datos entre clientes en una aplicación multi-tenant

Un SaaS de gestión donde 40 personas cuelgan el mismo espacio de trabajo. Un
error en el broadcast significa que la empresa A recibe los movimientos de la empresa B: no
un fallo visible, sino una fuga de datos que destruye la confianza en el producto y puede
costar la retención del cliente.

**Lo que hace este servicio:** las conexiones viven en **salas** nombradas, no en un único
bus global. Cada tablero y cada espacio de trabajo son salas separadas, y un evento solo se
difunde dentro de la sala correspondiente.

### 3. Una conexión WebSocket es una puerta trasera a la autorización

Este es el fallo de seguridad más fácil de introducir y el más difícil de detectar. Un
WebSocket es una conexión de larga duración: **si se acepta sin verificar, la petición
pasa por el estado del proceso** y la autorización checked en el momento del handshake deja
de aplicarse. El usuario conserva acceso a los eventos de ese recurso aunque se le revoque
el permiso o se elimine del espacio de trabajo.

**Lo que hace este servicio:** la autorización se comprueba **en el handshake**, antes de
aceptar la conexión, contra el token que llega en la query string (los navegadores no
permiten cabeceras personalizadas en `new WebSocket()`).

```python
@router.websocket("/ws/boards/{board_id}")
async def board_ws(websocket: WebSocket, board_id: int, token: str | None = None) -> None:
    if not token:
        await websocket.close(code=4401)   # sin credenciales
        return
    ...                                        # verificación de pertenencia al board
        await websocket.close(code=4403)   # sin permiso
    await manager.connect(board_id, websocket)
```

Los **códigos de cierre no son estándar a propósito**. 4401 y 4403 son el rango privado
(`4000-4999`) definido por la RFC 6455, así que el cliente puede distinguir "tus
credenciales caducaron" de "no tienes permiso" y de un cierre de red normal, y reacts en
cada caso: reautenticarse, pedir acceso, o reconectar. Con el código 1005 genérico sería
imposible saber qué pasó.

---

## Contexto de uso

Una API de WebSockets sólo tiene sentido donde el retraso se paga: cuando la persona está
mirando la pantalla y espera que el cambio ya esté ahí. En un CRUD HTTP, recargar es un
clic y un coste de un segundo. En un tablero colaborativo, recargar significa que dos
personas trabajen sobre información equivocada.

**Dónde encaja dentro de un producto real**

| Contexto | Cómo se usa | Por qué este diseño |
| :--- | :--- | :--- |
| **Tablero Kanban dentro de un SaaS de equipos** | El módulo de colaboración de una herramienta tipo Trello o Linear | El servidor empuja `task.created`, `task.updated`, `task.moved` y `task.deleted` a las conexiones abiertas de ese tablero, así que una persona mueve una tarea y la ve el resto sin recargar |
| **Herramienta interna de una empresa con varios pisos** | Seguimiento de incidencias compartido entre equipos | Las salas por workspace evitan que el tráfico de un equipo se mezcle con el de otro, que es el problema clásico de un WebSocket compartido |
| **Panel de operaciones con varios tenants** | Cada cliente ve únicamente sus propios tableros | El `workspace_id` va en el mensaje de suscripción, y el servidor valida la pertenencia antes de registrar la conexión, no después de recibir datos |

**Qué aporta frente a REST con polling**

El coste de mantener el estado sincronizado no lo marca el número de usuarios, lo marca el
número de consultas que no encuentran nada:

- **El tráfico escala con los cambios, no con los espectadores.** Con 50 personas mirando un
  tablero quieto, el coste es cero: no hay nada que empujar. Con polling, serían 50
  peticiones por intervalo devolviendo "nada ha cambiado", y todas llegarían a la base de
  datos antes de descartarse.
- **El servidor es la fuente de la verdad.** Un cliente que aplica su propio parche puede
  divergir del servidor. Con eventos del servidor, todos convergen al mismo estado.
- **Los códigos de cierre distinguen el motivo.** `4401` significa "vuelve a
  autenticarte" y `4403` significa "puedes estar conectado pero no tienes permiso, deja de
  reintentar". Con el `1005` genérico de la RFC el cliente no puede diferenciar un token
  caducado de un acceso denegado, y termina reintentando en bucle.

**Qué tendría que añadirse antes de ponerlo en producción**

- **Redis Pub/Sub detrás del `ConnectionManager`.** Hoy el gestor de conexiones es un
  diccionario en memoria del proceso, así que con dos réplicas cada una solo notifica a sus
  propios clientes: el usuario conectado a la réplica A no ve lo que pasa en la B. Es el
  defecto estructural más importante de este proyecto, y también el más fácil de explicar en
  una entrevista.
- **Renovación del token en el cliente.** El access token dura 30 minutos. Cuando expira, la
  conexión abierta sigue viva y tampoco puede refrescar sola: hace falta que el cliente
  cierre, refresque y vuelva a conectar, o que el servidor envíe un aviso de expiración antes
  de que ocurra.
- **Límite de conexiones y de frecuencia por usuario.** Un bucle de reconexión mal escrito
  puede abrir cientos de conexiones contra el mismo usuario.
- **Pruebas contra PostgreSQL real en CI.** Los tests usan SQLite en memoria con `StaticPool`,
  que es rápido y cómodo pero no reproduce los bloqueos de fila ni los tipos de PostgreSQL.
  Los otros tres proyectos de este perfil ya lo hacen con contenedores de servicio.

**A qué puesto corresponde este trabajo**

Backend Developer en herramientas de colaboración, SaaS multi-tenant o productos en tiempo
real. Es el tipo de trabajo donde el detalle importa: un WebSocket que filtra datos entre
tenant es un incidente de seguridad, no un bug de rendimiento.

---

## Impacto verificable

**11 tests** en 5 módulos, con un gate de cobertura del **70%** definido en `addopts`, de
modo que la CI falla si la cobertura baja de ese umbral.

| Comportamiento | Test que lo demuestra |
| :--- | :--- |
| El ciclo registro → login → refresh funciona | `test_register_login_refresh` |
| El flujo completo espacio de trabajo → tablero → tarea funciona | `test_workspace_board_task_flow` |
| Un miembro sin permiso de administrador recibe el rechazo esperado | `test_member_rbac_admin_only` |
| La conexión sin token se rechaza | `test_ws_rejects_missing_token` |
| La conexión con token inválido se rechaza | `test_ws_rejects_invalid_token` |
| El gestor mantiene salas separadas de tablero y de espacio de trabajo | `test_manager_board_and_workspace_rooms` |
| Un enum inválido en un filtro se rechaza con 422 | `test_invalid_enum_rejected_422` |
| La paginación y los filtros de tareas funcionan | `test_pagination_and_filters` |
| El hash de contraseña hace round-trip | `test_password_hashing` |
| El token se firma y se verifica correctamente | `test_token_roundtrip` |

**El coste de esta base de tests, dicho con claridad:** 11 tests son una cobertura
funcionalmente sólida pero cuantitativamente la más baja de los cuatro proyectos. Es el
primer sitio donde ampliaría si tuviera que seguir trabajando en él.

---

## Arquitectura

```
app/
├── main.py                  # Routers + WebSockets
├── core/
│   ├── config.py            # Pydantic Settings
│   ├── security.py          # bcrypt + JWT (python-jose)
│   └── deps.py              # get_current_user
├── db/
│   └── session.py           # Engine y sesión por request
├── models/
│   ├── user.py              # User, RefreshToken
│   ├── workspace.py         # Workspace, WorkspaceMember, WorkspaceRole
│   ├── board.py             # Board
│   └── task.py              # Task, TaskStatus, TaskPriority
├── schemas/                 # Contratos de request/response
├── routers/
│   ├── auth.py              # register, login, refresh, logout, me
│   ├── workspaces.py        # Crear y listar espacios
│   ├── boards.py            # Crear, listar, detalle, tareas
│   ├── tasks.py             # CRUD + move
│   └── ws.py                # Handshake y salas
└── services/
    ├── auth_service.py      # Login, refresh, logout
    ├── board_service.py
    ├── task_service.py
    ├── workspace_service.py
    └── ws_manager.py        # ConnectionManager
```

**El gestor de conexiones** mantiene las salas como un `defaultdict(set)` de WebSockets
por nombre de sala. Las claves se derivan con prefijo explícito, de modo que un tablero con
`id = 1` y un espacio de trabajo con `id = 1` **nunca** comparten la misma sala:

```python
self.rooms: dict[str, set[WebSocket]] = defaultdict(set)

def board_room(board_id: int) -> str:
    return f"board:{board_id}"

def workspace_room(workspace_id: int) -> str:
    return f"workspace:{workspace_id}"
```

Ese prefijo es la barrera de aislamiento entre tenants. Es una línea de código que evita
una fuga de datos entre clientes.

**La difusión es bidireccional en jerarquía:** un cambio en una tarea notifica al tablero
y, además, al espacio de trabajo que lo contiene, para que quien esté mirando el tablero de
equipo también lo reciba.

---

## Modelo de datos

**6 tablas** y 2 enums.

| Tabla | Campos clave |
| :--- | :--- |
| `user` | `email`, `hashed_password` (bcrypt), `full_name` |
| `refresh_token` | `token_hash` (SHA-256, UNIQUE, index), `user_id`, `expires_at`, `revoked` |
| `workspace` | `name`, `owner_id` (FK) |
| `workspace_member` | `workspace_id`, `user_id`, `role` (`owner`/`admin`/`member`) |
| `board` | `name`, `workspace_id` (FK) |
| `task` | `title`, `description`, `board_id` (FK), `status`, `priority`, `position`, `assignee_id` |

**Enums:** `TaskStatus` (`todo` / `in_progress` / `done`) y `TaskPriority`
(`low` / `medium` / `high`).

**`position` como decimal.** Las columnas de orden en un Kanban no se indexan como enteros
porque mover una tarjeta del inicio al final obligaría a renumerar todas las demás. Un valor
decimal permite insertar entre dos posiciones sin tocar el resto.

---

## API

### Autenticación
| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| POST | `/auth/register` | Crear cuenta (201) |
| POST | `/auth/login` | Devuelve access + refresh |
| POST | `/auth/refresh` | Rota el refresh token |
| POST | `/auth/logout` | Revoca los refresh tokens (204) |
| GET | `/auth/me` | Usuario autenticado |

### Espacios de trabajo y tableros
| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| POST | `/workspaces` | Crear espacio (201) |
| GET | `/workspaces` | Listar los espacios del usuario |
| POST | `/boards` | Crear tablero (201) |
| GET | `/workspaces/{workspace_id}/boards` | Tableros de un espacio |
| GET | `/boards/{board_id}` | Detalle del tablero |
| GET | `/boards/{board_id}/tasks` | Tareas del tablero, con filtros y paginación |

### Tareas
| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| POST | `/tasks` | Crear tarea (201) y difundir `task.created` |
| PATCH | `/tasks/{id}` | Actualizar y difundir `task.updated` |
| POST | `/tasks/{id}/move` | Mover de columna y difundir `task.moved` |
| DELETE | `/tasks/{id}` | Eliminar y difundir `task.deleted` |

### WebSockets
| Ruta | Descripción |
| :--- | :--- |
| `/ws/boards/{board_id}?token=<JWT>` | Sala del tablero. Cierra 4401 sin token, 4403 sin permiso |
| `/ws/workspaces/{workspace_id}?token=<JWT>` | Sala del espacio de trabajo, mismas reglas |

**Los cuatro eventos emitidos**

```json
{"event": "task.moved", "board_id": 7, "task_id": 42}
{"event": "task.moved", "board_id": 7, "task_id": 42, "workspace_id": 3}
```

El primero llega a la sala del tablero; el segundo, a la del espacio de trabajo.

**Cliente JavaScript**

```javascript
const ws = new WebSocket(
  `ws://localhost:8000/ws/boards/7?token=${accessToken}`
);

ws.onmessage = (e) => {
  const { event, task_id } = JSON.parse(e.data);
  if (event === "task.moved") reloadColumn();
};

ws.onclose = (e) => {
  if (e.code === 4401) reauthenticate();   // credenciales caducadas
  if (e.code === 4403) requestAccess();    // sin permiso
};
```

---

## Autorización

Tres roles por espacio de trabajo, en `WorkspaceRole`:

| Rol | Permisos |
| :--- | :--- |
| `owner` | Control total del espacio, incluida la propiedad |
| `admin` | Administra tableros y tareas del espacio |
| `member` | Trabaja en las tareas; no administra la estructura |

El RBAC se comprueba en dos puntos: en los endpoints HTTP y **de nuevo en el handshake del
WebSocket**. La duplicación es intencional, porque son dos caminos de entrada distintos y
validar solo uno deja el otro abierto.

---

## Seguridad

**Contraseñas:** `bcrypt` con sal generada por `gensalt()`.

**Refresh tokens: SHA-256, nunca en texto plano.** Este es el punto que más importa y el
que más se olvida. Guardar el refresh token tal cual en la base de datos significa que una
fuga de la base de datos entrega tokens de sesión **válidos y utilizables**. Aquí solo se
almacena el digest:

```python
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
```

Que SHA-256 sea aceptable aquí, y bcrypt no, se explica por la naturaleza del valor: una
contraseña la elige una persona y se puede atacar por fuerza bruta, así que necesita un
algoritmo **lento**; un refresh token lo genera el servidor con entropía completa, así que
no hay diccionario que probar y basta un hash **rápido** para que una lectura de la base de
datos no sirva para autenticarse.

**Access tokens:** 30 minutos, JWT HS256 con `python-jose`.
**Refresh tokens:** 7 días, con rotación en cada uso y campo `revoked`.
**El logout revoca** todos los refresh tokens del usuario, o solo el proporcionado.

---

## Pruebas

**11 tests** en 5 módulos.

| Módulo | Tests | Cubre |
| :--- | :--- | :--- |
| `test_api.py` | 3 | Health, registro/login/refresh, flujo espacio → tablero → tarea |
| `test_ws.py` | 3 | Salas de tablero y espacio, rechazo sin token, rechazo con token inválido |
| `test_security.py` | 2 | Hash de contraseña, round-trip de token |
| `test_task_filters.py` | 2 | Paginación y filtros, enum inválido rechazado con 422 |
| `test_rbac.py` | 1 | Un miembro no puede ejecutar acciones de administrador |

```bash
pytest                                    # aplica el gate del 70% automáticamente
pytest --cov=app --cov-report=term-missing
pytest -k "ws or rbac"                    # solo WebSockets y permisos
```

**Los tests usan SQLite en memoria** (`sqlite://` con `StaticPool`), sin servicios externos
y sin migraciones. Es lo que hace la suite rápida, pero tiene un coste que conviene decir:
el comportamiento se valida contra SQLite, no contra PostgreSQL.

---

## Integración continua

`.github/workflows/ci.yml` define **4 jobs** en paralelo más un aggregator de fallos.

| Job | Qué hace |
| :--- | :--- |
| **Lint** | `ruff check .` y `ruff format --check .` |
| **Typecheck** | `mypy app` con `strict = true` |
| **Tests** | `pytest` con cobertura y gate del 70% |
| **Docker Build & Smoke Test** | Construye la imagen, levanta compose y verifica `/health` en el puerto **8001** |
| **Notify on Failure** | `needs: [lint, typecheck, test, docker]` |

A diferencia del proyecto de SSO, esta CI **no** levanta PostgreSQL ni Redis: el workflow
indica explícitamente que los tests no requieren servicios ni migraciones, y el smoke test
sí verifica que la imagen arranque y responda.

**Configuración:** Ruff con `line-length = 100`; MyPy con `strict = true`; el gate de
cobertura del 70% en `addopts` de `pyproject.toml`.

---

## Puesta en marcha

**Requisitos:** Docker Desktop en ejecución.

```bash
# 1. Clonar y entrar
git clone https://github.com/jerryszc/Realtime-task-api.git
cd Realtime-task-api

# 2. Configurar
cp .env.example .env
#   Antes de nada: cambia SECRET_KEY

# 3. Levantar
docker compose up --build -d

# 4. Verificar
curl http://localhost:8001/health

# 5. Documentación
#    http://localhost:8001/docs
```

> El puerto por defecto en Docker Compose es el **8001**, para no chocar con otro servicio
> local en el 8000.

```bash
docker compose down
docker compose down -v
```

### Desarrollo local sin Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Migraciones

```bash
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
alembic current
```

---

## Variables de entorno

| Variable | Por defecto | Descripción |
| :--- | :--- | :--- |
| `SECRET_KEY` | `change-me-in-env` | **Cambiar en producción.** Firma de los JWT |
| `ALGORITHM` | `HS256` | Algoritmo de firma |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Vigencia del access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Vigencia del refresh token |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@db:5432/realtime` | Conexión a PostgreSQL |

---

## Alcance y limitaciones

- **Los tests corren sobre SQLite en memoria**, no sobre PostgreSQL. El comportamiento
  queda verificado, pero no el de la base de datos de producción.
- **El `ConnectionManager` es en memoria y por proceso.** Con varias réplicas, un cliente
  conectado a la réplica A no recibe los eventos emitidos en la réplica B. El siguiente paso
  natural es un bus (Redis Pub/Sub o similar) por detrás de la misma interfaz.
- **No hay refresh token en el query string del WebSocket más allá de la conexión inicial.**
  Como la conexión es de larga duración, un token de 30 minutos caduca mientras sigue
  abierta; la reconexión con token nuevo es la que resuelve esto, y no hay renovación
  automática implementada.
- **No hay paginación por cursor**: la paginación es por `skip`/`limit`.

---

## Licencia

MIT — uso libre comercial y educativo. Ver [LICENSE](LICENSE).
