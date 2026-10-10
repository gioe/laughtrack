"""Eligibility staging and public write boundary contracts."""


def test_contract_1(monkeypatch):
    from laughtrack.core import comedy_eligibility_store as store

    source = {
        "comedy_policy": "unreviewed",
        "id": 7,
        "enabled": True,
        "comedy_policy_version": 2,
        "comedy_gate_mode": "enforce",
    }
    monkeypatch.setattr(store, "load_source", lambda *args, **kwargs: source)
    rows = iter(
        [{"id": 10, "observation_generation": 1}, {"id": 20}, {"id": 10, "observation_generation": 2}, None, {"id": 20}]
    )
    monkeypatch.setattr(store, "_row", lambda cursor: next(rows))

    class Cursor:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params):
            self.calls.append((sql, params))

    cursor = Cursor()
    kwargs = dict(
        source_id=7,
        event_key="native:event-1",
        club_id=42,
        payload={"title": "Stand-up comedy", "performers": ["Raw Name"]},
        decision={
            "policy": "unreviewed",
            "source_id": 7,
            "policy_version": 2,
            "classifier_version": "v1",
            "decision": "review",
            "performers": [],
            "reason_codes": ["unknown"],
        },
        gate_mode="enforce",
    )
    first = store.stage_candidate(cursor, **kwargs)
    retry = store.stage_candidate(cursor, **kwargs)
    assert first.id == retry.id and first.decision_id == retry.decision_id
    assert first.observation_generation == 1 and retry.observation_generation == 2
    assert first.id == 10 and first.decision_id == 20 and first.source_id == 7
    assert first.policy_version == 2
    insert_calls = [params for sql, params in cursor.calls if sql == store.INSERT_DECISION_SQL]
    assert insert_calls[0] == insert_calls[1]
    assert "Raw Name" in insert_calls[0][-2] and "unknown" in insert_calls[0][-1]
    assert store.fingerprint({"a": 1, "b": 2}) == store.fingerprint({"b": 2, "a": 1})
    assert store.fingerprint({"a": 1}) != store.fingerprint({"a": 2})


# Runtime tests use the real classifier and handler dispatch with a transactional
# in-memory staging double. SQL idempotence and stale-generation fencing are separately exercised
# by the PGlite migration suite using the actual store SQL.
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock


def _gate_environment(monkeypatch, mode="enforce"):
    from laughtrack.core import comedy_eligibility_gate as gate
    from laughtrack.core.comedy_eligibility_store import StagedCandidate

    state = SimpleNamespace(
        source={
            "id": 7,
            "enabled": True,
            "comedy_policy": "unreviewed",
            "comedy_gate_mode": mode,
            "comedy_policy_version": 1,
        },
        staged=[],
        publications=[],
        active=0,
        calls=[],
        loads=0,
        fail_stage=False,
        fail_fence=False,
        after_stage=None,
        generation=0,
    )

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, sql, params=None):
            state.calls.append((sql, params))

        def fetchall(self):
            return [(7,)]

    class Connection:
        def cursor(self):
            return Cursor()

        def rollback(self):
            state.calls.append(("rollback", None))

    @contextmanager
    def transaction():
        state.active += 1
        try:
            yield Connection()
        finally:
            state.active -= 1

    def load(cursor, sid, lock=False):
        state.loads = getattr(state, "loads", 0) + 1
        if state.fail_fence and state.staged:
            raise RuntimeError("source unavailable")
        return dict(state.source) if sid == 7 else None

    def stage(cursor, **kwargs):
        if state.fail_stage:
            if state.after_stage:
                state.after_stage()
            raise RuntimeError("staging unavailable")
        state.generation += 1
        state.staged.append(kwargs)
        if state.after_stage:
            state.after_stage()
        return StagedCandidate(
            10, len(state.staged), 7, kwargs["event_key"], kwargs["decision"].policy_version, mode, state.generation
        )

    def verify(cursor, candidate):
        return (
            state.source["enabled"]
            and state.source["comedy_gate_mode"] == candidate.gate_mode
            and state.source["comedy_policy_version"] == candidate.policy_version
            and candidate.observation_generation == state.generation
        )

    monkeypatch.setattr(gate, "load_source", load)
    monkeypatch.setattr(gate, "stage_candidate", stage)
    monkeypatch.setattr(gate, "verify_publication", verify)
    monkeypatch.setattr(
        gate, "link_published", lambda c, s, show_id: state.publications.append((s.source_id, s.event_key, show_id))
    )
    monkeypatch.setattr(gate, "_identity_snapshot", lambda c, n: ([], []))
    state.transaction = transaction
    return state


