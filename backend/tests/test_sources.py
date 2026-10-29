import asyncio
import gzip

import httpx

from app.extract import _date_from_text
import app.sources as source_module
from app.sources import EventCardParser, Source, load_sources


class BytesStream(httpx.AsyncByteStream):
    def __init__(self, value: bytes):
        self.value = value

    async def __aiter__(self):
        yield self.value

    async def aclose(self):
        pass


def streamed_response(status_code: int, content: str, request, headers=None):
    return httpx.Response(
        status_code,
        headers=headers,
        stream=BytesStream(content.encode()),
        request=request,
    )


def test_event_directory_parser_reads_public_cards_and_ignores_ads():
    parser = EventCardParser()
    parser.feed(
        """
        <ul>
          <li class="event-card event-card-link"
              data-link="https://allevents.in/islamabad/ai-hackathon/123"
              data-name="AI Hackathon &amp; Meetup">
            <div class="date">Sun, 08 Nov, 2026 - 02:00 PM</div>
            <div class="location">Islamabad Convention Centre</div>
          </li>
          <li class="event-card"><div class="ad-item">Sponsored ad</div></li>
        </ul>
        """
    )
    assert len(parser.items) == 1
    assert parser.items[0].title == "AI Hackathon & Meetup"
    assert parser.items[0].url == "https://allevents.in/islamabad/ai-hackathon/123"
    assert "Islamabad Convention Centre" in parser.items[0].summary
    assert _date_from_text(parser.items[0].summary) == "2026-11-08"


def test_registry_attempts_all_indexed_sources_without_bypassing_blocks():
    sources = load_sources()
    active = [source for source in sources if source.enabled]
    ids = [source.id for source in sources]
    removed_ids = {
        "allevents-islamabad",
        "eventbrite-tech-pakistan",
        "devpost-hackathons",
        "luma-community-events",
        "mlh-hackathons-reference",
        "nic-islamabad-reference",
        "hackscout",
        "pasha-startup-hub",
        "linkedin-events",
        "facebook-events",
        "10times",
        "acm",
        "wikicfp",
        "pasha",
        "nascon",
        "punjab-it-board",
        "aws-user-groups",
        "owasp-events",
        "uet-lahore",
        "pkcert-events",
    }
    assert len(active) == 59
    assert len(sources) == 59
    assert len(ids) == len(set(ids))
    assert not any(source.kind == "event-directory" for source in active)
    assert all(source.crawl_policy == "eligible" for source in sources)
    assert sum(source.kind == "discover" for source in sources) == 48
    assert not removed_ids.intersection(ids)


def test_all_registered_enabled_feeds_have_unique_hosts_and_urls():
    sources = load_sources()
    assert len({source.url for source in sources}) == len(sources)


def test_all_indexed_sources_have_an_explicit_crawl_policy_and_discovery_connector():
    sources = load_sources()

    assert len(sources) == 59
    assert all(source.crawl_policy == "eligible" for source in sources)
    assert sum(source.kind == "discover" for source in sources) == 48


