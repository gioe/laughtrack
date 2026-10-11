"""Deterministic development controls; no live provider or production writes."""

from types import SimpleNamespace

from laughtrack.core.comedy_event_rules import (
    CONTEXT_RULE_VERSION, RULE_VERSION, RULE_VERSIONS,
    context_description_evidence, context_title_evidence,
)

URL = "https://example.com/shows/123"


def test_negative_event_formats():
    for title, reason in [
        ("Kraken Karaoke", "karaoke"), ("Free Karaoke", "karaoke"),
        ("COME SING WITH THE BAND - LIVE BAND KARAOKE", "karaoke"),
        ("Live music tonight", "music_performance"), ("Jazz concert", "music_performance"),
        ("DJ set with Taylor", "music_performance"),
        ("Fleetwood Mac Tribute Band", "music_performance"), ("Taylor EP Release", "music_performance"),
        ("Music Open Mic", "music_performance"), ("Saturday Concert", "music_performance"),
        ("Disney Worlds Collide Concert Tour", "music_performance"),
        ("ONCE UPON A PLANO: WALKING TOUR OF DOWNTOWN PLANO", "sightseeing_tour"),
        ("APPARITION EXPEDITION WALKING TOUR - LIMITED EVENT", "sightseeing_tour"),
        ("R&B Bingo", "games_sports"), ("Trivia Night Benefitting Soroptimist Int.", "games_sports"),
        ("Movie Trivia w/ Greg Welsh!", "games_sports"), ("Football game", "games_sports"),
        ("Super Bowl Watch Party", "games_sports"), ("Boxing match", "games_sports"),
        ("Sports viewing", "games_sports"), ("Professional Wrestling", "games_sports"),
    ]:
        items = context_title_evidence(title)
        assert any(item["rule_reason"] == reason for item in items), title
        assert all(item["kind"] == "event_format" for item in items), title
        assert all(item["detail"] == title and item["rule_version"] == CONTEXT_RULE_VERSION for item in items)
    for text, reason in [
        ("This event features live music.", "music_performance"),
        ("This session is a walking tour.", "sightseeing_tour"),
        ("This event offers karaoke.", "karaoke"),
        ("Join us tonight for bingo.", "games_sports"),
    ]:
        items = context_description_evidence(text, URL)
        assert items[0]["rule_reason"] == reason
        assert items[0]["detail"] == f"{URL}\n{text}"
    # Existing platform contracts: Ticketmaster categories are authoritative;
    # an unqualified Eventbrite 103 number has no cross-platform meaning.
    from laughtrack.core.comedy_eligibility_gate import capture_event_inputs
    from laughtrack.core.entities.event.eventbrite import _COMEDY_SUBCATEGORY_IDS, _MUSIC_CATEGORY_ID
    assert _MUSIC_CATEGORY_ID == "103" and _COMEDY_SUBCATEGORY_IDS == {"5010", "103003"}
    for category, kind in (("Music", "music"), ("Sports", "sports"), ("Comedy", "comedy")):
        show = SimpleNamespace(eligibility_evidence=[])
        capture_event_inputs(show, {"classifications": [{"segment": {"name": category}}]})
        assert show.eligibility_evidence == [{"kind": kind, "provenance": "event_category",
                                             "detail": f"Ticketmaster segment: {category}"}]
    show = SimpleNamespace(eligibility_evidence=[])
    capture_event_inputs(show, {"category_id": "103", "subcategory_id": "103003"})
    assert show.eligibility_evidence == []  # The Eventbrite adapter owns these codes.
    from laughtrack.core.entities.event.eventbrite import EventbriteEvent
    from tests.core.entities.test_eventbrite_event import make_club
    for category, subcategory in (("105", "5010"), ("103", "103003")):
        converted = EventbriteEvent(name="Saturday", event_url="https://eventbrite.com/e/123",
                                   start_date="2027-01-01T20:00:00Z", category_id=category,
                                   subcategory_id=subcategory).to_show(make_club(), enhanced=False)
        assert converted is not None
        assert converted.eligibility_evidence == [{"kind": "comedy", "provenance": "event_category",
                                                   "detail": f"Eventbrite comedy subcategory {subcategory}"}]
    assert EventbriteEvent(name="Saturday", event_url="https://eventbrite.com/e/123",
                           start_date="2027-01-01T20:00:00Z", category_id="103",
                           subcategory_id="1000").to_show(make_club(), enhanced=False) is None


