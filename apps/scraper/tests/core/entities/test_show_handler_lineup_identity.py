"""Regression coverage for event-title values at the shared lineup boundary."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.handler import ShowHandler


def _show(show_id: int, title: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=show_id,
        name=title,
        club_id=42,
        lineup=[Comedian(title)],
    )


def _handler(title_matches) -> ShowHandler:
    handler = ShowHandler.__new__(ShowHandler)
    handler.ticket_handler = MagicMock()
    handler.tag_handler = MagicMock()
    handler.lineup_handler = MagicMock()
    handler.comedian_handler = MagicMock()
    handler.lineup_handler.get_lineup.return_value = {}
    handler.lineup_handler.get_comedians_from_show_names.return_value = title_matches
    handler.lineup_handler.batch_update_lineups.return_value = (1, 0)
    handler.comedian_handler._filter_denied_comedians.side_effect = list
    handler.comedian_handler._filter_false_positive_comedians.side_effect = list
    handler.comedian_handler.insert_comedians.return_value = []
    handler.calculate_and_update_popularity = MagicMock()
    return handler


def test_existing_canonical_replaces_decorated_title_without_inventing_unknown_identity():
    carie_title = "CARIE KARAVAS - SATURDAY, 9/5 @ 7:00PM"
    unknown_title = "UNKNOWN FEATURE - SATURDAY, 9/5 @ 9:00PM"
    canonical_carie = Comedian(
        name="Carie Karavas",
        uuid="8643d3c3e078bef376480f7cda95925b",
    )
    polluted_carie = Comedian(name=carie_title)
    polluted_unknown = Comedian(name=unknown_title)
    carie_show = _show(1, carie_title)
    unknown_show = _show(2, unknown_title)
    handler = _handler(
        {
            carie_title: [canonical_carie, polluted_carie],
            unknown_title: [polluted_unknown],
        }
    )

    handler.update_show_lineups([carie_show, unknown_show])

    assert [(comedian.name, comedian.uuid) for comedian in carie_show.lineup] == [
        ("Carie Karavas", "8643d3c3e078bef376480f7cda95925b")
    ]
    assert unknown_show.lineup == []
    inserted = handler.comedian_handler.insert_comedians.call_args.args[0]
    assert [(comedian.name, comedian.uuid) for comedian in inserted] == [
        ("Carie Karavas", "8643d3c3e078bef376480f7cda95925b")
    ]
    persisted_shows = handler.lineup_handler.batch_update_lineups.call_args.args[0]
    assert persisted_shows == [carie_show, unknown_show]
