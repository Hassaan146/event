from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import FRONTEND_ORIGIN
from .db import connection, initialize_database
from .ingest import refresh_sources
from .sources import load_sources


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Islamabad Tech Events API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _event(row: Any) -> dict[str, Any]:
    result = dict(row)
    result.pop("source_text", None)
    return result


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/events")
def list_events(
    q: str = Query(default="", max_length=120),
    category: str = Query(default="", max_length=40),
    registration: str = Query(default="", pattern="^(|open|unknown)$"),
) -> dict[str, Any]:
    today = datetime.now(ZoneInfo("Asia/Karachi")).date().isoformat()
    clauses = ["event_date >= ?"]
    params: list[str] = [today]
    if q.strip():
        clauses.append("(title LIKE ? OR source_name LIKE ? OR category LIKE ?)")
        search = f"%{q.strip()}%"
        params.extend([search, search, search])
    if category.strip():
        clauses.append("category = ?")
        params.append(category.strip())
    if registration:
        clauses.append("registration_status = ?")
        params.append(registration)
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM events WHERE " + " AND ".join(clauses) + " ORDER BY event_date ASC",
            params,
        ).fetchall()
        last_refresh = conn.execute("SELECT MAX(last_checked) AS value FROM sources").fetchone()["value"]
    return {"events": [_event(row) for row in rows], "last_refresh": last_refresh}


@app.get("/api/sources")
def list_sources() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, name, url, publisher, enabled, last_checked, last_error FROM sources ORDER BY name"
        ).fetchall()
    status_by_id = {row["id"]: dict(row) for row in rows}
    result = []
    for source in load_sources():
        status = status_by_id.get(source.id, {})
        result.append(
            {
                "id": source.id,
                "name": source.name,
                "url": source.url,
                "publisher": source.publisher,
                "enabled": source.enabled,
                "note": source.note,
                "last_checked": status.get("last_checked"),
                "last_error": status.get("last_error"),
            }
        )
    return result


@app.post("/api/refresh")
async def refresh() -> dict[str, Any]:
    try:
        sources = load_sources()
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not load source registry: {exc}") from exc
    return await refresh_sources(sources)
