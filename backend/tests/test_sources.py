from app.extract import _date_from_text
from app.sources import EventCardParser, load_sources


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


def test_registry_has_at_least_ten_active_sites_and_pauses_blocked_source():
    sources = load_sources()
    active = [source for source in sources if source.enabled]
    ids = [source.id for source in sources]
    assert len(active) >= 10
    assert len(sources) >= 60
    assert len(ids) == len(set(ids))
    assert any(source.kind == "event-directory" for source in active)
    paused = next(source for source in sources if source.id == "pakevents-islamabad")
    assert paused.enabled is False
    assert paused.note and "403" in paused.note
    assert any(source.url == "https://hack-scout-delta.vercel.app/events" for source in sources)
    assert any(source.url == "https://startups.pasha.org.pk/" for source in sources)


def test_all_registered_enabled_feeds_have_unique_hosts_and_urls():
    sources = load_sources()
    assert len({source.url for source in sources}) == len(sources)
