"""Inspect staged events and apply attributed, previewed eligibility reviews."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    queue = commands.add_parser("list", help="Read a stable page of candidates")
    queue.add_argument("--source-id", type=int)
    queue.add_argument("--club-id", type=int)
    queue.add_argument("--decision", choices=("accept", "reject", "review"))
    queue.add_argument("--review-state")
    queue.add_argument("--coverage", choices=("missing", "partial", "observed"))
    queue.add_argument("--after-id", type=int, default=0)
    queue.add_argument("--ceiling-id", type=int)
    queue.add_argument("--limit", type=int, default=50)
    detail = commands.add_parser("inspect", help="Read evidence, source and immutable history")
    detail.add_argument("candidate_id", type=int)
    preview = commands.add_parser("preview", help="Prepare exact candidate scopes without applying actions")
    preview.add_argument("--candidate-id", type=int, action="append", required=True)
    preview.add_argument("--action", choices=("approve", "reject", "defer"), required=True)
    preview.add_argument("--actor", required=True)
    preview.add_argument("--reason", required=True)
    apply = commands.add_parser("apply", help="Apply the exact previously inspected preview")
    apply.add_argument("--preview-id", required=True)
    apply.add_argument("--token-digest", required=True)
    apply.add_argument("--actor", required=True)
    apply.add_argument("--idempotency-key", required=True)
    return result


def main(argv=None, *, store=None):
    args = parser().parse_args(argv)
    if store is None:
        from dotenv import load_dotenv

        load_dotenv(_root / ".env")
        from laughtrack.adapters.db import get_transaction
        from laughtrack.core.comedy_eligibility_review import current_identity_fingerprint
        from laughtrack.core.comedy_eligibility_review_store import ReviewStore

        store = ReviewStore(get_transaction, snapshot_validator=current_identity_fingerprint)
    if args.command == "list":
        filters = {
            k: getattr(args, k)
            for k in ("source_id", "club_id", "decision", "review_state", "coverage")
            if getattr(args, k) is not None
        }
        output = store.list_queue(filters=filters, after_id=args.after_id, ceiling_id=args.ceiling_id, limit=args.limit)
    elif args.command == "inspect":
        output = store.detail(args.candidate_id)
    elif args.command == "preview":
        output = {"operation": "PLAN", **store.preview(args.candidate_id, args.action, args.reason, args.actor)}
    else:
        output = store.apply(args.preview_id, args.actor, args.idempotency_key, args.token_digest)
    print(json.dumps(output, sort_keys=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
