"""Faithful reduced markup from https://www.comedycastle.com/events/ (2026-09-25)."""

from datetime import date

import pytest

from laughtrack.scrapers.implementations.api.etix.rockhouse import extract_rockhouse_events

TODAY = date(2026, 9, 25)
MIKE = "https://www.etix.com/ticket/p/62115951/mike-cronin-royal-oak-mark-ridleys-comedy-castle?partner_id=100"
THANKSGIVING = "https://www.etix.com/ticket/p/50537895/the-night-before-thanksgiving-comedy-special-royal-oak-mark-ridleys-comedy-castle?partner_id=100"


def series(title, slug, rows):
    # These selectors and Show | strings are retained from actual public markup.
    entries = "".join(
        f'<li class="rhp-event-series-individual"><div class="rhp-event-series-date">{day}</div><div class="rhp-event-series-time">{time}</div><a href="{url}">Tickets</a></li>'
        for day, time, url in rows
    )
    return f'<div class="rhp-event__single-series--list"><h2 class="rhpEventHeader"><a href="https://www.comedycastle.com/events/category/series/{slug}/mark-ridleys-comedy-castle/royal-oak/">{title}</a></h2><ul>{entries}</ul></div>'


def test_explicit_pipe_showtimes_keep_distinct_early_late_performances():
    html = '<div class="rhp-events-list-separator-month">December 2026</div>' + series(
        "CAM ROWE",
        "cam-rowe",
        [
            (
                "Dec 26",
                "Show | 7 pm",
                "https://www.etix.com/ticket/p/92131822/cam-rowe-royal-oak-mark-ridleys-comedy-castle?partner_id=100",
            ),
            (
                "Dec 26",
                "Show | 9:30 pm",
                "https://www.etix.com/ticket/p/45478958/cam-rowe-royal-oak-mark-ridleys-comedy-castle?partner_id=100",
            ),
        ],
    )
    events = extract_rockhouse_events(html, TODAY)
    assert [e.start_date for e in events] == ["2026-12-26T19:00:00", "2026-12-26T21:30:00"]


@pytest.mark.parametrize(
    "showtime", ["", "Doors: 7 pm", "7 pm", "Show | 13 pm", "Show | 7:65 pm", "Show | 7 pm / Show | 9 pm"]
)
def test_no_default_or_doors_or_invalid_showtime(showtime):
    assert extract_rockhouse_events(series("MIKE CRONIN", "mike-cronin", [("Oct 15", showtime, MIKE)]), TODAY) == []


def test_invalid_calendar_date_is_rejected():
    assert extract_rockhouse_events(series("MIKE CRONIN", "mike-cronin", [("Feb 30", "Show: 7 pm", MIKE)]), TODAY) == []


def test_conflicting_performance_identity_is_rejected_in_both_card_orders():
    cam = series("CAM ROWE", "cam-rowe", [("Oct 15", "Show | 7:30 pm", MIKE)])
    mike = series("MIKE CRONIN", "mike-cronin", [("Oct 15", "Show | 7:30 pm", MIKE)])
    classroom = series(
        "ADVANCED COMEDY CLASS SHOWCASE", "advanced-comedy-class-showcase", [("Nov 25", "Show | 7:30 pm", THANKSGIVING)]
    )
    holiday = series(
        "THE NIGHT BEFORE THANKSGIVING SPECIAL",
        "the-night-before-thanksgiving-special",
        [("Nov 25", "Show | 7:30 pm", THANKSGIVING)],
    )
    assert extract_rockhouse_events(cam + mike + classroom + holiday, TODAY) == []
    assert extract_rockhouse_events(holiday + classroom + mike + cam, TODAY) == []


def test_nested_card_never_borrows_descendant_performances():
    child = series("MIKE CRONIN", "mike-cronin", [("Oct 15", "Show: 7:30 pm", MIKE)])
    html = (
        '<div class="rhp-event__single-series--list"><h2 class="rhpEventHeader"><a href="https://example.com/parent">PARENT WITHOUT SHOWTIMES</a></h2>'
        + child
        + "</div>"
    )
    events = extract_rockhouse_events(html, TODAY)
    assert [(e.title, e.start_date) for e in events] == [("MIKE CRONIN", "2026-10-15T19:30:00")]


def test_funny_bone_colon_times_price_and_duplicate_cards_remain_supported():
    html = series("MIKE CRONIN", "mike-cronin", [("Oct 15", "Doors: 5:30 pm // Show: 7 pm", MIKE)])
    html = html.replace("<ul>", '<span class="rhp-event__cost-text--list">$26 - $31</span><ul>')
    events = extract_rockhouse_events(html + html, TODAY)
    assert len(events) == 1
    assert events[0].start_date == "2026-10-15T19:00:00"
    assert events[0].ticket_price == 26


