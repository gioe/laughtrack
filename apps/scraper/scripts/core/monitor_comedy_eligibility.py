"""Report source comedy quality, explicitly downgrade unsafe trust, or roll back."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.core.comedy_eligibility_monitor import MonitorConfig, evaluate_source


def main(argv=None, *, store=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    report = commands.add_parser("report", help="Record and print deduplicated reports; never change policy")
    report.add_argument("--source-id", type=int)
    apply = commands.add_parser("apply", help="Explicitly apply a qualifying comedy_only to mixed/enforce downgrade")
    apply.add_argument("--source-id", type=int, required=True)
    history = commands.add_parser("history")
    history.add_argument("--source-id", type=int, required=True)
    rollback = commands.add_parser("rollback")
    rollback.add_argument("--transition-id", type=int, required=True)
    rollback.add_argument("--expected-version", type=int, required=True)
    rollback.add_argument("--actor", required=True)
    rollback.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    if store is None:
        from dotenv import load_dotenv

        load_dotenv(_root / ".env")
        from laughtrack.adapters.db import get_transaction
        from laughtrack.core.comedy_eligibility_monitor_store import MonitorStore

        store = MonitorStore(get_transaction)
    if args.command == "history":
        result = store.history(args.source_id)
    elif args.command == "rollback":
        result = store.rollback(
            args.transition_id, expected_version=args.expected_version, actor=args.actor, reason=args.reason
        )
    else:
        config = MonitorConfig.from_env()
        if args.source_id is not None:
            source_ids = [args.source_id]
        else:
            source_ids = sorted(
                s["id"]
                for s in store.sources()
                if s["comedy_policy"] == "comedy_only" or s["comedy_gate_mode"] != "off"
            )
        reports = [evaluate_source(store, sid, config, apply=args.command == "apply") for sid in source_ids]
        result = {
            "monitored_source_count": len(source_ids),
            "reports": reports,
            "status": "no_monitored_sources" if not source_ids else "reported",
        }
    print(json.dumps(result, sort_keys=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
