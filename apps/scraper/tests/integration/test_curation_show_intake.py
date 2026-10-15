"""Real cross-language show admission contracts on embedded PostgreSQL."""
from pathlib import Path
import subprocess


def test_durable_show_intake_contract():
    web = Path(__file__).resolve().parents[3] / "web"
    result = subprocess.run(["npm", "test", "--", "lib/admin/curation/showIntake.test.ts"],
                            cwd=web, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock
import json
import pytest

@pytest.mark.parametrize("allowed", [True, False])
def test_python_preflight_precedes_off_mode_publication(allowed):
    from laughtrack.core.entities.show.model import Show
    from laughtrack.core.entities.show.curation import screen_shows
    show=Show(name="Occurrence",club_id=42,date=datetime(2027,1,1,tzinfo=timezone.utc),show_page_url="https://example.com/event",source_performance_id="provider:1",eligibility_source_id=7,eligibility_gate_mode="off")
    cursor=MagicMock();cursor.__enter__.return_value=cursor
    cursor.fetchone.return_value={"allowed":allowed,"reason":"blocked" if not allowed else "unreviewed"}
    conn=MagicMock();conn.cursor.return_value=cursor
    @contextmanager
    def transaction(): yield conn
    result=screen_shows(transaction,[show])
    assert result.shows==([show] if allowed else [])
    assert result.reconciliation_safe is allowed
    calls=cursor.execute.call_args_list
    assert calls[0].args[0]=="SELECT curation_lock_intake()"
    observed=json.loads(calls[1].args[1][0])
    assert observed["source_id"]==7 and observed["source_performance_id"]=="provider:1"


def test_policy_unavailable_fails_closed():
    from laughtrack.core.entities.show.model import Show
    from laughtrack.core.entities.show.curation import screen_shows
    show=Show(name="Occurrence",club_id=42,date=datetime(2027,1,1,tzinfo=timezone.utc),show_page_url="https://example.com")
    def unavailable(): raise RuntimeError("Database unavailable")
    result=screen_shows(unavailable,[show])
    assert not result.shows and result.withheld==1 and not result.reconciliation_safe


@pytest.mark.parametrize("row,allowed", [(None,False),((1,),True)])
def test_delivery_rechecks_publication_predicate(monkeypatch,row,allowed):
    from laughtrack.core.services.notification import service as module
    cursor=MagicMock();cursor.__enter__.return_value=cursor;cursor.fetchone.return_value=row
    conn=MagicMock();conn.cursor.return_value=cursor
    @contextmanager
    def connection(): yield conn
    monkeypatch.setattr(module,"get_connection",connection)
    assert module.ComedianArrivalNotificationService()._show_is_public(42) is allowed
    sql,params=cursor.execute.call_args.args
    assert "s.visible" in sql and "NOT s.is_cancelled" in sql and "c.visible" in sql and params==(42,)


def test_publication_fence_reuses_connection_for_nested_entity_writes(monkeypatch):
    from laughtrack.core.data.base_handler import BaseDatabaseHandler, publication_transaction
    class Handler(BaseDatabaseHandler):
        def get_entity_name(self): return "test"
        def get_entity_class(self): return dict
    show_handler=Handler();ticket_handler=Handler();shared=MagicMock()
    monkeypatch.setattr(show_handler,"create_connection",MagicMock(side_effect=AssertionError("Competing connection")))
    monkeypatch.setattr(ticket_handler,"create_connection",MagicMock(side_effect=AssertionError("Competing connection")))
    with publication_transaction(shared):
        with show_handler.transaction() as conn:
            assert conn is shared
            with ticket_handler._acquire_connection(None) as nested:
                assert nested is shared
    shared.commit.assert_not_called();shared.close.assert_not_called()
    with pytest.raises(AssertionError,match="Competing connection"):
        with show_handler.transaction(): pass


def test_publication_connection_does_not_leak_to_another_worker():
    from concurrent.futures import ThreadPoolExecutor
    from laughtrack.core.data.base_handler import _publication_connection, publication_transaction
    with publication_transaction(object()):
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(_publication_connection.get).result() is None
