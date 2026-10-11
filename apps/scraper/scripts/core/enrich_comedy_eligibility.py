"""Bounded model enrichment of staged reviews; never writes public entities."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.core.comedy_eligibility import (
    CLASSIFIER_VERSION,
    EventEvidence,
    PerformerObservation,
    classify_comedy_eligibility,
    normalize_name,
)
from laughtrack.core.comedy_eligibility_gate import _identity_snapshot
from laughtrack.core.comedy_eligibility_model import ModelConfig, ModelResolver, eligible, model_context
from laughtrack.core.comedy_eligibility_model_store import ModelDecisionStore
from laughtrack.core.comedy_eligibility_store import load_source
from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy

SELECT_REVIEWS = """
SELECT recent.source_id,recent.payload,recent.evidence FROM (
 SELECT DISTINCT ON (c.id) c.id,c.source_id,d.payload,d.evidence,d.decision,d.created_at
 FROM comedy_event_candidates c JOIN comedy_event_decisions d ON d.candidate_id=c.id
 JOIN scraping_sources ss ON ss.id=c.source_id
 WHERE ss.enabled AND ss.comedy_gate_mode IN ('shadow','enforce')
 AND (%s IS NULL OR c.id=%s)
 ORDER BY c.id,d.created_at DESC,d.id DESC
) recent WHERE recent.decision='review' ORDER BY recent.id LIMIT %s
"""


def collect_reviews(transaction, limit: int, candidate_id=None):
    """Snapshot current policies and identity state, then release DB before calls."""
    contexts = []
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(SELECT_REVIEWS, (candidate_id, candidate_id, limit))
            rows = cur.fetchall()
            for source_id, payload, old in rows:
                source = load_source(cur, source_id)
                if not source or not source["enabled"] or source["comedy_gate_mode"] == "off":
                    continue
                # A changed deterministic algorithm needs a fresh scrape first.
                if old.get("classifier_version") != CLASSIFIER_VERSION:
                    continue
                names = sorted(
                    {normalize_name(n) for n in payload.get("performers") or [] if isinstance(n, str) and n.strip()}
                )
                people, denied = _identity_snapshot(cur, names)
                decision = classify_comedy_eligibility(
                    source_id=source_id,
                    policy=SourceComedyPolicy.from_row(source),
                    evidence=[EventEvidence(**e) for e in old.get("evidence", [])],
                    performers=[PerformerObservation(n) for n in names],
                    people=people,
                    denied=denied,
                )
                if names and not payload.get("raw_performers_preserved"):
                    decision = replace(
                        decision,
                        lineup_status="partial",
                        reason_codes=tuple(sorted((*decision.reason_codes, "raw_lineup_partial"))),
                    )
                if eligible(decision):
                    contexts.append((model_context(payload, decision, people, denied), decision))
    return contexts


def enrich_reviews(transaction, provider, config, *, limit=25, candidate_id=None):
    if not config.enabled:
        return {"selected": 0, "cached": 0, "review": 0, "disabled": True}
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Limit must be between 1 and 1000")
    contexts = collect_reviews(transaction, limit, candidate_id)
    resolver = ModelResolver(ModelDecisionStore(transaction), provider, config)
    cached = sum(resolver.enrich(context, decision) is not None for context, decision in contexts)
    return {"selected": len(contexts), "cached": cached, "review": len(contexts) - cached, "disabled": False}


def configured_provider(config):
    if config.provider != "openai":
        raise ValueError("Only the explicitly selected OpenAI provider is supported")
    from laughtrack.core.clients.comedy_model.client import OpenAIComedyProvider

    return OpenAIComedyProvider()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--candidate-id", type=int)
    args = parser.parse_args(argv)
    from dotenv import load_dotenv

    load_dotenv(_root / ".env")
    config = ModelConfig.from_env()
    if not config.enabled:
        print(json.dumps({"disabled": True, "selected": 0}))
        return 0
    provider = configured_provider(config)
    from laughtrack.adapters.db import get_transaction

    print(
        json.dumps(enrich_reviews(get_transaction, provider, config, limit=args.limit, candidate_id=args.candidate_id))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
