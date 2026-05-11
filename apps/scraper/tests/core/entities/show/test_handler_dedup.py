from datetime import datetime
from unittest.mock import MagicMock

from laughtrack.core.entities.show.handler import ShowHandler
from laughtrack.core.entities.show.model import Show


def _handler():
    h = ShowHandler.__new__(ShowHandler)
    h.ticket_handler = MagicMock()
    h.tag_handler = MagicMock()
    h.lineup_handler = MagicMock()
    h.comedian_handler = MagicMock()
    h.execute_batch_operation = MagicMock(
        return_value=[
            {
                "id": 10,
                "club_id": 1,
                "date": datetime(2026, 6, 1, 20, 0, 0),
                "room": "",
                "operation_type": "updated",
            }
        ]
    )
    h.ticket_handler.insert_tickets.return_value = None
    h.tag_handler.process_show_tags.return_value = None
    h.update_show_lineups = MagicMock(return_value=(0, 0))
    return h


def _show(name="Same Show", room="", url="https://example.com/show"):
    return Show(
        name=name,
        club_id=1,
        date=datetime(2026, 6, 1, 20, 0, 0),
        show_page_url=url,
        room=room,
    )


def test_insert_shows_dedups_cross_batch():
    h = _handler()
    h.execute_with_cursor = MagicMock(
        return_value=[
            {
                "id": 10,
                "club_id": 1,
                "date": datetime(2026, 6, 1, 20, 0, 0),
                "room": "",
                "name": "Same Show",
            }
        ]
    )

    result = h._process_single_batch([_show(room="Main Room")])

    inserted_items = h.execute_batch_operation.call_args.args[1]
    assert len(inserted_items) == 1
    assert inserted_items[0][6] == ""
    assert result.updates == 1


def test_insert_shows_preserves_distinct_rooms():
    h = _handler()
    h.execute_with_cursor = MagicMock(
        return_value=[
            {
                "id": 10,
                "club_id": 1,
                "date": datetime(2026, 6, 1, 20, 0, 0),
                "room": "Main Room",
                "name": "Same Show",
            }
        ]
    )

    h._process_single_batch([_show(room="Side Room")])

    inserted_items = h.execute_batch_operation.call_args.args[1]
    assert len(inserted_items) == 1
    assert inserted_items[0][6] == "Side Room"
