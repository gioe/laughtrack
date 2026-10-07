"""ThunderTix physical-key collisions must not overwrite distinct performances."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from laughtrack.core.entities.show.handler import ShowHandler
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.models.operation_result import DatabaseOperationResult


def _show(performance, *, club=183, hour=20, room="", producer=None):
    return Show(
        name="Recurring title",
        club_id=club,
        date=datetime.now(timezone.utc).replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=10),
        room=room,
        show_page_url="https://venue.thundertix.com/events/100",
        tickets=[
            Ticket(
                price=None,
                purchase_url=f"https://venue.thundertix.com/orders/new?event_id=100&performance_id={performance}",
            )
        ],
        last_scraped_by=producer,
        source_performance_id=f"thundertix:venue:100:{performance}",
    )


def _handler():
    handler = ShowHandler.__new__(ShowHandler)
    handler._process_single_batch = MagicMock(return_value=DatabaseOperationResult())
    return handler


@pytest.mark.parametrize("batch_size", [1, 100])
def test_distinct_performances_are_retained_across_batches(batch_size):
    handler = _handler()
    safe = _show(3, hour=21)
    result = handler.insert_shows([_show(1), safe, _show(2)], batch_size=batch_size, scraper_key="thundertix")
    assert result.validation_errors == 0
    retained = [show for call in handler._process_single_batch.call_args_list for show in call.args[0]]
    assert len(retained) == 3
    assert safe in retained


def test_exact_repeated_performance_is_not_a_conflict():
    handler = _handler()
    shows = [_show(1), _show(1)]
    result = handler.insert_shows(shows, scraper_key="thundertix")
    assert result.validation_errors == 0
    assert handler._process_single_batch.call_args.args[0] == shows


@pytest.mark.parametrize("different", [{"club": 9}, {"hour": 21}, {"room": "Small Theater"}])
def test_different_physical_key_is_not_rejected(different):
    handler = _handler()
    result = handler.insert_shows([_show(1), _show(2, **different)], scraper_key="thundertix")
    assert result.validation_errors == 0
    assert len(handler._process_single_batch.call_args.args[0]) == 2


def test_other_scrapers_are_unchanged():
    handler = _handler()
    result = handler.insert_shows([_show(1), _show(2)], scraper_key="other")
    assert result.validation_errors == 0
    assert len(handler._process_single_batch.call_args.args[0]) == 2


def test_collision_blocks_stale_cleanup():
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    handler = _handler()
    processor = ScrapingResultProcessor.__new__(ScrapingResultProcessor)
    processor.show_service = handler
    processor._reconcile_stale_future_shows = MagicMock()
    club_result = SimpleNamespace(
        shows=[_show(1), _show(1, hour=21)], is_synthetic=False, club_name="Venue", scraper_key="thundertix",
        cancellations=[],
    )
    result = processor.insert_club_result(club_result)
    assert result.validation_errors == 2
    handler._process_single_batch.assert_not_called()
    processor._reconcile_stale_future_shows.assert_not_called()


def test_direct_batch_rejects_before_dedup_or_database_write():
    handler = ShowHandler.__new__(ShowHandler)
    handler._classify_missing_show_types = MagicMock()
    handler._suppress_room_matching_club_name = MagicMock()
    handler.execute_batch_operation = MagicMock()
    result = handler._process_single_batch([_show(1, producer="thundertix"), _show(1, hour=21, producer="thundertix")])
    assert result.validation_errors == 2
    handler.execute_batch_operation.assert_not_called()


def test_annoyance_shaped_cohort_retains_all_280_across_batches():
    handler = _handler()
    safe = [_show(i + 1, club=1000 + i) for i in range(200)]
    first = [_show(1000 + i, club=2000 + i) for i in range(40)]
    second = [_show(2000 + i, club=2000 + i) for i in range(40)]
    result = handler.insert_shows(first + safe + second, batch_size=100, scraper_key="thundertix")
    assert result.validation_errors == 0
    retained = [show for call in handler._process_single_batch.call_args_list for show in call.args[0]]
    assert retained == first + safe + second


def test_ticket_query_order_does_not_create_false_identity_conflict():
    handler = _handler()
    shows = [_show(1), _show(1)]
    shows[1].tickets[
        0
    ].purchase_url = "https://venue.thundertix.com/orders/new?performance_id=1&event_id=100&utm_source=test"
    result = handler.insert_shows(shows, scraper_key="thundertix")
    assert result.validation_errors == 0


def test_native_source_identity_keeps_simultaneous_performances():
    first, second = _show(1), _show(2)
    first.source_performance_id = "thundertix:venue:100:1"
    second.source_performance_id = "thundertix:venue:100:2"
    assert first.to_unique_key() != second.to_unique_key()


@pytest.mark.parametrize("identity", ["", "thundertix:venue:100:0", "garbage"])
def test_missing_or_malformed_identity_is_not_adopted_by_slot(identity):
    handler = _handler()
    show = _show(1)
    show.source_performance_id = identity
    result = handler.insert_shows([show], scraper_key="thundertix")
    assert result.validation_errors == 1
    handler._process_single_batch.assert_not_called()


def test_same_identity_contradictory_times_rejected_across_batch_boundaries():
    handler = _handler()
    result = handler.insert_shows([_show(1), _show(2), _show(1, hour=21)], batch_size=1, scraper_key="thundertix")
    assert result.validation_errors == 2
    assert handler._process_single_batch.call_count == 1
    assert handler._process_single_batch.call_args.args[0][0].source_performance_id.endswith(":2")


def test_unactivated_thundertix_retains_legacy_collision_protection():
    handler = _handler()
    shows = [_show(1), _show(2), _show(3, hour=21)]
    for show in shows:
        show.source_performance_id = None
    result = handler.insert_shows(shows, scraper_key="thundertix")
    assert result.validation_errors == 2
    assert handler._process_single_batch.call_args.args[0] == [shows[2]]
