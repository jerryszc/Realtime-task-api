from fastapi import FastAPI

from app.routers import auth, boards, tasks, workspaces, ws

app = FastAPI(title="Real-Time Collaborative Task Management API", version="0.1.0")

app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(boards.router)
app.include_router(tasks.router)
app.include_router(ws.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