def _gate_show(name="Stand-up comedy showcase", **kwargs):
    from laughtrack.core.entities.show.model import Show

    return Show(
        name=name,
        club_id=42,
        date=datetime(2099, 1, 1, 20, tzinfo=timezone.utc),
        show_page_url="https://example.org/events/one",
        eligibility_source_id=7,
        last_scraped_by="test",
        **kwargs,
    )


def _writer_handler(monkeypatch, state):
    from laughtrack.core.entities.show.handler import ShowHandler
    from laughtrack.core.entities.show.handler import ShowValidator
    from laughtrack.foundation.models.operation_result import DatabaseOperationResult

    handler = ShowHandler.__new__(ShowHandler)
    handler.transaction = state.transaction
    state.public = {}
    handler._classify_missing_show_types = lambda shows: None
    monkeypatch.setattr(ShowValidator, "validate_shows", lambda shows: (shows, []))
    handler._suppress_room_matching_club_name = lambda shows: None
    handler._reject_thundertix_collisions = lambda shows: (shows, 0)
    handler._fullcalendar_input_conflicts = lambda shows: (set(), set())
    handler._reconcile_patronticket_instances = lambda shows: None
    handler._reconcile_seatengine_classic_show_urls = lambda shows: None
    handler._collapse_cross_batch_duplicates = lambda shows: None

    def persist(shows, **kwargs):
        assert state.active > 0  # Publication fence remains open through public writes.
        for show in shows:
            state.public.setdefault(show.to_unique_key(), len(state.public) + 1)
        return [
            {
                "id": state.public[s.to_unique_key()],
                "club_id": s.club_id,
                "date": s.date,
                "room": s.room,
                "operation_type": "inserted",
            }
            for s in shows
        ]

    handler._persist_show_partitions = MagicMock(side_effect=persist)

    def related(shows, rows):
        for show, row in zip(shows, rows):
            show.id = row["id"]
            show.operation_type = row["operation_type"]
            show.eligibility_persisted = True
        return shows, len(shows), len(shows)

    handler._update_shows_and_related = MagicMock(side_effect=related)
    return handler


def test_contract_2(monkeypatch):
    from laughtrack.core import comedy_eligibility_gate as gate
    from laughtrack.core.entities.show.service import ShowService

    state = _gate_environment(monkeypatch)
    handler = _writer_handler(monkeypatch, state)
    rejected = _gate_show("Live music", id=99)
    reviewed = _gate_show("Unclear event", id=100)
    result = handler.insert_shows([rejected, reviewed])
    assert result.eligibility_withheld == 2 and not result.reconciliation_safe
    handler._persist_show_partitions.assert_not_called()
    handler._update_shows_and_related.assert_not_called()
    assert len(state.staged) == 2 and not state.publications
    accepted = _gate_show()
    service = ShowService.__new__(ShowService)
    service.show_handler = handler
    assert service.insert_shows([accepted]).total == 1
    assert handler.insert_shows([_gate_show()]).total == 1
    assert len(state.public) == 1 and state.publications
    # Disabled source and direct lineup-only entry cannot bypass admission.
    state.source["enabled"] = False
    handler._update_screened_show_lineups = MagicMock(return_value=(0, 0))
    assert handler.update_show_lineups([_gate_show()]) == (0, 0)
    assert handler._update_screened_show_lineups.call_args.args[0] == []
    state.source["enabled"] = True
    # Existing IDs on filtered inputs must not be mistaken for publication.
    monkeypatch.setattr(
        "laughtrack.core.entities.show.handler.ShowValidator.validate_shows", lambda s: ([], ["invalid"])
    )
    before = len(state.publications)
    handler.insert_shows([_gate_show(id=999)])
    assert len(state.publications) == before
    # Source-ID propagation used by standard and early national writes.
    source = SimpleNamespace(id=7, comedy_policy=SimpleNamespace(gate_mode="enforce"))
    unstamped = _gate_show()
    unstamped.eligibility_source_id = None
    gate.stamp_source([unstamped], source)
    assert unstamped.eligibility_source_id == 7


