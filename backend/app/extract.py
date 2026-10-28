import json
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Any

import httpx

from .config import GROQ_API_KEY, GROQ_MODEL

MONTHS = (
    "January February March April May June July August September October November December"
).split()
MONTH_LOOKUP = {month.lower(): number for number, month in enumerate(MONTHS, 1)}
MONTH_LOOKUP.update({month[:3].lower(): number for number, month in enumerate(MONTHS, 1)})


def _date_from_text(text: str) -> str | None:
    iso_match = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text)
    if iso_match:
        try:
            return date(*map(int, iso_match.groups())).isoformat()
        except ValueError:
            return None

    month_pattern = "|".join(MONTH_LOOKUP)
    match = re.search(
        rf"\b({month_pattern})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?[,]?\s+(20\d{{2}})\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(
            rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_pattern})\.?[,]?\s+(20\d{{2}})\b",
            text,
            re.IGNORECASE,
        )
        if match:
            day, month, year = match.groups()
        else:
            return None
    else:
        month, day, year = match.groups()
    try:
        return date(int(year), MONTH_LOOKUP[month.lower().rstrip(".")], int(day)).isoformat()
    except ValueError:
        return None


def local_extract(title: str, text: str) -> dict[str, Any]:
    combined = f"{title}. {text}"
    lowered = combined.lower()
    event_date = _date_from_text(combined)
    category = None
    if "hackathon" in lowered:
        category = "Hackathon"
    elif "workshop" in lowered or "bootcamp" in lowered:
        category = "Workshop"
    elif "meetup" in lowered:
        category = "Meetup"
    elif any(term in lowered for term in ("tech event", "technology event", "conference", "summit")):
        category = "Tech event"

    registration = "unknown"
    if re.search(r"\b(registration|applications?)\s+((is|are)\s+)?(closed|ended|over)\b", lowered):
        registration = "closed"
    elif re.search(r"\b(register|registration|applications?)\s+(is\s+)?(open|now open)\b", lowered):
        registration = "open"

    team_match = re.search(
        r"\bteams?\s+(?:of|must have|can have|up to)\s+(\d{1,2})(?:\s*(?:-|to)\s*(\d{1,2}))?\s*(?:members?|people|participants)?",
        combined,
        re.IGNORECASE,
    )
    venue = None
    venue_match = re.search(r"\b(?:at|venue:)\s+([A-Z][\w&'(). -]{2,50})", combined)
    if venue_match:
        venue = venue_match.group(1).strip(" .,-")
    event_format = "Online" if re.search(r"\b(online|virtual)\b", lowered) else None
    level = None
    if "national" in lowered or "across pakistan" in lowered:
        level = "National"
    elif "regional" in lowered:
        level = "Regional"
    elif "university" in lowered or "university-level" in lowered:
        level = "University"

    return {
        "event_date": event_date,
        "end_date": None,
        "category": category,
        "venue": venue,
        "format": event_format,
        "eligibility": None,
        "team_size": _team_size(team_match),
        "level": level,
        "registration_status": registration,
    }


def _team_size(match: re.Match[str] | None) -> str | None:
    if not match:
        return None
    if match.group(2):
        return f"{match.group(1)}–{match.group(2)} members"
    return f"{match.group(1)} members"


async def enrich_with_groq(title: str, text: str, extracted: dict[str, Any]) -> dict[str, Any]:
    if not GROQ_API_KEY:
        return extracted
    schema = {
        "event_date": "ISO date YYYY-MM-DD or null",
        "end_date": "ISO date YYYY-MM-DD or null",
        "category": "Hackathon, Meetup, Tech event, Workshop, or null",
        "venue": "venue or city mentioned, or null",
        "format": "Online, In-person, Hybrid, or null",
        "eligibility": "eligibility exactly summarized from text, or null",
        "team_size": "team size exactly summarized from text, or null",
        "level": "National, Regional, University, or null",
        "registration_status": "open, closed, or unknown",
        "evidence": "object mapping every non-null field to an exact quote copied from the supplied text",
    }
    prompt = (
        "Extract event facts from the source text only. Never infer or fill gaps. "
        "Return a JSON object matching this shape: "
        f"{json.dumps(schema)}. If the evidence quote is not an exact substring of the source text, "
        "the value will be discarded. The title is part of the source text. "
        f"\nTITLE: {title}\nSOURCE TEXT: {text[:6000]}"
    )
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": GROQ_MODEL,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You extract source-grounded event metadata."},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()

    content = payload["choices"][0]["message"]["content"]
    result = json.loads(content)
    evidence = result.get("evidence", {})
    fields = (
        "event_date",
        "end_date",
        "category",
        "venue",
        "format",
        "eligibility",
        "team_size",
        "level",
        "registration_status",
    )
    for field in fields:
        value = result.get(field)
        quote = evidence.get(field)
        if not value or not isinstance(quote, str) or quote not in f"{title}\n{text}":
            continue
        if field in ("event_date", "end_date"):
            if not isinstance(value, str) or _date_from_text(quote) != value:
                continue
        if field == "registration_status" and value not in ("open", "closed", "unknown"):
            continue
        extracted[field] = value
    return extracted


def is_future_event(event_date: str | None, today: date | None = None) -> bool:
    if not event_date:
        return False
    try:
        return date.fromisoformat(event_date) >= (today or datetime.now(ZoneInfo("Asia/Karachi")).date())
    except ValueError:
        return False


def is_relevant_to_islamabad(text: str, facts: dict[str, Any]) -> bool:
    lowered = text.casefold()
    location_match = re.search(r"\b(islamabad|ict|islamabad capital territory)\b", lowered)
    if facts.get("format") in ("Online", "Hybrid") or re.search(r"\b(online|virtual|hybrid)\b", lowered):
        national_access = re.search(
            r"\b(open to (?:all|anyone)|across pakistan|all over pakistan|nationwide|worldwide|national)\b",
            lowered,
        )
        return bool(location_match or national_access)
    return bool(location_match)
