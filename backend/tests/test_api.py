from fastapi.testclient import TestClient

from app import db, ingest, main
from app.sources import FeedItem, Source


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

        connector.close_hackathons = True
        assert client.post("/api/refresh").status_code == 200
        remaining = client.get("/api/events").json()["events"]
        assert len(remaining) == 1
        assert remaining[0]["category"] == "Tech workshop"
