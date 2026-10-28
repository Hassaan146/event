from datetime import date

from app.extract import _date_from_text, is_future_event, is_relevant_to_islamabad, local_extract


def test_extracts_supported_event_facts():
    facts = local_extract(
        "Islamabad university hackathon",
        "Registration is open. Teams of 3-5 members. National event on December 12, 2099. Online.",
    )
    assert facts["event_date"] == "2099-12-12"
    assert facts["category"] == "Hackathon"
    assert facts["registration_status"] == "open"
    assert facts["team_size"] == "3–5 members"
    assert facts["format"] == "Online"
    assert facts["level"] == "National"


def test_unknown_facts_are_not_invented():
    facts = local_extract("Hackathon in Islamabad", "Details will be announced soon.")
    assert facts["event_date"] is None
    assert facts["registration_status"] == "unknown"
    assert facts["team_size"] is None
    assert facts["eligibility"] is None


def test_date_parsing_and_future_filter():
    assert _date_from_text("Event is on 2099-02-28") == "2099-02-28"
    assert _date_from_text("Workshop on February 28, 2099") == "2099-02-28"
    assert _date_from_text("Workshop on 31 February 2099") is None
    assert is_future_event("2099-02-28", date(2099, 2, 28))
    assert not is_future_event("2099-02-27", date(2099, 2, 28))
    assert not is_future_event(None)


def test_islamabad_scope_requires_local_or_broad_online_access_evidence():
    assert is_relevant_to_islamabad(
        "Islamabad national hackathon online",
        {"format": "Online", "level": "National"},
    )
    assert not is_relevant_to_islamabad(
        "Virtual workshop with registration details to be announced",
        {"format": "Online", "level": None},
    )
    assert not is_relevant_to_islamabad(
        "Karachi in-person meetup",
        {"format": "In-person", "level": None},
    )