def test_conflict_diagnostics_expose_rejected_ids_without_losing_safe_rows():
    from laughtrack.scrapers.implementations.api.etix.rockhouse import extract_rockhouse_events_with_conflicts

    html = series("CAM ROWE", "cam-rowe", [("Oct 15", "Show | 7:30 pm", MIKE)])
    html += series("MIKE CRONIN", "mike-cronin", [("Oct 15", "Show | 7:30 pm", MIKE)])
    html += series(
        "THE NIGHT BEFORE THANKSGIVING SPECIAL",
        "the-night-before-thanksgiving-special",
        [("Nov 25", "Show | 7:30 pm", THANKSGIVING)],
    )
    events, conflicts = extract_rockhouse_events_with_conflicts(html, TODAY)
    assert [e.title for e in events] == ["THE NIGHT BEFORE THANKSGIVING SPECIAL"]
    assert set(conflicts) == {"62115951"}
    assert {row["title"] for row in conflicts["62115951"]} == {"CAM ROWE", "MIKE CRONIN"}
    assert all(row["ticket_url"] == MIKE for row in conflicts["62115951"])


def test_same_ticket_with_conflicting_dates_is_not_assigned_either_date():
    html = series(
        "MIKE CRONIN", "mike-cronin", [("Oct 15", "Show | 7:30 pm", MIKE), ("Oct 16", "Show | 7:30 pm", MIKE)]
    )
    assert extract_rockhouse_events(html, TODAY) == []


@pytest.mark.parametrize(
    "price,expected",
    [
        ("$0 to $29", None),
        ("$-5 to $29", None),
        ("$-5 to $0", None),
        ("$0 - $29", None),
        ("$29 to $0", None),
        ("$0 to 29", None),
        ("$0.00–$29.00", None),
        ("$26 to $31", 26),
        ("$31 - $26", 26),
        ("Free", 0),
        ("$0", 0),
        ("$0 to $0", 0),
    ],
)
def test_zero_to_paid_range_does_not_claim_general_admission_is_free(price, expected):
    # Raue official cost elements include '$0 to $29' for tiered ticket types.
    html = series("Lucy Comedy", "lucy-comedy", [("Oct 15", "Show | 7 pm", MIKE)])
    html = html.replace("<ul>", f'<span class="rhp-event__cost-text--list">{price}</span><ul>')
    assert extract_rockhouse_events(html, TODAY)[0].ticket_price == expected


@pytest.mark.parametrize("bad_time", ["Doors: 7 pm", "", "Show | 13 pm"])
def test_partial_unparsed_card_reports_omission_for_cleanup_safety(bad_time):
    from laughtrack.scrapers.implementations.api.etix.rockhouse import extract_rockhouse_events_with_conflicts

    html = series("MIKE CRONIN", "mike-cronin", [("Oct 15", bad_time, MIKE)])
    html += series("THANKSGIVING SPECIAL", "thanksgiving", [("Nov 25", "Show | 7:30 pm", THANKSGIVING)])
    events, issues = extract_rockhouse_events_with_conflicts(html, TODAY)
    assert [e.title for e in events] == ["THANKSGIVING SPECIAL"]
    assert set(issues) == {"unparsed:62115951"}
    assert issues["unparsed:62115951"][0]["ticket_url"] == MIKE


def test_valid_duplicate_card_representation_prevents_false_omission():
    from laughtrack.scrapers.implementations.api.etix.rockhouse import extract_rockhouse_events_with_conflicts

    missing = series("MIKE CRONIN", "mike-cronin", [("Oct 15", "Doors: 7 pm", MIKE)])
    valid = series("MIKE CRONIN", "mike-cronin", [("Oct 15", "Show | 7:30 pm", MIKE)])
    for html in (missing + valid, valid + missing):
        events, issues = extract_rockhouse_events_with_conflicts(html, TODAY)
        assert len(events) == 1
        assert issues == {}


def test_invalid_other_title_is_not_mistaken_for_duplicate_representation():
    from laughtrack.scrapers.implementations.api.etix.rockhouse import extract_rockhouse_events_with_conflicts

    html = series("CAM ROWE", "cam-rowe", [("Oct 15", "Doors: 7 pm", MIKE)])
    html += series("MIKE CRONIN", "mike-cronin", [("Oct 15", "Show | 7:30 pm", MIKE)])
    events, issues = extract_rockhouse_events_with_conflicts(html, TODAY)
    assert len(events) == 1
    assert set(issues) == {"unparsed:62115951"}