def test_contract_3(monkeypatch):
    from laughtrack.core import comedy_eligibility_gate as gate
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor
    from laughtrack.core.models.results import ClubScrapingResult
    from laughtrack.foundation.models.operation_result import DatabaseOperationResult

    state = _gate_environment(monkeypatch, "shadow")
    handler = _writer_handler(monkeypatch, state)
    assert handler.insert_shows([_gate_show("Live music")]).total == 1
    assert state.staged[0]["decision"].decision == "reject"
    state.fail_stage = True
    result = handler.insert_shows([_gate_show("Unknown")])
    assert result.total == 1 and not result.reconciliation_safe
    state.after_stage = lambda: state.source.update(comedy_gate_mode="enforce", comedy_policy_version=2)
    result = handler.insert_shows([_gate_show("Unknown")])
    assert result.total == 0 and result.eligibility_withheld == 1
    proc = ScrapingResultProcessor.__new__(ScrapingResultProcessor)
    proc.show_service = MagicMock()
    proc.show_service.insert_shows.return_value = DatabaseOperationResult(
        eligibility_withheld=1, reconciliation_safe=False
    )
    proc._reconcile_stale_future_shows = MagicMock()
    proc.insert_club_result(ClubScrapingResult("Test", [_gate_show()], 1, club_id=42, scraper_key="test"))
    proc._reconcile_stale_future_shows.assert_not_called()
    # Empty gated inventories and multiply-owned venues inhibit deletion too.
    state.source.update(comedy_gate_mode="enforce", enabled=True)
    result = ClubScrapingResult("Test", [], 1, club_id=42, scraper_key="test", eligibility_source_id=7)
    assert not gate.safe_to_reconcile(handler, result)
    state.source["comedy_gate_mode"] = "off"
    cursor = MagicMock()
    cursor.fetchone.side_effect = [(2,)]

    @contextmanager
    def tx():
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        yield conn

    handler.transaction = tx
    assert not gate.safe_to_reconcile(handler, result)
    cursor.fetchone.side_effect = [(1,), ("comedy_event_publications",), (True,)]
    assert not gate.safe_to_reconcile(handler, result)


def test_contract_4(monkeypatch):
    import asyncio
    from laughtrack.core import comedy_eligibility_gate as gate
    from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

    state = _gate_environment(monkeypatch)
    handler = _writer_handler(monkeypatch, state)

    async def delivery():
        return handler.insert_shows([_gate_show()]).total

    assert asyncio.run(delivery()) == 1
    assert asyncio.run(delivery()) == 1
    assert len(state.public) == 1 and state.active == 0
    state.after_stage = lambda: state.source.update(comedy_policy_version=2)
    result = handler.insert_shows([_gate_show()])
    assert result.total == 0 and not result.reconciliation_safe
    one = _gate_show()
    two = _gate_show()
    two.date = one.date.astimezone(timezone(timedelta(hours=-4)))
    two.show_page_url += "?token=secret&utm_source=mail"
    assert gate.event_key(one) == gate.event_key(two)
    assert "secret" not in str(gate.candidate_payload(two))
    assert (
        gate.safe_url("https://user:password@example.org/x?event_id=123&api_key=secret")
        == "https://example.org/x?event_id=123"
    )
    raw = ShowFactoryUtils.create_lineup_from_performers(["Open Mic", "Actual Person"])
    show = _gate_show(lineup=raw)
    assert "Open Mic" in show.eligibility_performer_names
    assert "Open Mic" not in [p.name for p in show.lineup]


def test_off_batch_queries_once_per_source(monkeypatch):
    from laughtrack.core.comedy_eligibility_gate import EligibilityGate

    state = _gate_environment(monkeypatch, "off")
    with EligibilityGate(state.transaction).screen([_gate_show() for _ in range(100)]) as screened:
        assert len(screened.shows) == 100
    assert state.loads == 2  # Initial snapshot and publication fence.
    assert not state.staged


