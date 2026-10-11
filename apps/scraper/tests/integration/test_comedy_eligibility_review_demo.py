"""Synthetic operator demonstration through real CLI/store/gate/handler code.

Only database I/O and physical public persistence are doubles. PostgreSQL
constraints and concurrency are exercised separately by the PGlite suite.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path


def test_harvelles_style_review_demo(monkeypatch, capsys):
    from laughtrack.core import comedy_eligibility_gate as gate
    from laughtrack.core import comedy_eligibility_review_store as reviews
    from laughtrack.core.comedy_eligibility import CanonicalPerson
    from laughtrack.core.comedy_eligibility_review import current_identity_fingerprint
    from laughtrack.core.comedy_eligibility_store import LOAD_SOURCE_SQL, StagedCandidate, fingerprint
    from laughtrack.core.entities.show.model import Show
    from scripts.core.review_comedy_eligibility import main

    helpers_path = Path(__file__).with_name("test_comedy_eligibility_gate.py")
    spec = importlib.util.spec_from_file_location("review_demo_gate_helpers", helpers_path)
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    state = helpers._gate_environment(monkeypatch)
    fixture = json.loads(Path(__file__).with_name("fixtures").joinpath("comedy_eligibility_review_demo.json").read_text())
    state.source.update(fixture["source"])
    original_source = dict(state.source)
    candidates, actions, previews, operations = {}, [], {}, {}
    people = [CanonicalPerson(**p) for p in fixture["people"]]
    monkeypatch.setenv("COMEDY_MODEL_ENABLED", "0")
    monkeypatch.setenv("COMEDY_MODEL_CACHE_ENABLED", "0")
    monkeypatch.setattr(gate, "_identity_snapshot", lambda cursor, names: (people if "r. example" in names else [], []))

    class Cursor:
        description = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, sql, params=()):
            self.rows = []
            if sql.startswith(LOAD_SOURCE_SQL):
                self.rows = [dict(state.source)]
            elif sql.startswith(reviews.CURRENT_SQL):
                row = candidates.get(params[0])
                self.rows = [dict(row)] if row else []
            elif sql == reviews.INSERT_PREVIEW_SQL:
                pid, actor, action, reason, items, digest = params
                previews[pid] = dict(id=pid, actor=actor, action=action, reason=reason,
                                     items=json.loads(items), token_digest=digest, fresh=True)
            elif sql == reviews.LOAD_PREVIEW_SQL:
                self.rows = [previews[params[0]]] if params[0] in previews else []
            elif sql == reviews.LOAD_OPERATION_SQL:
                self.rows = [r for r in operations.values() if r["idempotency_key"] == params[0] or r["preview_id"] == params[1]]
            elif sql == reviews.INSERT_OPERATION_SQL:
                key, pid, actor, digest, result = params
                operations[key] = dict(idempotency_key=key, preview_id=pid, actor=actor,
                                       token_digest=digest, result=json.loads(result))
            elif sql == reviews.ADVANCE_REVIEW_SQL:
                cid, version, generation = params
                row = candidates[cid]
                if (row["review_version"], row["observation_generation"]) == (version, generation):
                    row["review_version"] += 1
                    self.rows = [{"review_version": row["review_version"]}]
            elif sql == reviews.INSERT_REVIEW_SQL:
                keys = ("candidate_id", "observation_generation", "decision_id", "review_version",
                        "payload_fingerprint", "identity_fingerprint", "policy_version", "actor", "reason", "action", "operation_key")
                action = dict(zip(keys, params), id=len(actions) + 1)
                actions.append(action)
                candidates[action["candidate_id"]].update(
                    review_action=action["action"], reviewed_identity_fingerprint=action["identity_fingerprint"],
                    reviewed_payload_fingerprint=action["payload_fingerprint"], reviewed_policy_version=action["policy_version"])
            elif sql == reviews.LOAD_REVIEW_SQL:
                row = next((r for r in candidates.values() if (r["source_id"], r["event_key"]) == params), None)
                if row:
                    action = next((r for r in reversed(actions) if r["candidate_id"] == row["candidate_id"]), None)
                    self.rows = [{**(action or {"id": None}), "review_version": row["review_version"]}]
            elif sql == reviews.HISTORY_SQL:
                self.rows = [r for r in reversed(actions) if r["candidate_id"] == params[0]]
            elif sql == reviews.OBSERVATION_HISTORY_SQL:
                self.rows = [dict(candidates[params[0]])]
            elif sql == reviews.PUBLICATIONS_SQL:
                self.rows = [{"show_id": show_id} for source_id, event_key, show_id in state.publications
                             if event_key == candidates[params[0]]["event_key"]]
            else:
                raise AssertionError(f"Demo does not implement SQL: {sql}")

        def fetchone(self):
            return self.rows[0] if self.rows else None

        def fetchall(self):
            return self.rows

    class Connection:
        def cursor(self):
            return Cursor()

        def rollback(self):
            pass

    @contextmanager
    def transaction():
        state.active += 1
        try:
            yield Connection()
        finally:
            state.active -= 1

    state.transaction = transaction

    def stage(cursor, **kwargs):
        row = next((r for r in candidates.values() if r["event_key"] == kwargs["event_key"]), None)
        cid = row["candidate_id"] if row else len(candidates) + 1
        generation = row["observation_generation"] + 1 if row else 1
        version = row["review_version"] if row else 0
        decision = kwargs["decision"]
        state.staged.append(kwargs)
        current = dict(row or {}, candidate_id=cid, source_id=7, club_id=42, event_key=kwargs["event_key"],
                       observation_generation=generation, review_version=version, decision_id=len(state.staged),
                       identity_fingerprint=kwargs["baseline_identity_fingerprint"],
                       payload_fingerprint=fingerprint(kwargs["payload"]), policy_version=1,
                       payload=kwargs["payload"], evidence=decision.to_dict(), decision=decision.decision,
                       classifier_version=decision.classifier_version, current_policy_version=1,
                       gate_mode="enforce", enabled=True, club_name=fixture["venue"], scraper_key="synthetic-demo")
        candidates[cid] = current
        return StagedCandidate(cid, current["decision_id"], 7, kwargs["event_key"], 1, "enforce", generation, version)

    monkeypatch.setattr(gate, "stage_candidate", stage)
    monkeypatch.setattr(gate, "load_review", reviews.load_review)
    monkeypatch.setattr(gate, "verify_publication", lambda cursor, staged: (
        candidates[staged.id]["observation_generation"] == staged.observation_generation
        and candidates[staged.id]["review_version"] == staged.review_version
        and candidates[staged.id]["decision"] == "accept"))
    handler = helpers._writer_handler(monkeypatch, state)
    store = reviews.ReviewStore(transaction, current_identity_fingerprint)

    def show(item):
        return Show(name=item["name"], description=item["description"], club_id=42,
                    date=datetime(2099, 1, 1, 20, tzinfo=timezone.utc) + timedelta(days=fixture["events"].index(item)),
                    show_page_url=f"https://example.invalid/events/{item['key']}",
                    source_performance_id=item["key"], eligibility_source_id=7, last_scraped_by="synthetic-demo",
                    eligibility_performer_names=item["performers"], eligibility_raw_performers_preserved=True)

    music, comedy, unrelated = fixture["events"]
    assert handler.insert_shows([show(music)]).eligibility_withheld == 1
    assert handler.insert_shows([show(comedy)]).eligibility_withheld == 1
    assert handler.insert_shows([show(unrelated)]).total == 1
    public_before_review = dict(state.public)
    for cid, event in ((1, music), (2, comedy)):
        assert main(["inspect", str(cid)], store=store) == 0
        inspected = json.loads(capsys.readouterr().out)
        if cid == 2:
            performers = inspected["current"]["evidence"]["performers"]
            assert performers[0]["canonical_id"] == 102
            assert "canonical_parent_resolved" in performers[0]["diagnostics"]
        assert main(["preview", "--candidate-id", str(cid), "--action", event["review_action"],
                     "--actor", "synthetic-demo-operator", "--reason", event["review_reason"]], store=store) == 0
        preview = json.loads(capsys.readouterr().out)
        assert preview["operation"] == "PLAN" and len(actions) == cid - 1
        args = ["apply", "--preview-id", preview["preview_id"], "--token-digest", preview["token_digest"],
                "--actor", "synthetic-demo-operator", "--idempotency-key", f"synthetic-demo-{cid}"]
        assert main(args, store=store) == 0
        applied = json.loads(capsys.readouterr().out)
        assert main(args, store=store) == 0
        assert json.loads(capsys.readouterr().out) == applied
        assert len(actions) == cid
    assert state.public == public_before_review  # Review action itself never publishes.
    assert handler.insert_shows([show(music)]).eligibility_withheld == 1
    assert handler.insert_shows([show(comedy)]).total == 1
    assert handler.insert_shows([show(comedy)]).total == 1
    assert handler.insert_shows([show(unrelated)]).total == 1
    assert len(state.public) == 2
    assert {p[1] for p in state.publications} == {"native:comedy", "native:unrelated"}
    assert actions[0]["action"] == "reject" and actions[1]["action"] == "approve"
    assert actions[0]["actor"] == actions[1]["actor"] == "synthetic-demo-operator"
    assert state.source == original_source
    assert people[0].visible is False and people[0].parent_id == 102 and people[1].visible is True
    print(json.dumps({"fixture": "synthetic Harvelle's-style mixed programming", "review_actions": len(actions),
                      "music": "rejected and still withheld on next scrape", "comedy": "parent 102 resolved; approved and published through normal handler",
                      "public_events": len(state.public), "unrelated_event": "still published without duplicate", "source_policy": "unchanged",
                      "identity_visibility": "unchanged", "review_apply_public_writes": 0, "production_writes": 0}, sort_keys=True))
