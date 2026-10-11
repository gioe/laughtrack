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
    for text in ["This event features Elvis, who starred in a comedy show.",
                 "This event features music by the cast of a comedy show.",
                 "This event is a concert with songs from a comedy show."]:
        assert not any(item["kind"] == "comedy" for item in context_description_evidence(text, URL)), text
    assert context_description_evidence("This event doesn’t include karaoke.", URL)[0]["kind"] == "unknown"
    for title in ["Ｋａｒａｏｋｅ", "Ｆｏｏｔｂａｌｌ　ｇａｍｅ"]:
        assert context_title_evidence(title)[0]["kind"] == "event_format"
        assert context_title_evidence(title)[0]["detail"] == title
    title = "Stand‑up comedy and karaoke"
    assert context_title_evidence(title)[0]["kind"] == "comedy"
    assert context_title_evidence(title)[0]["detail"] == title
    for title in ["Music from a Comedy Show", "Songs from Stand-up Comedy",
                  "Karaoke featuring songs from a Comedy Show", "Songs from Karaoke and Comedy"]:
        assert not any(item["kind"] == "comedy" for item in context_title_evidence(title)), title
    for title in ["Karaokers", "Trivial Pursuits of a Comedian", "Concertina", "Bandana Stories", "Tourmaline", "Bandara", "Classic"]:
        assert context_title_evidence(title) == []


