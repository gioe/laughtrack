from datetime import datetime, timezone

from laughtrack.core.entities.show.model import Show
from sql.show_queries import ShowQueries


def _show() -> Show:
    return Show(
        name="Test Show",
        club_id=42,
        date=datetime(2026, 4, 15, 20, 0, 0, tzinfo=timezone.utc),
        show_page_url="https://example.com/show",
        room="Main Room",
    )


def test_show_from_db_row_reads_show_type():
    show = Show.from_db_row(
        {
            "id": 77,
            "name": "Test Show",
            "show_page_url": "https://example.com/show",
            "description": "",
            "date": datetime(2026, 4, 15, 20, 0, 0, tzinfo=timezone.utc),
            "club_id": 42,
            "room": "Main Room",
            "show_type": "standup",
        }
    )

    assert show.show_type == "standup"


def test_to_tuple_emits_show_type_after_scraped_by_organizer_id():
    show = _show()
    show.show_type = "improv"

    assert show.to_tuple()[10] == "improv"


def test_batch_insert_show_writes_and_updates_show_type():
    insert_columns = ShowQueries.BATCH_INSERT_SHOWS.split("VALUES", maxsplit=1)[0]
    conflict_update = ShowQueries.BATCH_INSERT_SHOWS.split("DO UPDATE SET", maxsplit=1)[1].split(
        "RETURNING", maxsplit=1
    )[0]

    assert "show_type" in insert_columns
    assert "show_type = EXCLUDED.show_type" in conflict_update


def test_get_show_details_selects_show_type():
    select_clause = ShowQueries.GET_SHOW_DETAILS.split("FROM shows", maxsplit=1)[0]

    assert "show_type" in select_clause