def test_failed_public_write_preserves_staged_decision(monkeypatch):
    state = _gate_environment(monkeypatch)
    handler = _writer_handler(monkeypatch, state)
    handler._persist_show_partitions.side_effect = RuntimeError("write unavailable")
    result = handler.insert_shows([_gate_show(id=991)])
    assert result.errors == 1 and len(state.staged) == 1
    assert not state.publications and state.active == 0


def test_early_national_writer_stamps_and_screens(monkeypatch):
    import asyncio
    from laughtrack.core.entities.show.service import ShowService
    from laughtrack.scrapers.implementations.api.ticketmaster_national.scraper import TicketmasterNationalScraper

    state = _gate_environment(monkeypatch)
    handler = _writer_handler(monkeypatch, state)
    service = ShowService.__new__(ShowService)
    service.show_handler = handler
    monkeypatch.setattr("laughtrack.core.entities.show.service.ShowService", lambda: service)
    scraper = TicketmasterNationalScraper.__new__(TicketmasterNationalScraper)
    scraper._club = SimpleNamespace(
        name="National",
        active_scraping_source=SimpleNamespace(id=7, comedy_policy=SimpleNamespace(gate_mode="enforce")),
    )
    scraper.logger_context = {}
    show = _gate_show("Live music")
    show.eligibility_source_id = None
    assert asyncio.run(scraper._persist_in_chunks([show])) == 0
    assert show.eligibility_source_id == 7 and len(state.staged) == 1
    handler._persist_show_partitions.assert_not_called()


def test_event_identity_retains_instance_fragment_and_utc_naive():
    from laughtrack.core.comedy_eligibility_gate import event_key

    first = _gate_show()
    second = _gate_show()
    first.show_page_url += "#/instances/1"
    second.show_page_url += "#/instances/2"
    assert event_key(first) != event_key(second)
    second.show_page_url = first.show_page_url
    second.date = first.date.replace(tzinfo=None)
    assert event_key(first) == event_key(second)


def test_adapter_malformed_metadata_does_not_drop_off_events(monkeypatch):
    from laughtrack.core import comedy_eligibility_gate as gate

    state = _gate_environment(monkeypatch, "off")
    for raw in (
        {"classifications": None, "_embedded": None},
        {"classifications": [None, {"genre": None, "segment": {"name": None}}]},
        {"classifications": "comedy", "performers": [None, {}, "Real Name"]},
    ):
        show = _gate_show()
        gate.capture_event_inputs(show, raw)
        with gate.EligibilityGate(state.transaction).screen([show]) as screened:
            assert screened.shows == [show]


def test_explicit_cancellations_obey_current_source_and_ownership_guard(monkeypatch):
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor
    from laughtrack.core.models.results import ClubScrapingResult
    from laughtrack.foundation.models.operation_result import DatabaseOperationResult

    state = _gate_environment(monkeypatch, "shadow")
    handler = _writer_handler(monkeypatch, state)
    handler.apply_cancellations = MagicMock(return_value=[1])
    processor = ScrapingResultProcessor.__new__(ScrapingResultProcessor)
    processor.show_service = MagicMock()
    processor.show_service.show_handler = handler
    processor.show_service.insert_shows.return_value = DatabaseOperationResult(total=1)
    processor._reconcile_stale_future_shows = MagicMock()
    result = ClubScrapingResult(
        "Test",
        [_gate_show()],
        1,
        club_id=42,
        scraper_key="test",
        eligibility_source_id=7,
        cancellations=[SimpleNamespace(scraper_key="test", production_company_id=None)],
    )
    processor.insert_club_result(result)
    handler.apply_cancellations.assert_not_called()

    # An off-mode sibling is also prohibited from cancelling multiply-owned rows.
    state.source["comedy_gate_mode"] = "off"
    cursor = MagicMock()
    cursor.fetchone.return_value = (2,)

    @contextmanager
    def transaction():
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        yield connection

    handler.transaction = transaction
    processor.insert_club_result(result)
    handler.apply_cancellations.assert_not_called()
