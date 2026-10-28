import asyncio
import hashlib
import html
import re
import xml.etree.ElementTree as ElementTree

import httpx

from .db import connection, utc_now
from .extract import (
    enrich_with_groq,
    is_future_event,
    is_hackathon,
    is_relevant_to_islamabad,
    is_technology_related,
    local_extract,
)
from .sources import CONNECTORS, RobotsFetchError, Source, SourceRedirectError

EVENT_TERMS = (
    "hackathon",
    "meetup",
    "workshop",
    "conference",
    "summit",
    "competition",
    "challenge",
    "bootcamp",
    "networking event",
)
SOURCE_CONCURRENCY = 4

def _is_tech_event(text: str) -> bool:
    lowered = text.casefold()
    has_event_term = any(re.search(rf"\b{re.escape(term)}s?\b", lowered) for term in EVENT_TERMS)
    return (has_event_term or is_hackathon(text)) and (
        is_hackathon(text) or is_technology_related(text)
    )


def _plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _event_id(title: str, event_date: str) -> str:
    normalized_title = re.sub(r"\W+", " ", title.casefold()).strip()
    return hashlib.sha256(f"{normalized_title}:{event_date}".encode()).hexdigest()[:24]


def _crawl_status(exc: Exception) -> str:
    if isinstance(exc, RobotsFetchError):
        return "robots_unavailable"
    if isinstance(exc, PermissionError):
        return "robots_denied"
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 401:
            return "login_required"
        if exc.response.status_code == 403:
            return "forbidden"
        if 300 <= exc.response.status_code < 400:
            return "unsupported"
    if isinstance(exc, SourceRedirectError):
        return "unsupported"
    if isinstance(exc, TypeError):
        return "unsupported"
    if isinstance(exc, ElementTree.ParseError):
        return "parse_error"
    return "error"