def test_researched_pakistan_event_sources_use_verified_public_pages():
    sources = {source.id: source for source in load_sources()}
    expected_urls = {
        "bano-qabil-hackathon": "https://banoqabil.org/hackathon",
        "code-for-pakistan-events": "https://codeforpakistan.org/events",
        "aspire-pakistan": "https://aspirepk.org/",
        "lablab-ai-hackathons": "https://lablab.ai/",
        "dev-events-pakistan": "https://dev.events/AS/PK",
        "founder-institute-islamabad": "https://fi.co/events/islamabad",
        "indus-ai-week": "https://indusai.sindh.gov.pk/",
        "ai-tinkerers-lahore": "https://lahore.aitinkerers.org/",
        "ai-tinkerers-karachi": "https://karachi.aitinkerers.org/",
        "friends-of-figma-lahore": "https://friends.figma.com/lahore/",
        "nic-karachi-events": "https://nickarachi.com/",
        "phoneworld-pakistan": "https://www.phoneworld.com.pk/",
        "eventbrite-islamabad-tech": (
            "https://www.eventbrite.com/d/pakistan--islamabad/technology/"
        ),
        "nic-islamabad-events": "https://nicislamabad.com/events/",
        "nutech-events": "https://nutech.edu.pk/events/",
        "invest2innovate": "https://invest2innovate.com/",
        "the-nest-io": "https://thenest.io/",
        "qau-events": "https://qau.edu.pk/events/",
        "gdg-islamabad-events": "https://gdg.community.dev/gdg-islamabad/",
        "techvalley-training": "https://techvalley.pk/trainings/",
    }

    assert {source_id: sources[source_id].url for source_id in expected_urls} == expected_urls
    assert all(sources[source_id].crawl_policy == "eligible" for source_id in expected_urls)
    assert sources["meetup-pakistan-tech"].url == (
        "https://www.meetup.com/find/?location=pk--Islamabad&source=EVENTS"
    )


def test_discovery_parser_extracts_declared_same_host_feed_and_jsonld_event():
    page = """
      <link rel="alternate" type="application/rss+xml" href="/events/feed.xml">
      <script type="application/ld+json">
        {"@type":"Event","name":"Islamabad AI Hackathon",
         "startDate":"2026-11-08T10:00:00+05:00",
         "url":"/events/ai-hackathon",
         "description":"Build software with Islamabad developers."}
      </script>
    """

    assert hasattr(source_module, "_parse_discovery_page")
    items, feeds = source_module._parse_discovery_page(page, "https://example.com/events")

    assert feeds == ["https://example.com/events/feed.xml"]
    assert len(items) == 1
    assert items[0].title == "Islamabad AI Hackathon"
    assert items[0].url == "https://example.com/events/ai-hackathon"
    assert "2026-11-08" in items[0].summary
    assert "Islamabad developers" in items[0].summary


def test_discovery_parser_ignores_non_event_jsonld_and_external_feed_links():
    page = """
      <link rel="alternate" type="application/rss+xml"
            href="https://other.example/feed.xml">
      <script type="application/ld+json">
        {"@type":"Organization","name":"Not an event"}
      </script>
    """

    items, feeds = source_module._parse_discovery_page(page, "https://example.com/")

    assert items == []
    assert feeds == []


def test_discovery_parser_rejects_feed_on_different_origin():
    page = """
      <link rel="alternate" type="application/rss+xml"
            href="https://example.com:8443/events.xml">
    """

    _, feeds = source_module._parse_discovery_page(page, "https://example.com/events")

    assert feeds == []


def test_source_url_validation_rejects_private_and_mixed_dns_results(monkeypatch):
    def private_addresses(*_args, **_kwargs):
        return [(2, 1, 6, "", ("127.0.0.1", 443))]

    monkeypatch.setattr(source_module.socket, "getaddrinfo", private_addresses)
    try:
        asyncio.run(source_module._validate_public_url("https://example.com"))
    except ValueError as exc:
        assert "non-public" in str(exc)
    else:
        raise AssertionError("private DNS results must be rejected")

    try:
        asyncio.run(source_module._validate_public_url("http://127.0.0.1/"))
    except ValueError as exc:
        assert "non-public" in str(exc)
    else:
        raise AssertionError("private IP literals must be rejected")

    def mixed_addresses(*_args, **_kwargs):
        return [
            (2, 1, 6, "", ("1.1.1.1", 443)),
            (2, 1, 6, "", ("10.0.0.1", 443)),
        ]

    monkeypatch.setattr(source_module.socket, "getaddrinfo", mixed_addresses)
    try:
        asyncio.run(source_module._validate_public_url("https://example.com"))
    except ValueError as exc:
        assert "non-public" in str(exc)
    else:
        raise AssertionError("mixed public and private DNS results must be rejected")