def test_rule_decision_integration(monkeypatch):
    from dataclasses import replace
    from datetime import datetime, timezone
    from laughtrack.core.comedy_eligibility import (
        CLASSIFIER_VERSION, CanonicalPerson, DeniedName, EventEvidence,
        PerformerObservation, classify_comedy_eligibility,
    )
    from laughtrack.core.comedy_eligibility_gate import capture_event_inputs, event_evidence
    from laughtrack.core.comedy_eligibility_model import ModelConfig, eligible
    from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy
    from laughtrack.core.comedy_event_rules import title_rule_evidence
    from tests.integration.test_comedy_event_evidence import event
    from tests.integration.test_comedy_eligibility_gate import _gate_environment, _gate_show, _writer_handler

    def classify(title="Saturday", payload=None, **kwargs):
        show = SimpleNamespace(name=title, description="This show features comedy performances.", eligibility_evidence=[])
        if payload is not None:
            capture_event_inputs(show, payload)
            capture_event_inputs(show, payload)
        return classify_comedy_eligibility(source_id=7, policy=kwargs.pop("policy", SourceComedyPolicy()),
                                           evidence=event_evidence(show), **kwargs)

    assert CLASSIFIER_VERSION == "comedy-eligibility-v2-rules-v2"
    positives = ["R&B Karaoke and Comedy Hosted by Monifah and Jamie Roberts",
                 "Fri Oct 16th Bingo + Comedy = Bingomedy! 8pm",
                 "The Comedy Studio's Tour of Harvard Square: A Comedic Historical Tour and Comedy Show",
                 "JOSH JOHNSON'S COMEDY BAND CAMP", "The Song Bird Music Improv Jam"]
    for title in positives:
        decision = classify(title)
        assert decision.decision == "accept", title
        assert "affirmative_event_comedy" in decision.reason_codes
        assert "explicit_unrelated_activity" not in decision.reason_codes
        assert decision.evidence[0].rule_family == "comedy_format"
        saved = decision.to_dict()
        replay = classify_comedy_eligibility(source_id=7, policy=SourceComedyPolicy(),
                                             evidence=[EventEvidence(**item) for item in saved["evidence"]])
        assert replay.to_dict() == saved
    for title in ["Free Karaoke", "Rock concert", "Ghost Tour", "R&B Bingo", "Professional Wrestling",
                  "Walking Tour at Comedy Club", "Karaoke at Comedy Night Lounge"]:
        decision = classify(title)
        assert decision.decision == "reject", title
        assert "explicit_non_comedy_event" in decision.reason_codes
        assert any(code.startswith("rule_event_format_") for code in decision.reason_codes)
        assert not eligible(decision)
    for title in ["Music from a Comedy Show", "Songs from Stand-up Comedy"]:
        assert classify(title).decision == "review", title
    assert classify("Karaoke featuring songs from a Comedy Show").decision == "reject"
    for title in ["Karaoke featuring songs from a Comedy Show + Stand-up Comedy Show",
                  "Karaoke featuring songs from a Comedy Show and Stand-up Comedy Show"]:
        result = classify(title)
        assert result.decision == "review" and "conflicting_event_evidence" in result.reason_codes, title
    assert classify().decision == "review"  # No evidence; arbitrary description ignored.
    for payload in ({"classifications": None}, {"classifications": [None]},
                    {"classifications": [{"segment": {"name": "Unknown"}}]}, {}):
        assert classify(payload=payload).decision == "review"
    categories = {"classifications": [{"segment": {"name": "Music"}}, {"genre": {"name": "Comedy"}}]}
    assert classify(payload=categories).decision == "review"
    for title in positives:
        for category in ("Music", "Sports"):
            conflict = classify(title, {"classifications": [{"segment": {"name": category}}]})
            assert conflict.decision == "review" and "conflicting_event_evidence" in conflict.reason_codes
            assert not eligible(conflict)
    for title in ["Rock concert / Comedy Show", "Karaoke and Comedy / Rock Concert",
                  "Bingo + Comedy / Professional Wrestling"]:
        assert classify(title).decision == "review"
    for title, text in [
        ("Karaoke", "This event doesn’t include karaoke."),
        ("Comedy Show", "This show doesn’t feature comedy performances."),
        ("Rock concert", "This show features comedy performances."),
        ("Stand-up comedy show", "This event features live music."),
    ]:
        decision = classify(title, event(text))
        assert decision.decision == "review", (title, text)
        assert not eligible(decision)
    trusted = SourceComedyPolicy(policy="comedy_only", reviewed_by="reviewer",
                                 reviewed_at=datetime(2026, 10, 11, tzinfo=timezone.utc),
                                 evidence={"calendar": "reviewed"})
    for title in ["No karaoke tonight", "Cancelled: stand-up comedy", "No live music tonight",
                  "We aren’t offering karaoke", "Previously: Comedy Show"]:
        assert classify(title, policy=trusted).decision == "review", title
    performance_list = "This show features comedy, burlesque and live music performances."
    assert any(item["kind"] == "comedy" for item in context_description_evidence(performance_list, URL))
    result = classify(payload=event(performance_list))
    assert result.decision == "review" and "conflicting_event_evidence" in result.reason_codes
    assert classify(payload=event("This event features stand-up performances.")).decision == "accept"
    # Same-event description hybrids remove only duplicate signals for that
    # sentence. Another negative sentence remains independently conflicting.
    assert classify(payload=event("This event combines karaoke and comedy.")).decision == "accept"
    detail = "This event combines karaoke and comedy. This event features live music."
    assert classify(payload=event(detail)).decision == "review"
    for text in ["This show features live music at our other venue.",
                 "This show features comedy performances at our other venue.",
                 "She is a comedian. Previously she performed a night of comedy.",
                 'This is called "Comedy Show". This event is a rock concert.',
                 "This event features Elvis, who starred in a comedy show.",
                 "This event features music by the cast of a comedy show.",
                 "This event features music by the cast of the comedy show.",
                 "This event is a concert with songs from a comedy show."]:
        decision = classify(payload=event(text))
        assert decision.decision != "accept", text
    for changes in ({"event_id": "99"}, {"selector": "#bio"}, {"status": "failed"}):
        assert classify(payload=event("This event offers karaoke.", **changes)).decision == "review"

    # Historical v1 records and their legacy three-field neighbors still replay.
    old = EventEvidence(**title_rule_evidence("BULL RIDES")[0])
    assert old.valid and old.rule_version == RULE_VERSION
    legacy = EventEvidence("comedy", "event_category", "Eventbrite comedy subcategory 103003")
    old_decision = classify_comedy_eligibility(source_id=7, policy=SourceComedyPolicy(), evidence=[old, legacy])
    assert old_decision.decision == "review"
    assert {"kind", "provenance", "detail"} == set(next(item for item in old_decision.to_dict()["evidence"]
                                                        if item["kind"] == "comedy"))
    typed = EventEvidence(**context_title_evidence("Karaoke")[0])
    for malformed in [replace(typed, rule_version=RULE_VERSION), replace(typed, rule_family="comedy_format"),
                      replace(typed, rule_reason="unknown"), replace(typed, provenance="venue_description"),
                      replace(typed, rule_version=None), replace(legacy, rule_family="comedy_format")]:
        result = classify_comedy_eligibility(source_id=7, policy=trusted, evidence=[malformed])
        assert result.decision == "review" and "invalid_event_evidence" in result.reason_codes
        assert not eligible(result)

    parent = CanonicalPerson(1, "Root", True)
    alias = CanonicalPerson(2, "Alias", False, parent_id=1, block_reason="duplicate")
    blocked = CanonicalPerson(3, "Blocked", False, block_reason="not a comic")
    assert classify(positives[0], people=[parent, alias], performers=[PerformerObservation("Alias")]).decision == "accept"
    assert classify(people=[blocked], performers=[PerformerObservation("Blocked")]).decision == "reject"
    assert classify(positives[0], people=[blocked], performers=[PerformerObservation("Blocked")]).decision == "review"
    assert classify(positives[0], people=[parent, blocked], denied=[DeniedName("Another Blocked", "deny_list")],
                    performers=[PerformerObservation("Root"), PerformerObservation("Blocked"),
                                PerformerObservation("Another Blocked")]).decision == "review"
    troupe = CanonicalPerson(4, "Troupe", False, block_reason="show label", entity_kind="troupe")
    structural = PerformerObservation("Troupe", structural_kind="troupe", structural_evidence="Reviewed actual troupe")
    assert classify(positives[0], people=[troupe], performers=[structural]).decision == "accept"
    assert classify("Karaoke", people=[troupe], performers=[structural]).decision == "reject"
    assert classify(positives[0], people=[troupe], performers=[structural],
                    denied=[DeniedName("Troupe", "non_comedian_musician", "troupe")]).decision == "review"
    assert not ModelConfig().enabled

    # Exercise the real write boundary with no network/model provider enabled.
    monkeypatch.setenv("COMEDY_MODEL_ENABLED", "0")
    for mode in ("off", "shadow", "enforce"):
        for title, expected in (("Karaoke", "reject"), (positives[0], "accept"),
                                ("Rock concert / Comedy Show", "review")):
            state = _gate_environment(monkeypatch, mode)
            handler = _writer_handler(monkeypatch, state)
            result = handler.insert_shows([_gate_show(title)])
            withheld = mode == "enforce" and expected != "accept"
            assert result.total == (0 if withheld else 1)
            if withheld:
                assert result.eligibility_withheld == 1 and not result.reconciliation_safe
                handler._persist_show_partitions.assert_not_called()
                handler._update_shows_and_related.assert_not_called()
            else:
                handler._persist_show_partitions.assert_called_once()
                handler._update_shows_and_related.assert_called_once()
            if mode == "off":
                assert state.staged == []
            else:
                assert state.staged[0]["decision"].decision == expected
                assert state.staged[0]["decision"].classifier_version == CLASSIFIER_VERSION
