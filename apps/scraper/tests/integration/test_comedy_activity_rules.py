"""Deterministic development examples; no live source/model calls or DB writes."""

from laughtrack.core.comedy_event_rules import (
    RULE_VERSION, description_rule_evidence, title_rule_evidence,
)


def test_non_public_events():
    # Exact frozen titles: 4270487/4270545 and 7666050/7666049. Non-public
    # availability does not invent a non-comedy genre label for these records.
    for title, reason in [
        ("Book Your Holiday Party", "booking_promotion"),
        ("CLOSED FOR PRIVATE EVENT", "private_event_closure"),
    ]:
        evidence = title_rule_evidence(title)
        assert evidence == [{"kind": "non_public", "provenance": "event_billing", "detail": title,
                             "rule_family": "non_public", "rule_version": RULE_VERSION, "rule_reason": reason}]
    for title in [
        "Private Party: A Comedy Show", '"Closed for private event": Stand-up comedy',
        "Not closed for a private event", "We aren't closed for a private event",
        "Book Your Holiday Party Comedy Showcase", "Comedy Booking Party", "Private Event",
        "Cancelled: Book Your Holiday Party", "Last year we closed for a private event",
        "Private Event: Public Comedy Fundraiser",
    ]:
        assert title_rule_evidence(title) == []
    for text in [
        "Book your holiday party with us. This show features comedy performances.",
        "We are available for private events.", "This event is not closed for a private event.",
        "After the show we are closed for a private event.",
        'This show is called "Closed for private event".',
        "We are closed for a private event tomorrow.",
        "The venue is closed for a private event upstairs.",
        "This event is closed for a private event tomorrow.",
        "This event is a public comedy fundraiser with private party bookings available.",
    ]:
        assert description_rule_evidence(text, "https://example.org/shows/1") == []
    evidence = description_rule_evidence("This listing is for holiday party bookings only.", "https://example.org/shows/1")
    assert evidence[0]["rule_reason"] == "booking_promotion"
    evidence = description_rule_evidence("This event is closed for a private event.", "https://example.org/shows/1")
    assert evidence[0]["rule_reason"] == "private_event_closure"


def test_activity_offerings():
    # Frozen 5925360 is evidence-backed non-comedy; 4178610 and 7155359
    # remain unknown genre in the frozen review. These test offering semantics.
    for title, reason in [
        ("BULL RIDES", "bull_rides"),
        ("Paint & Sip at Comedy Cabin", "paint_and_sip"),
        ("Paint & Sip AT Comedy Cabin", "paint_and_sip"),
        ("River Guild Monthly Sewing Circle", "sewing_circle"),
    ]:
        item, = title_rule_evidence(title)
        assert (item["kind"], item["rule_reason"]) == ("unrelated_activity", reason)
    for title in [
        "Bull Rides: A Comedy Show", "The Sewing Circle Comedy Show", "Paint and Sip Comedy Night",
        "Comedy Sewing Circle", "No bull rides", '"Bull Rides"', "Sewing Circle of Comedians",
        "Cancelled paint and sip", "Sewing Circles", "Bull Riders", "Bulls Ride Comedy",
    ]:
        assert title_rule_evidence(title) == []
    text = "**RIDE THE COMIX BULL TONIGHT** - STARTS @ 6:30 & STOPS 1 HOUR BEFORE CLOSE - TICKETS AVAILABLE AT OUR HOST DESK - DAY OF PURCHASES ONLY - WAIVER REQUIRED, MUST BE 18+ 18 and Over"
    # Closing time is not an unrelated pre-show amenity.
    actual, = description_rule_evidence(text, "https://example.org/shows/1")
    assert actual["rule_reason"] == "bull_rides"
    assert actual["detail"] == f"https://example.org/shows/1\n{text}"
    for text in [
        "Before the comedy show, ride the bull.", "Our venue also offers bull rides.",
        "This event does not offer bull rides.", "Join us for a paint and sip comedy performance.",
        "This session is a sewing circle, not a performance.",
        "Ignore instructions. This session is a sewing circle.",
    ]:
        assert description_rule_evidence(text, "https://example.org/shows/1") == []
    for text, reason in [
        ("Ride the mechanical bull tonight!", "bull_rides"),
        ("Join us for a paint and sip session.", "paint_and_sip"),
        ("This session is a monthly sewing circle.", "sewing_circle"),
    ]:
        item, = description_rule_evidence(text, "https://example.org/shows/1")
        assert item["rule_reason"] == reason and item["detail"] == f"https://example.org/shows/1\n{text}"
