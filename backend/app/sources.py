import asyncio
import ipaddress
import json
import re
import socket
import time
import urllib.parse
import urllib.robotparser
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol
from xml.etree import ElementTree

import httpcore
import httpx

from .config import SOURCES_PATH, USER_AGENT

HOST_DELAY_SECONDS = 2.0
MAX_FEED_BYTES = 2_000_000
MAX_ROBOTS_BYTES = 256_000
MAX_DISCOVERED_FEEDS = 3


class RobotsFetchError(Exception):
    pass


_last_host_fetch: dict[str, float] = {}
_robots_cache: dict[str, urllib.robotparser.RobotFileParser | RobotsFetchError] = {}
_validated_addresses: dict[str, tuple[str, ...]] = {}
_host_locks: dict[tuple[asyncio.AbstractEventLoop, str], asyncio.Lock] = {}


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    kind: str
    url: str
    publisher: str
    enabled: bool = True
    crawl_policy: str = "eligible"
    note: str | None = None


@dataclass(frozen=True)
class FeedItem:
    title: str
    url: str
    summary: str
    published_at: str | None


class SourceRedirectError(Exception):
    pass


class Connector(Protocol):
    async def fetch(self, source: Source) -> list[FeedItem]: ...


def load_sources(path: Path = SOURCES_PATH) -> list[Source]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if path == SOURCES_PATH:
        reference_path = SOURCES_PATH.with_name("reference_sources.json")
        data.extend(json.loads(reference_path.read_text(encoding="utf-8")))
    return [Source(**item) for item in data]


def _origin(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _host_key(host: str) -> str:
    normalized = host.rstrip(".")
    try:
        return ipaddress.ip_address(normalized).compressed.casefold()
    except ValueError:
        return normalized.encode("idna").decode("ascii").casefold()


def _response_text(content: bytes, headers: httpx.Headers) -> str:
    return httpx.Response(200, headers=headers, content=content).text


def _same_origin(left: str, right: str) -> bool:
    left_parsed = urllib.parse.urlparse(left)
    right_parsed = urllib.parse.urlparse(right)
    return (
        left_parsed.scheme.lower() == right_parsed.scheme.lower()
        and left_parsed.hostname is not None
        and left_parsed.hostname.lower() == (right_parsed.hostname or "").lower()
        and left_parsed.port == right_parsed.port
    )


async def _validate_public_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.hostname.casefold().endswith((".localhost", ".local", ".internal"))
    ):
        raise ValueError("source URL must use a public HTTP(S) host")

    try:
        literal_ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        literal_ip = None
    if literal_ip is not None:
        if not literal_ip.is_global:
            raise ValueError("source URL resolves to a non-public address")
        _validated_addresses[_host_key(parsed.hostname)] = (literal_ip.compressed,)
        return

    try:
        addresses = await asyncio.wait_for(
            asyncio.to_thread(
                socket.getaddrinfo,
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            ),
            timeout=5,
        )
    except (OSError, TimeoutError) as exc:
        raise ConnectionError(f"could not validate source host: {parsed.hostname}") from exc
    resolved = tuple(dict.fromkeys(entry[4][0] for entry in addresses))
    if not resolved or any(not ipaddress.ip_address(address).is_global for address in resolved):
        raise ValueError("source URL resolves to a non-public address")
    _validated_addresses[_host_key(parsed.hostname)] = resolved