def _record_source_status(
    source: Source,
    checked: str,
    status: str,
    items_found: int = 0,
    events_saved: int = 0,
    error: str | None = None,
) -> None:
    was_attempted = status not in ("review_required", "disallowed")
    checked_at = checked if was_attempted else None
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO sources (
                id, name, url, publisher, enabled, last_checked, last_error,
                crawl_policy, crawl_status, last_attempted, items_found, events_saved
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, url=excluded.url, publisher=excluded.publisher,
                enabled=excluded.enabled, last_checked=COALESCE(excluded.last_checked, sources.last_checked),
                last_error=excluded.last_error, crawl_policy=excluded.crawl_policy,
                crawl_status=excluded.crawl_status, last_attempted=excluded.last_attempted,
                items_found=excluded.items_found, events_saved=excluded.events_saved
            """,
            (
                source.id,
                source.name,
                source.url,
                source.publisher,
                int(source.enabled),
                checked_at,
                error,
                source.crawl_policy,
                status,
                checked if was_attempted else None,
                items_found,
                events_saved,
            ),
        )


async def refresh_sources(sources: list[Source]) -> dict[str, int | list[dict[str, str]]]:
    saved_ids: set[str] = set()
    semaphore = asyncio.Semaphore(SOURCE_CONCURRENCY)

    async def refresh_source(source: Source) -> dict[str, int | str | dict[str, str] | None]:
        if source.crawl_policy not in ("eligible", "review_required", "disallowed"):
            status = "disallowed"
            note = f"Unsupported crawl policy: {source.crawl_policy}"
            _record_source_status(source, utc_now(), status, error=note)
            return {"status": status, "items_found": 0, "events_saved": 0, "error": None}
        if source.crawl_policy != "eligible" or not source.enabled:
            status = "review_required" if source.crawl_policy == "review_required" else "disallowed"
            _record_source_status(
                source, utc_now(), status, error=source.note or status.replace("_", " ")
            )
            return {"status": status, "items_found": 0, "events_saved": 0, "error": None}

        async with semaphore:
            items_found = 0
            source_saved_ids: set[str] = set()
            try:
                connector = CONNECTORS.get(source.kind)
                if connector is None:
                    raise TypeError(f"unsupported source connector: {source.kind}")
                items = await connector.fetch(source)
                items_found = len(items)
                for item in items:
                    title = _plain_text(item.title)
                    summary = _plain_text(item.summary)
                    text = f"{title}\n{summary}".strip()
                    if not _is_tech_event(text):
                        with connection() as conn:
                            conn.execute("DELETE FROM events WHERE source_url = ?", (item.url,))
                        continue
                    facts = local_extract(title, summary)
                    facts = await enrich_with_groq(title, summary, facts)
                    event_date = facts.get("event_date")
                    event_id = _event_id(title, event_date) if event_date else None
                    eligible = (
                        is_future_event(event_date)
                        and facts.get("registration_status") != "closed"
                        and is_relevant_to_islamabad(text, facts)
                    )
                    if not eligible or event_id is None:
                        with connection() as conn:
                            conn.execute("DELETE FROM events WHERE source_url = ?", (item.url,))
                        continue
                    now = utc_now()
                    with connection() as conn:
                        conn.execute(
                            "DELETE FROM events WHERE source_url = ? AND id != ?",
                            (item.url, event_id),
                        )
                        conn.execute(
                            """
                            INSERT INTO events (
                                id, title, event_date, end_date, category, venue, format,
                                eligibility, team_size, level, registration_status,
                                source_name, source_url, source_text, last_checked, first_seen
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                title=excluded.title, event_date=excluded.event_date,
                                end_date=excluded.end_date, category=excluded.category,
                                venue=excluded.venue, format=excluded.format,
                                eligibility=excluded.eligibility, team_size=excluded.team_size,
                                level=excluded.level, registration_status=excluded.registration_status,
                                source_name=excluded.source_name, source_url=excluded.source_url,
                                source_text=excluded.source_text, last_checked=excluded.last_checked
                            """,
                            (
                                event_id, title, facts.get("event_date"), facts.get("end_date"),
                                facts.get("category"), facts.get("venue"), facts.get("format"),
                                facts.get("eligibility"), facts.get("team_size"), facts.get("level"),
                                facts.get("registration_status", "unknown"), source.name, item.url,
                                text, now, now,
                            ),
                        )
                    if event_id not in source_saved_ids:
                        source_saved_ids.add(event_id)
                        saved_ids.add(event_id)
                status = "success" if items_found else "empty"
                _record_source_status(
                    source,
                    utc_now(),
                    status,
                    items_found=items_found,
                    events_saved=len(source_saved_ids),
                )
                return {
                    "status": status,
                    "items_found": items_found,
                    "events_saved": len(source_saved_ids),
                    "error": None,
                }
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"[:500]
                status = _crawl_status(exc)
                _record_source_status(
                    source, utc_now(), status, items_found=items_found, error=message
                )
                return {
                    "status": status,
                    "items_found": items_found,
                    "events_saved": len(source_saved_ids),
                    "error": {"source": source.name, "error": message},
                }

    results = await asyncio.gather(*(refresh_source(source) for source in sources))
    errors = [result["error"] for result in results if isinstance(result["error"], dict)]
    statuses = [result["status"] for result in results]
    return {
        "feeds_found": sum(int(result["items_found"]) for result in results),
        "events_saved": len(saved_ids),
        "sources_attempted": sum(
            status not in ("review_required", "disallowed") for status in statuses
        ),
        "sources_succeeded": statuses.count("success"),
        "sources_empty": statuses.count("empty"),
        "sources_skipped": statuses.count("review_required") + statuses.count("disallowed"),
        "sources_failed": sum(
            status in (
                "robots_denied", "robots_unavailable", "forbidden", "login_required",
                "unsupported", "parse_error", "error"
            )
            for status in statuses
        ),
        "errors": errors,
    }