def test_source_url_validation_records_dns_results_for_connection_pinning(monkeypatch):
    def public_address(*_args, **_kwargs):
        return [(2, 1, 6, "", ("1.1.1.1", 443))]

    monkeypatch.setattr(source_module.socket, "getaddrinfo", public_address)
    source_module._validated_addresses.clear()

    asyncio.run(source_module._validate_public_url("https://example.com/events"))

    assert source_module._validated_addresses["example.com"] == ("1.1.1.1",)


def test_source_response_fetches_are_serialized_per_origin(monkeypatch):
    active = 0
    peak_active = 0

    async def no_validate(_url):
        return None

    async def no_wait(_origin, _crawl_delay):
        return None

    async def delayed_fetch(_client, _url, _max_bytes=source_module.MAX_FEED_BYTES, **_kwargs):
        nonlocal active, peak_active
        active += 1
        peak_active = max(peak_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return 200, httpx.Headers(), b"ok"

    monkeypatch.setattr(source_module, "_validate_public_url", no_validate)
    monkeypatch.setattr(source_module, "_wait_for_host", no_wait)
    monkeypatch.setattr(source_module, "_get_limited", delayed_fetch)

    async def fetch_concurrently():
        await asyncio.gather(
            *(
                source_module._fetch_source_response(None, "https://example.com/events", 0)
                for _ in range(3)
            )
        )

    asyncio.run(fetch_concurrently())

    assert peak_active == 1


def test_pinned_network_backend_connects_to_the_validated_ip():
    class RecordingBackend:
        def __init__(self):
            self.hosts = []

        async def connect_tcp(self, host, port, **_kwargs):
            self.hosts.append((host, port))
            return object()

    backend = RecordingBackend()
    pinned = source_module.PinnedNetworkBackend(backend, {"example.com": ("1.1.1.1",)})

    asyncio.run(pinned.connect_tcp("example.com", 443))

    assert backend.hosts == [("1.1.1.1", 443)]


def test_robots_fetch_failure_is_not_reported_as_an_explicit_denial(monkeypatch):
    async def allow_public_url(_url):
        return None

    async def fail_request(*_args, **_kwargs):
        raise httpx.ConnectError("connection failed")

    monkeypatch.setattr(source_module, "_validate_public_url", allow_public_url)
    monkeypatch.setattr(source_module, "_get_limited", fail_request)
    source_module._robots_cache.clear()

    try:
        asyncio.run(source_module._robots_policy("https://example.com/events", None))
    except source_module.RobotsFetchError as exc:
        assert "robots.txt" in str(exc)
    else:
        raise AssertionError("robots fetch errors must stay distinct from explicit denials")


def test_discovery_parser_closes_event_cards_with_void_html_elements():
    page = """
      <article class="event-card"><a href="/one">First tech meetup</a>
        <br><img src="/banner.png"><p>Islamabad developers</p>
      </article>
      <article class="event-card"><a href="/two">Second AI meetup</a>
        <img src="/banner-two.png"><p>Islamabad community</p>
      </article>
    """

    items, _ = source_module._parse_discovery_page(page, "https://example.com/events")

    assert [item.title for item in items] == ["First tech meetup", "Second AI meetup"]


def test_get_limited_rejects_encoded_and_oversized_responses():
    async def handler(request):
        if request.url.path == "/compressed":
            return httpx.Response(
                200,
                headers={"content-encoding": "gzip"},
                stream=BytesStream(gzip.compress(b"compressed")),
                request=request,
            )
        return httpx.Response(200, stream=BytesStream(b"123456"), request=request)

    async def verify_responses():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            for path, limit, expected in (
                ("/compressed", 100, "compressed"),
                ("/large", 5, "size limit"),
            ):
                try:
                    await source_module._get_limited(client, f"https://example.com{path}", limit)
                except ValueError as exc:
                    assert expected in str(exc)
                else:
                    raise AssertionError(f"{path} response should be rejected")

    asyncio.run(verify_responses())


def test_atom_feed_parser_preserves_published_event_text():
    feed = """<?xml version="1.0"?>
      <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
          <title>Islamabad AI Hackathon</title>
          <link rel="alternate" href="https://example.com/events/ai-hackathon"/>
          <summary>Teams build an AI product in Islamabad.</summary>
          <updated>2026-10-20T12:00:00Z</updated>
        </entry>
      </feed>"""

    assert hasattr(source_module, "_parse_feed")
    items = source_module._parse_feed(feed.encode(), "https://example.com/feed.xml")

    assert len(items) == 1
    assert items[0].title == "Islamabad AI Hackathon"
    assert items[0].url == "https://example.com/events/ai-hackathon"
    assert "AI product in Islamabad" in items[0].summary
    assert items[0].published_at == "2026-10-20T12:00:00+00:00"


def test_discovery_connector_fetches_declared_feed_after_robots_allows_source(monkeypatch):
    source = Source(
        id="public-source",
        name="Public source",
        kind="discover",
        url="https://example.com/events",
        publisher="Fixture",
    )
    requested_paths = []
    accept_encodings = []
    page = """
      <link rel="alternate" type="application/rss+xml" href="/events/feed.xml">
      <script type="application/ld+json">
        {"@type":"Event","name":"Islamabad AI Hackathon",
         "startDate":"2026-11-08T10:00:00+05:00","url":"/events/ai-hackathon"}
      </script>
    """
    feed = """<rss><channel><item><title>Islamabad Dev Meetup</title>
      <link>/events/meetup</link><description>November 9 Islamabad</description></item>
      </channel></rss>"""

    def handler(request):
        requested_paths.append(request.url.path)
        accept_encodings.append(request.headers.get("accept-encoding"))
        if request.url.path == "/robots.txt":
            return streamed_response(200, "User-agent: *\nAllow: /\n", request)
        if request.url.path == "/events":
            return streamed_response(
                200, page, request, headers={"content-type": "text/html"}
            )
        if request.url.path == "/events/feed.xml":
            return streamed_response(
                200,
                feed,
                request,
                headers={"content-type": "application/rss+xml"},
            )
        return httpx.Response(404, request=request)

    async def no_wait(_origin, _crawl_delay):
        return None

    real_client = httpx.AsyncClient

    def mocked_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(source_module, "_wait_for_host", no_wait)
    async def allow_public_url(_url):
        return None

    monkeypatch.setattr(source_module, "_validate_public_url", allow_public_url)
    monkeypatch.setattr(source_module.httpx, "AsyncClient", mocked_client)
    source_module._robots_cache.clear()

    assert "discover" in source_module.CONNECTORS
    items = asyncio.run(source_module.CONNECTORS["discover"].fetch(source))

    assert requested_paths == ["/robots.txt", "/events", "/events/feed.xml"]
    assert set(accept_encodings) == {"identity"}
    assert {item.title for item in items} == {"Islamabad AI Hackathon", "Islamabad Dev Meetup"}


def test_discovery_connector_does_not_fetch_source_when_robots_disallows_it(monkeypatch):
    source = Source(
        id="blocked-source",
        name="Blocked source",
        kind="discover",
        url="https://example.com/events",
        publisher="Fixture",
    )
    requested_paths = []

    def handler(request):
        requested_paths.append(request.url.path)
        return streamed_response(200, "User-agent: *\nDisallow: /\n", request)

    real_client = httpx.AsyncClient

    def mocked_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(source_module.httpx, "AsyncClient", mocked_client)
    async def allow_public_url(_url):
        return None

    monkeypatch.setattr(source_module, "_validate_public_url", allow_public_url)
    source_module._robots_cache.clear()

    assert "discover" in source_module.CONNECTORS
    try:
        asyncio.run(source_module.CONNECTORS["discover"].fetch(source))
    except PermissionError as exc:
        assert str(exc) == "robots.txt does not allow fetching this source"
    else:
        raise AssertionError("robots denial must stop the source-page request")
    assert requested_paths == ["/robots.txt"]
