import json
import re
import time
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass
from datetime import timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
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
    note: str | None = None


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


async def _robots_policy(url: str, client: httpx.AsyncClient) -> tuple[bool, float]:
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
        _last_host_fetch[origin] = time.monotonic()
    parser = _robots_cache[origin]
    return (
        parser.can_fetch(USER_AGENT, url),
        float(parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*") or 0),
    )


async def _wait_for_host(origin: str, crawl_delay: float) -> None:
    last_fetch = _last_host_fetch.get(origin, 0)
    delay = max(HOST_DELAY_SECONDS, crawl_delay) - (time.monotonic() - last_fetch)
    if delay > 0:
        import asyncio

        await asyncio.sleep(delay)


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

        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"},
        ) as client:
            allowed, crawl_delay = await _robots_policy(source.url, client)
            if not allowed:
                raise PermissionError("robots.txt does not allow fetching this feed")
            await _wait_for_host(origin, crawl_delay)
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


class EventCardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current: dict[str, str] | None = None
        self.items: list[FeedItem] = []
        self.depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class", "").split()
        if tag == "li" and "event-card-link" in classes and self.current is None:
            self.current = {
                "title": attributes.get("data-name", ""),
                "url": attributes.get("data-link", ""),
                "text": "",
            }
            self.depth = 1
        elif self.current is not None and tag == "li":
            self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self.current is None or tag != "li":
            return
        self.depth -= 1
        if self.depth <= 0:
            title = re.sub(r"\s+", " ", self.current["title"]).strip()
            url = self.current["url"].strip()
            summary = re.sub(r"\s+", " ", self.current["text"]).strip()
            if title and url:
                self.items.append(FeedItem(title, url, f"Islamabad event. {summary}", None))
            self.current = None
            self.depth = 0

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            self.current["text"] += f" {data}"


class EventDirectoryConnector:
    async def fetch(self, source: Source) -> list[FeedItem]:
        parsed = urllib.parse.urlparse(source.url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        ) as client:
            allowed, crawl_delay = await _robots_policy(source.url, client)
            if not allowed:
                raise PermissionError("robots.txt does not allow fetching this directory")
            await _wait_for_host(origin, crawl_delay)
            response = await client.get(source.url)
            response.raise_for_status()
            if len(response.content) > MAX_FEED_BYTES:
                raise ValueError("directory page exceeds the 2 MB size limit")
            _last_host_fetch[origin] = time.monotonic()

        parser = EventCardParser()
        parser.feed(response.text)
        allowed_host = parsed.netloc.lower()
        return [
            item
            for item in parser.items
            if urllib.parse.urlparse(item.url).netloc.lower() in (allowed_host, f"www.{allowed_host}")
        ]


def _text(node: ElementTree.Element, tag: str) -> str:
    child = node.find(tag)
    if child is None or child.text is None:
        return ""
    return " ".join(child.text.split())


CONNECTORS: dict[str, Connector] = {
    "rss": RSSConnector(),
    "event-directory": EventDirectoryConnector(),
}
