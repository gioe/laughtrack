"""Regression coverage for event-title values at the shared lineup boundary."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

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


@pytest.mark.parametrize("source_name", [
    "Steve Marshall Comedy", "STEVE MARSHALL COMEDY", "Steve Marshall Comedy Special",
    "Steve Marshall LIVE at Snappers",
])
@pytest.mark.parametrize("title_is_source", [True, False])
def test_decorated_source_resolves_before_both_persistence_steps(source_name, title_is_source):
    canonical = Comedian("Steve Marshall", uuid="existing-steve")
    show = _show(1, source_name if title_is_source else "Thursday Headliners")
    show.lineup = [Comedian(source_name)]
    handler = _handler({source_name: [canonical]})

    handler.update_show_lineups([show])

    assert show.lineup == [canonical]
    inserted = handler.comedian_handler.insert_comedians.call_args.args[0]
    assert [(c.name, c.uuid) for c in inserted] == [("Steve Marshall", "existing-steve")]
    persisted = handler.lineup_handler.batch_update_lineups.call_args.args[0]
    assert persisted[0].lineup == [canonical]
    queried = handler.lineup_handler.get_comedians_from_show_names.call_args.args[0]
    assert (source_name,) in queried


def test_historical_decorated_identity_from_title_matching_is_collapsed():
    canonical = Comedian("Steve Marshall", uuid="existing-steve")
    polluted = Comedian("Steve Marshall Comedy", uuid="historical-duplicate")
    show = _show(1, "Steve Marshall Comedy at Snappers")
    show.lineup = []
    handler = _handler({show.name: [canonical, polluted]})
    handler.update_show_lineups([show])
    assert show.lineup == [canonical]
    assert handler.comedian_handler.insert_comedians.call_args.args[0] == [canonical]


@pytest.mark.parametrize("source_name, known_name", [
    ("Chris Rock Jr.", "Chris Rock"),
    ("Chris Rockwell Comedy", "Chris Rock"),
    ("Chris Rock Jr. Comedy", "Chris Rock"),
    ("Steve Marshall and Jane Smith", "Steve Marshall"),
    ("Steve Marshall & Jane Smith Comedy", "Steve Marshall"),
])
def test_containment_without_unambiguous_decoration_does_not_replace(source_name, known_name):
    source = Comedian(source_name, uuid="source-person")
    show = _show(1, "Thursday Headliners")
    show.lineup = [source]
    handler = _handler({})
    handler._reconcile_decorated_lineup_entries(
        [show], {source_name: [Comedian(known_name, uuid="different-person")]}
    )
    assert show.lineup == [source]


def test_ambiguous_known_identities_do_not_choose_arbitrary_parent():
    show = _show(1, "Steve Marshall Comedy")
    source = show.lineup[0]
    handler = _handler({})
    handler._reconcile_decorated_lineup_entries([show], {show.name: [
        Comedian("Steve Marshall", uuid="steve-one"),
        Comedian("Steve Marshall", uuid="steve-two"),
    ]})
    assert show.lineup == [source]


def test_unknown_decorated_performer_is_not_replaced_by_guessed_identity():
    show = _show(1, "Unknown Person Comedy")
    source = show.lineup[0]
    handler = _handler({})
    handler._reconcile_decorated_lineup_entries([show], {})
    assert show.lineup == [source]


def test_multiple_real_performers_survive_and_repeated_canonical_is_deduplicated():
    steve = Comedian("Steve Marshall", uuid="steve")
    jane = Comedian("Jane Smith", uuid="jane")
    show = _show(1, "Thursday Headliners")
    show.lineup = [Comedian("Steve Marshall Comedy"), jane, steve]
    handler = _handler({"Steve Marshall Comedy": [steve]})
    handler.update_show_lineups([show])
    assert show.lineup == [steve, jane]


def test_disabled_title_inference_still_reconciles_only_supplied_performers():
    steve = Comedian("Steve Marshall", uuid="steve")
    unrelated = Comedian("Jane Smith", uuid="jane")
    show = _show(1, "Jane Smith")
    show.infer_lineup_from_title = False
    show.lineup = [Comedian("Steve Marshall Comedy")]
    handler = _handler({show.name: [unrelated], "Steve Marshall Comedy": [steve]})
    handler.update_show_lineups([show])
    assert show.lineup == [steve]


def test_disabled_title_inference_keeps_empty_lineup_empty():
    show = _show(1, "Steve Marshall Comedy")
    show.infer_lineup_from_title = False
    show.lineup = []
    handler = _handler({show.name: [Comedian("Steve Marshall", uuid="steve")]})
    handler.update_show_lineups([show])
    assert show.lineup == []
