import json
import time
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Protocol
from xml.etree import ElementTree

import httpx

from .config import SOURCES_PATH, USER_AGENT

HOST_DELAY_SECONDS = 2.0
MAX_FEED_BYTES = 2_000_000
_last_host_fetch: dict[str, float] = {}
_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    kind: str
    url: str
    publisher: str
    enabled: bool = True


@dataclass(frozen=True)
class FeedItem:
    title: str
    url: str
    summary: str
    published_at: str | None


class Connector(Protocol):
    async def fetch(self, source: Source) -> list[FeedItem]: ...


def load_sources(path: Path = SOURCES_PATH) -> list[Source]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Source(**item) for item in data]


async def _robots_allowed(url: str, client: httpx.AsyncClient) -> bool:
    parsed = urllib.parse.urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in _robots_cache:
        robots_url = urllib.parse.urljoin(origin, "/robots.txt")
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        try:
            response = await client.get(robots_url)
            if response.status_code == 404:
                parser.parse([])
            elif response.is_success:
                parser.parse(response.text.splitlines())
            else:
                parser.parse(["User-agent: *", "Disallow: /"])
        except httpx.HTTPError:
            parser.parse(["User-agent: *", "Disallow: /"])
        _robots_cache[origin] = parser
    return _robots_cache[origin].can_fetch(USER_AGENT, url)


def _published_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


class RSSConnector:
    async def fetch(self, source: Source) -> list[FeedItem]:
        parsed = urllib.parse.urlparse(source.url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        last_fetch = _last_host_fetch.get(origin, 0)
        delay = HOST_DELAY_SECONDS - (time.monotonic() - last_fetch)
        if delay > 0:
            import asyncio

            await asyncio.sleep(delay)

        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"},
        ) as client:
            if not await _robots_allowed(source.url, client):
                raise PermissionError("robots.txt does not allow fetching this feed")
            response = await client.get(source.url)
            response.raise_for_status()
            if len(response.content) > MAX_FEED_BYTES:
                raise ValueError("feed exceeds the 2 MB size limit")
            _last_host_fetch[origin] = time.monotonic()

        root = ElementTree.fromstring(response.content)
        items = []
        for node in root.findall(".//item"):
            title = _text(node, "title")
            link = _text(node, "link")
            summary = _text(node, "description")
            if not title or not link:
                continue
            items.append(
                FeedItem(
                    title=title,
                    url=link,
                    summary=summary,
                    published_at=_published_date(_text(node, "pubDate")),
                )
            )
        return items


def _text(node: ElementTree.Element, tag: str) -> str:
    child = node.find(tag)
    if child is None or child.text is None:
        return ""
    return " ".join(child.text.split())


CONNECTORS: dict[str, Connector] = {"rss": RSSConnector()}