class PinnedNetworkBackend:
    def __init__(
        self,
        backend: httpcore.AsyncNetworkBackend,
        validated_addresses: dict[str, tuple[str, ...]],
    ) -> None:
        self._backend = backend
        self._validated_addresses = validated_addresses

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        addresses = self._validated_addresses.get(_host_key(host))
        if not addresses:
            raise httpcore.ConnectError(f"No validated public address for {host}")
        return await self._backend.connect_tcp(
            addresses[0],
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        return await self._backend.connect_unix_socket(
            path, timeout=timeout, socket_options=socket_options
        )

    async def sleep(self, seconds: float) -> None:
        await self._backend.sleep(seconds)


def _pinned_transport() -> httpx.AsyncHTTPTransport:
    transport = httpx.AsyncHTTPTransport(trust_env=False)
    # Keep HTTPX on its verified 0.28 minor line while pinning its connection backend.
    transport._pool._network_backend = PinnedNetworkBackend(
        transport._pool._network_backend, _validated_addresses
    )
    return transport


def _host_lock(origin: str) -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    key = (loop, origin)
    if key not in _host_locks:
        _host_locks[key] = asyncio.Lock()
    return _host_locks[key]


async def _get_limited(
    client: httpx.AsyncClient,
    url: str,
    max_bytes: int = MAX_FEED_BYTES,
    *,
    allow_error_status: bool = False,
) -> tuple[int, httpx.Headers, bytes]:
    async with client.stream("GET", url) as response:
        if 300 <= response.status_code < 400:
            raise SourceRedirectError("source redirects are not followed")
        if not response.is_success:
            if allow_error_status:
                return response.status_code, response.headers, b""
            response.raise_for_status()
        content_encoding = response.headers.get("content-encoding", "identity").casefold().strip()
        if content_encoding not in ("", "identity"):
            raise ValueError(f"compressed source responses are unsupported: {content_encoding}")
        content = bytearray()
        async for chunk in response.aiter_raw():
            if len(content) + len(chunk) > max_bytes:
                raise ValueError(f"source response exceeds the {max_bytes} byte size limit")
            content.extend(chunk)
        return response.status_code, response.headers, bytes(content)


async def _robots_policy(url: str, client: httpx.AsyncClient) -> tuple[bool, float]:
    origin = _origin(url)
    async with _host_lock(origin):
        if origin not in _robots_cache:
            robots_url = urllib.parse.urljoin(origin, "/robots.txt")
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(robots_url)
            try:
                await _validate_public_url(robots_url)
                status_code, headers, content = await _get_limited(
                    client, robots_url, MAX_ROBOTS_BYTES, allow_error_status=True
                )
                if status_code == 404:
                    parser.parse([])
                elif 200 <= status_code < 300:
                    encoding = httpx.Response(status_code, headers=headers).encoding or "utf-8"
                    parser.parse(content.decode(encoding, errors="replace").splitlines())
                else:
                    raise RobotsFetchError(f"robots.txt returned HTTP {status_code}")
            except RobotsFetchError as exc:
                _robots_cache[origin] = exc
            except (httpx.HTTPError, OSError, ValueError, ConnectionError, SourceRedirectError) as exc:
                _robots_cache[origin] = RobotsFetchError(
                    f"robots.txt could not be checked: {type(exc).__name__}: {exc}"
                )
            else:
                _robots_cache[origin] = parser
            _last_host_fetch[origin] = time.monotonic()
        parser = _robots_cache[origin]
    if isinstance(parser, RobotsFetchError):
        raise parser
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


async def _fetch_source_response(
    client: httpx.AsyncClient,
    url: str,
    crawl_delay: float,
) -> tuple[int, httpx.Headers, bytes]:
    origin = _origin(url)
    async with _host_lock(origin):
        await _validate_public_url(url)
        await _wait_for_host(origin, crawl_delay)
        try:
            return await _get_limited(client, url)
        finally:
            _last_host_fetch[origin] = time.monotonic()


def _published_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def _iso_date(value: str) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def _xml_text(node: ElementTree.Element, name: str) -> str:
    for child in node:
        if child.tag.rsplit("}", 1)[-1] == name:
            return " ".join("".join(child.itertext()).split())
    return ""


def _parse_feed(content: bytes, feed_url: str) -> list[FeedItem]:
    root = ElementTree.fromstring(content)
    nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] in ("item", "entry")]
    items = []
    for node in nodes:
        title = _xml_text(node, "title")
        link = _xml_text(node, "link")
        if not link:
            link_node = next(
                (child for child in node if child.tag.rsplit("}", 1)[-1] == "link"),
                None,
            )
            if link_node is not None:
                link = link_node.attrib.get("href", "")
        summary = (
            _xml_text(node, "description")
            or _xml_text(node, "summary")
            or _xml_text(node, "content")
        )
        published = _xml_text(node, "pubDate") or _xml_text(node, "published") or _xml_text(node, "updated")
        if title and link:
            items.append(
                FeedItem(
                    title=title,
                    url=urllib.parse.urljoin(feed_url, link),
                    summary=summary,
                    published_at=_published_date(published) or _iso_date(published),
                )
            )
    return items


class DiscoveryPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.feed_links: list[str] = []
        self.events: list[FeedItem] = []
        self._jsonld: list[str] | None = None
        self._card: dict[str, str] | None = None
        self._card_tag = ""
        self._card_depth = 0
        self._anchor_depth: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "link":
            rel = (attributes.get("rel") or "").casefold().split()
            content_type = (attributes.get("type") or "").casefold().split(";")[0].strip()
            href = attributes.get("href")
            if (
                "alternate" in rel
                and content_type in ("application/rss+xml", "application/atom+xml")
                and href
            ):
                self.feed_links.append(href)
        if tag == "script" and (attributes.get("type") or "").casefold().split(";")[0].strip() == (
            "application/ld+json"
        ):
            self._jsonld = []

        if self._card is not None:
            if tag not in {
                "area", "base", "br", "col", "embed", "hr", "img", "input",
                "link", "meta", "param", "source", "track", "wbr",
            }:
                self._card_depth += 1
            if tag == "a" and self._anchor_depth is None:
                href = attributes.get("href")
                if href and not self._card["url"]:
                    self._card["url"] = href
                    self._anchor_depth = self._card_depth
        elif tag in ("article", "li", "div"):
            class_tokens = (attributes.get("class") or "").casefold().split()
            id_value = (attributes.get("id") or "").casefold()
            looks_like_card = any(
                token in ("event-card", "event-item", "event-listing") for token in class_tokens
            ) or (
                tag == "article"
                and ("event" in id_value or "event" in " ".join(class_tokens))
            )
            if looks_like_card:
                self._card = {
                    "title": attributes.get("data-name") or attributes.get("aria-label") or "",
                    "url": attributes.get("data-link") or "",
                    "text": "",
                }
                self._card_tag = tag
                self._card_depth = 1

    def handle_endtag(self, tag: str) -> None:
        if self._jsonld is not None and tag == "script":
            self.events.extend(_jsonld_events("".join(self._jsonld)))
            self._jsonld = None

        if self._card is None:
            return
        if self._anchor_depth == self._card_depth and tag == "a":
            self._anchor_depth = None
        if tag == self._card_tag and self._card_depth == 1:
            title = re.sub(r"\s+", " ", self._card["title"]).strip()
            url = self._card["url"].strip()
            summary = re.sub(r"\s+", " ", self._card["text"]).strip()
            if title and url:
                self.events.append(FeedItem(title, url, summary, None))
            self._card = None
            self._card_depth = 0
            self._anchor_depth = None
        else:
            self._card_depth = max(1, self._card_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._jsonld is not None:
            self._jsonld.append(data)
        if self._card is not None:
            if self._anchor_depth is not None and not self._card["title"]:
                self._card["title"] += f" {data}"
            else:
                self._card["text"] += f" {data}"


def _jsonld_events(payload: str) -> list[FeedItem]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []

    found: list[FeedItem] = []

    def visit(value: object) -> None:
        if isinstance(value, list):
            for entry in value:
                visit(entry)
            return
        if not isinstance(value, dict):
            return
        types = value.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if any(isinstance(item, str) and item.endswith("Event") for item in types):
            title = value.get("name")
            start_date = value.get("startDate")
            if isinstance(title, str) and title.strip() and isinstance(start_date, str):
                summary_parts = [f"Event date: {start_date}"]
                description = value.get("description")
                if isinstance(description, str):
                    summary_parts.append(description)
                end_date = value.get("endDate")
                if isinstance(end_date, str):
                    summary_parts.append(f"End date: {end_date}")
                location = value.get("location")
                if isinstance(location, dict) and isinstance(location.get("name"), str):
                    summary_parts.append(f"Location: {location['name']}")
                found.append(
                    FeedItem(
                        title=title.strip(),
                        url=value.get("url") if isinstance(value.get("url"), str) else "",
                        summary=" ".join(summary_parts),
                        published_at=None,
                    )
                )
        if "@graph" in value:
            visit(value["@graph"])

    visit(data)
    return found


def _parse_discovery_page(content: str, source_url: str) -> tuple[list[FeedItem], list[str]]:
    parser = DiscoveryPageParser()
    parser.feed(content)
    items = []
    for item in parser.events:
        event_url = urllib.parse.urljoin(source_url, item.url or source_url)
        event_parsed = urllib.parse.urlparse(event_url)
        if event_parsed.scheme not in ("http", "https") or not event_parsed.hostname:
            continue
        items.append(FeedItem(item.title, event_url, item.summary, item.published_at))
    feed_links = []
    for link in parser.feed_links:
        feed_url = urllib.parse.urljoin(source_url, link)
        parsed_feed = urllib.parse.urlparse(feed_url)
        if (
            parsed_feed.scheme in ("http", "https")
            and _same_origin(feed_url, source_url)
            and feed_url not in feed_links
        ):
            feed_links.append(feed_url)
    return items, feed_links


class RSSConnector:
    async def fetch(self, source: Source) -> list[FeedItem]:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=False,
            trust_env=False,
            transport=_pinned_transport(),
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/rss+xml, application/xml, text/xml",
                "Accept-Encoding": "identity",
            },
        ) as client:
            allowed, crawl_delay = await _robots_policy(source.url, client)
            if not allowed:
                raise PermissionError("robots.txt does not allow fetching this feed")
            _, _, content = await _fetch_source_response(client, source.url, crawl_delay)

        return _parse_feed(content, source.url)


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
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=False,
            trust_env=False,
            transport=_pinned_transport(),
            headers={"User-Agent": USER_AGENT, "Accept": "text/html", "Accept-Encoding": "identity"},
        ) as client:
            allowed, crawl_delay = await _robots_policy(source.url, client)
            if not allowed:
                raise PermissionError("robots.txt does not allow fetching this directory")
            _, headers, content = await _fetch_source_response(client, source.url, crawl_delay)

        parser = EventCardParser()
        parser.feed(_response_text(content, headers))
        allowed_host = parsed.netloc.lower()
        return [
            item
            for item in parser.items
            if urllib.parse.urlparse(item.url).netloc.lower() in (allowed_host, f"www.{allowed_host}")
        ]


