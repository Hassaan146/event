import hashlib
import html
import re

from .db import connection, utc_now
from .extract import enrich_with_groq, is_future_event, is_relevant_to_islamabad, local_extract
from .sources import CONNECTORS, Source

CATEGORY_TERMS = ("hackathon", "meetup", "workshop", "technology event", "tech event", "conference", "summit")


def _plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _event_id(title: str, event_date: str) -> str:
    normalized_title = re.sub(r"\W+", " ", title.casefold()).strip()
    return hashlib.sha256(f"{normalized_title}:{event_date}".encode()).hexdigest()[:24]


async def refresh_sources(sources: list[Source]) -> dict[str, int | list[dict[str, str]]]:
    found = 0
    saved = 0
    saved_ids: set[str] = set()
    errors: list[dict[str, str]] = []
    for source in sources:
        if not source.enabled:
            continue
        checked = utc_now()
        try:
            connector = CONNECTORS.get(source.kind)
            if connector is None:
                raise ValueError(f"unsupported source connector: {source.kind}")
            items = await connector.fetch(source)
            with connection() as conn:
                conn.execute(
                    "INSERT INTO sources (id, name, url, publisher, enabled, last_checked, last_error) "
                    "VALUES (?, ?, ?, ?, ?, ?, NULL) "
                    "ON CONFLICT(id) DO UPDATE SET last_checked=excluded.last_checked, last_error=NULL",
                    (source.id, source.name, source.url, source.publisher, int(source.enabled), checked),
                )
            found += len(items)
            for item in items:
                title = _plain_text(item.title)
                summary = _plain_text(item.summary)
                text = f"{title}\n{summary}".strip()
                if not any(term in text.lower() for term in CATEGORY_TERMS):
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
                if event_id not in saved_ids:
                    saved += 1
                    saved_ids.add(event_id)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            errors.append({"source": source.name, "error": message})
            with connection() as conn:
                conn.execute(
                    "INSERT INTO sources (id, name, url, publisher, enabled, last_checked, last_error) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET last_checked=excluded.last_checked, last_error=excluded.last_error",
                    (source.id, source.name, source.url, source.publisher, int(source.enabled), checked, message[:500]),
                )
    return {"feeds_found": found, "events_saved": saved, "errors": errors}
