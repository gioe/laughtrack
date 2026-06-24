from laughtrack.scrapers.implementations.venues.lesher_center.extractor import (
    LesherCenterExtractor,
)


def test_extract_events_filters_comedy_genre_and_expands_instances():
    payload = [
        {
            "name": "Best of San Francisco Stand-Up Comedy (SEP 2026)",
            "description": "Bay Area stand-up comedy.",
            "duration": 75,
            "id": "82201ALMMGMRMBVSDRJDMGQHDVSMGGKDG",
            "webEventId": "FMM-32627",
            "attribute_Genre": "Comedy and Improv",
            "attribute_Presenter": "Force Majeure Media LLC",
            "availableInstanceDates": [
                "2026-09-05T20:15:00",
                "2026-09-19T20:15:00",
                "2026-09-26T20:15:00",
            ],
            "isSoldOut": False,
        },
        {
            "name": "Music from the Shadows",
            "id": "83601ARJRQHJPSDPRNGGRVVHTJHNRMKRC",
            "webEventId": "WCB-12627",
            "attribute_Genre": "Music",
            "availableInstanceDates": ["2026-10-13T19:00:00"],
        },
    ]

    events = LesherCenterExtractor.extract_events(payload)

    assert [event.date_time.isoformat() for event in events] == [
        "2026-09-05T20:15:00",
        "2026-09-19T20:15:00",
        "2026-09-26T20:15:00",
    ]
    assert {event.title for event in events} == {"Best of San Francisco Stand-Up Comedy (SEP 2026)"}
    assert all(event.genre == "Comedy and Improv" for event in events)


def test_extract_events_skips_malformed_items():
    payload = [
        "not an object",
        {"name": "Comedy without dates", "attribute_Genre": "Comedy and Improv"},
        {
            "name": "Comedy with bad date",
            "id": "bad-date",
            "attribute_Genre": "Comedy and Improv",
            "availableInstanceDates": ["not-a-date"],
        },
    ]

    assert LesherCenterExtractor.extract_events(payload) == []