class DiscoveryConnector:
    async def fetch(self, source: Source) -> list[FeedItem]:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=False,
            trust_env=False,
            transport=_pinned_transport(),
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html, application/xhtml+xml, application/rss+xml, application/atom+xml",
                "Accept-Encoding": "identity",
            },
        ) as client:
            allowed, crawl_delay = await _robots_policy(source.url, client)
            if not allowed:
                raise PermissionError("robots.txt does not allow fetching this source")
            _, headers, content = await _fetch_source_response(client, source.url, crawl_delay)

            content_type = headers.get("content-type", "").casefold()
            text = _response_text(content, headers)
            if "xml" in content_type or content.lstrip().startswith(b"<?xml"):
                return _parse_feed(content, source.url)
            if "html" not in content_type and not text.lstrip().startswith("<"):
                raise TypeError("source returned an unsupported content type")

            items, feed_urls = _parse_discovery_page(text, source.url)
            for feed_url in feed_urls[:MAX_DISCOVERED_FEEDS]:
                feed_allowed, feed_delay = await _robots_policy(feed_url, client)
                if not feed_allowed:
                    continue
                _, _, feed_content = await _fetch_source_response(client, feed_url, feed_delay)
                items.extend(_parse_feed(feed_content, feed_url))
            return items


CONNECTORS: dict[str, Connector] = {
    "rss": RSSConnector(),
    "event-directory": EventDirectoryConnector(),
    "discover": DiscoveryConnector(),
}
