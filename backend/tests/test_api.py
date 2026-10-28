from fastapi.testclient import TestClient

from app import db, ingest, main
from app.sources import FeedItem, Source, load_sources


def test_database_adds_source_outcome_columns_to_existing_schema(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.sqlite"
    monkeypatch.setattr(db, "DATABASE_PATH", database_path)
    with db.connection() as conn:
        conn.execute(
            """
            CREATE TABLE sources (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL,
                publisher TEXT NOT NULL, enabled INTEGER NOT NULL,
                last_checked TEXT, last_error TEXT
            )
            """
        )

    db.initialize_database()

    with db.connection() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(sources)")}
    assert {
        "crawl_policy", "crawl_status", "last_attempted", "items_found", "events_saved"
    } <= columns


class FixtureConnector:
    def __init__(self):
        self.close_hackathons = False

    async def fetch(self, source: Source) -> list[FeedItem]:
        registration = "Registration is closed." if self.close_hackathons else "Registration is open."
        return [
            FeedItem(
                title="Islamabad AI hackathon",
                url="https://news.google.com/item/open",
                summary=f"{registration} Teams of 3-5 members. National event on December 12, 2099. Online.",
                published_at=None,
            ),
            FeedItem(
                title="Islamabad workshop",
                url="https://news.google.com/item/unknown",
                summary="A software engineering community workshop on December 13, 2099.",
                published_at=None,
            ),
            FeedItem(
                title="Closed Islamabad meetup",
                url="https://news.google.com/item/closed",
                summary="Registration is closed. Meetup on December 14, 2099.",
                published_at=None,
            ),
            FeedItem(
                title="Islamabad AI hackathon!",
                url="https://news.google.com/item/open-duplicate",
                summary=f"{registration} Teams of 3-5 members. National event on December 12, 2099. Online.",
                published_at=None,
            ),
            FeedItem(
                title="Past Islamabad hackathon",
                url="https://news.google.com/item/past",
                summary="Hackathon on January 1, 2000.",
                published_at=None,
            ),
            FeedItem(
                title="Karachi hackathon",
                url="https://news.google.com/item/out-of-scope",
                summary="Registration is open. Teams of 4. Event on December 15, 2099.",
                published_at=None,
            ),
            FeedItem(
                title="Virtual technology workshop",
                url="https://news.google.com/item/online-unclear",
                summary="Online workshop on December 16, 2099.",
                published_at=None,
            ),
            FeedItem(
                title="Islamabad baking workshop",
                url="https://news.google.com/item/non-tech",
                summary="A cooking workshop on December 17, 2099.",
                published_at=None,
            ),
            FeedItem(
                title="mufti Mehmood conference",
                url="https://news.google.com/item/non-tech-conference",
                summary="A public conference on December 18, 2099.",
                published_at=None,
            ),
        ]


class EmptyConnector:
    def __init__(self):
        self.source_ids = []

    async def fetch(self, source: Source) -> list[FeedItem]:
        self.source_ids.append(source.id)
        return []


class DeniedConnector:
    async def fetch(self, source: Source) -> list[FeedItem]:
        raise PermissionError("robots.txt does not allow fetching this feed")


class RobotsUnavailableConnector:
    async def fetch(self, source: Source) -> list[FeedItem]:
        raise ingest.RobotsFetchError("robots.txt could not be fetched: connection failed")


async def no_ai(title: str, text: str, facts: dict) -> dict:
    return facts


def test_refresh_persists_and_filters_future_events(tmp_path, monkeypatch):
    source = Source(
        id="fixture-feed",
        name="Fixture community feed",
        kind="rss",
        url="https://news.google.com/rss",
        publisher="Fixture",
    )
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "events.sqlite")
    monkeypatch.setattr(main, "load_sources", lambda: [source])
    connector = FixtureConnector()
    monkeypatch.setattr(ingest, "CONNECTORS", {"rss": connector})
    monkeypatch.setattr(ingest, "enrich_with_groq", no_ai)

    with TestClient(main.app) as client:
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO events (
                    id, title, event_date, category, registration_status,
                    source_name, source_url, source_text, last_checked, first_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "stale-non-tech",
                    "mufti Mehmood conference",
                    "2099-12-18",
                    "Tech event",
                    "unknown",
                    source.name,
                    "https://news.google.com/item/non-tech-conference",
                    "Previously misclassified non-technical conference",
                    "2099-01-01",
                    "2099-01-01",
                ),
            )
        response = client.post("/api/refresh")
        assert response.status_code == 200
        assert response.json()["events_saved"] == 2
        assert response.json()["sources_attempted"] == 1
        assert response.json()["sources_succeeded"] == 1
        assert response.json()["sources_failed"] == 0

        all_events = client.get("/api/events").json()["events"]
        assert len(all_events) == 2
        assert all("conference" not in event["title"].lower() for event in all_events)
        assert {event["registration_status"] for event in all_events} == {"open", "unknown"}
        assert all("source_text" not in event for event in all_events)

        open_events = client.get("/api/events?registration=open").json()["events"]
        assert len(open_events) == 1
        assert open_events[0]["team_size"] == "3–5 members"
        assert open_events[0]["level"] == "National"

        sources = client.get("/api/sources").json()
        assert sources[0]["name"] == source.name
        assert sources[0]["last_checked"] is not None
        assert sources[0]["crawl_status"] == "success"
        assert sources[0]["items_found"] == 9
        assert sources[0]["events_saved"] == 2
        assert sources[0]["crawl_policy"] == "eligible"
        assert sources[0]["last_attempted"] is not None

        connector.close_hackathons = True
        assert client.post("/api/refresh").status_code == 200
        remaining = client.get("/api/events").json()["events"]
        assert len(remaining) == 1
        assert remaining[0]["category"] == "Tech workshop"