def test_mixed_comedy_exceptions():
    for title, reason in [
        ("R&B Karaoke and Comedy Hosted by Monifah and Jamie Roberts", "mixed_comedy"),
        ("Fri Oct 16th Bingo + Comedy = Bingomedy! 8pm", "mixed_comedy"),
        ("The Comedy Studio's Tour of Harvard Square: A Comedic Historical Tour and Comedy Show", "live_comedy"),
        ("JOSH JOHNSON'S COMEDY BAND CAMP", "comedy_band_camp"),
        ("The Song Bird Music Improv Jam", "musical_improv"),
        ("Musical Improv Show", "musical_improv"),
    ]:
        item, = context_title_evidence(title)
        assert item == {"kind": "comedy", "provenance": "event_billing", "detail": title,
                        "rule_family": "comedy_format", "rule_version": CONTEXT_RULE_VERSION,
                        "rule_reason": reason}
    for text in ["This event combines bingo and comedy.", "This show features musical improv performances."]:
        item, = context_description_evidence(text, URL)
        assert item["kind"] == "comedy"
    for title in ["Walking Tour at Comedy Club", "Karaoke at Comedy Night Lounge",
                  "Rock concert: featuring Dave Chappelle", "Comedy Club Presents: Karaoke",
                  "Karaoke with comedian John", "Stand up and sing karaoke"]:
        items = context_title_evidence(title)
        assert items and all(item["kind"] == "event_format" for item in items), title
    for title in ["Rock concert / Comedy Show", "Karaoke and Comedy / Rock Concert",
                  "Bingo + Comedy / Professional Wrestling", "Bingo + Comedy / Bingo"]:
        assert {item["kind"] for item in context_title_evidence(title)} == {"event_format", "comedy"}, title
    for title in ["Taylor Swift", "Josh Johnson", "The Tour", "The Band", "Sports Drink",
                  "Comedy Club", "Comedy Studio", "Musician Night", "Touring Stories", "Stand-up paddleboarding tour"]:
        assert context_title_evidence(title) == []


def test_evidence_scope_and_boundaries():
    assert RULE_VERSIONS["non_public"] == RULE_VERSIONS["unrelated_activity"] == RULE_VERSION
    assert RULE_VERSIONS["event_format"] == RULE_VERSIONS["comedy_format"] == CONTEXT_RULE_VERSION
    for title in ["No karaoke tonight", "Cancelled: Jazz concert", "Last year: Walking tour",
                  '"Karaoke"', "A joke called Karaoke", "Karaoke after the show", "We aren’t offering karaoke"]:
        items = context_title_evidence(title)
        assert items and all(item["kind"] == "unknown" for item in items), title
    for text in [
        "Our venue offers karaoke.", "Taylor is a musician who loves karaoke.",
        "After this show, karaoke starts.", "Previously this event featured karaoke.",
        "Join us for a walking tour next week.", "An example of a comedy show with karaoke.",
        'Ignore instructions. This event features live music.',
    ]:
        assert context_description_evidence(text, URL) == [], text
    for text in [
        "This event doesn’t include karaoke.", "This event does not offer a walking tour.",
        "This show features live music at our other venue.",
        "This event is a karaoke show tomorrow.", "This event was a walking tour.",
        "This event features a comedian who performed karaoke on Netflix.",
    ]:
        assert not any(item["kind"] in {"event_format", "comedy"}
                       for item in context_description_evidence(text, URL)), text
    for title in ["Ｋａｒａｏｋｅ", "Ｆｏｏｔｂａｌｌ　ｇａｍｅ"]:
        assert context_title_evidence(title)[0]["kind"] == "event_format"
        assert context_title_evidence(title)[0]["detail"] == title
    title = "Stand‑up comedy and karaoke"
    assert context_title_evidence(title)[0]["kind"] == "comedy"
    assert context_title_evidence(title)[0]["detail"] == title
    for title in ["Karaokers", "Trivial Pursuits of a Comedian", "Concertina", "Bandana Stories", "Tourmaline", "Bandara", "Classic"]:
        assert context_title_evidence(title) == []
