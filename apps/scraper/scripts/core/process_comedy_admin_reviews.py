"""Apply pending admin reviews. No model calls, scraping or public inventory writes.

Usage: python -m scripts.core.process_comedy_admin_reviews --limit 100
"""
import argparse
import json
from pathlib import Path
import sys

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(_root / ".env")
    from laughtrack.adapters.db import get_transaction
    from laughtrack.core.comedy_admin_reviews import process_requests
    print(json.dumps(process_requests(get_transaction, args.limit)))


if __name__ == "__main__":
    main()