def test_refresh_reports_noneligible_sources_as_skipped(tmp_path, monkeypatch):
    source = Source(
        id="review-source",
        name="Review-required source",
        kind="discover",
        url="https://example.com/events",
        publisher="Fixture",
        enabled=False,
        crawl_policy="review_required",
    )
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "events.sqlite")
    monkeypatch.setattr(main, "load_sources", lambda: [source])
    connector = FixtureConnector()
    monkeypatch.setattr(ingest, "CONNECTORS", {"discover": connector})

    with TestClient(main.app) as client:
        response = client.post("/api/refresh")
        status = client.get("/api/sources").json()[0]

    assert response.status_code == 200
    assert response.json()["sources_attempted"] == 0
    assert response.json()["sources_skipped"] == 1
    assert status["crawl_status"] == "review_required"
    assert status["last_attempted"] is None
    assert connector.close_hackathons is False


def test_refresh_reports_robots_denial_as_failed_attempt(tmp_path, monkeypatch):
    source = Source(
        id="blocked-feed",
        name="Blocked feed",
        kind="rss",
        url="https://example.com/feed.xml",
        publisher="Fixture",
    )
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "events.sqlite")
    monkeypatch.setattr(main, "load_sources", lambda: [source])
    monkeypatch.setattr(ingest, "CONNECTORS", {"rss": DeniedConnector()})

    with TestClient(main.app) as client:
        response = client.post("/api/refresh")
        status = client.get("/api/sources").json()[0]

    assert response.status_code == 200
    assert response.json()["sources_attempted"] == 1
    assert response.json()["sources_failed"] == 1
    assert response.json()["errors"][0]["source"] == "Blocked feed"
    assert status["crawl_status"] == "robots_denied"
    assert status["last_attempted"] is not None
    assert "robots.txt" in status["last_error"]


def test_refresh_reports_robots_fetch_failure_separately_from_denial(tmp_path, monkeypatch):
    source = Source(
        id="unavailable-robots",
        name="Robots unavailable",
        kind="rss",
        url="https://example.com/feed.xml",
        publisher="Fixture",
    )
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "events.sqlite")
    monkeypatch.setattr(main, "load_sources", lambda: [source])
    monkeypatch.setattr(ingest, "CONNECTORS", {"rss": RobotsUnavailableConnector()})

    with TestClient(main.app) as client:
        result = client.post("/api/refresh").json()
        status = client.get("/api/sources").json()[0]

    assert result["sources_failed"] == 1
    assert status["crawl_status"] == "robots_unavailable"
    assert "could not be fetched" in status["last_error"]


def test_duplicate_event_keeps_source_attribution_with_extracted_facts(tmp_path, monkeypatch):
    first = Source(
        id="first-source",
        name="First source",
        kind="first",
        url="https://first.example/feed.xml",
        publisher="Fixture",
    )
    second = Source(
        id="second-source",
        name="Second source",
        kind="second",
        url="https://second.example/feed.xml",
        publisher="Fixture",
    )

    class DuplicateConnector:
        def __init__(self, event_url: str, team_size: int):
            self.event_url = event_url
            self.team_size = team_size

        async def fetch(self, _source: Source) -> list[FeedItem]:
            return [
                FeedItem(
                    title="Islamabad AI hackathon",
                    url=self.event_url,
                    summary=(
                        f"Registration open. Teams of {self.team_size}. "
                        "National event on December 12, 2099. Online."
                    ),
                    published_at=None,
                )
            ]

    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "events.sqlite")
    monkeypatch.setattr(main, "load_sources", lambda: [first, second])
    monkeypatch.setattr(
        ingest,
        "CONNECTORS",
        {
            "first": DuplicateConnector("https://first.example/event", 2),
            "second": DuplicateConnector("https://second.example/event", 4),
        },
    )
    monkeypatch.setattr(ingest, "enrich_with_groq", no_ai)

    with TestClient(main.app) as client:
        response = client.post("/api/refresh")
        events = client.get("/api/events").json()["events"]

    assert response.status_code == 200
    assert len(events) == 1
    event = events[0]
    attribution = {
        "First source": ("https://first.example/event", "2 members"),
        "Second source": ("https://second.example/event", "4 members"),
    }
    assert (event["source_url"], event["team_size"]) == attribution[event["source_name"]]


def test_refresh_attempts_and_reports_every_eligible_registry_source(tmp_path, monkeypatch):
    sources = load_sources()
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "events.sqlite")
    monkeypatch.setattr(main, "load_sources", lambda: sources)
    connector = EmptyConnector()
    monkeypatch.setattr(
        ingest,
        "CONNECTORS",
        {"rss": connector, "event-directory": connector, "discover": connector},
    )

    with TestClient(main.app) as client:
        response = client.post("/api/refresh")
        source_statuses = client.get("/api/sources").json()

    assert response.status_code == 200
    result = response.json()
    assert result["sources_attempted"] == 60
    assert result["sources_succeeded"] == 0
    assert result["sources_empty"] == 60
    assert result["sources_skipped"] == 0
    assert result["sources_failed"] == 0
    assert len(connector.source_ids) == 60
    assert len(source_statuses) == 60
    assert all(source["crawl_status"] == "empty" for source in source_statuses)
    assert all(source["last_attempted"] for source in source_statuses)
