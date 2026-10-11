from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import decisions, queue, reports, tasks, ws
from .db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Claude Foreman", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(queue.router)
app.include_router(reports.router)
app.include_router(decisions.router)
app.include_router(ws.router)


@app.get("/api/health")
def health():
    return {"ok": True}
