"""Sync club has_image flag with CDN.

Checks BunnyCDN for club images and updates the has_image column accordingly.

Usage:
    # Dry-run: show which clubs have/don't have CDN images
    python scripts/core/sync_club_images.py

    # Update the has_image column in the DB
    python scripts/core/sync_club_images.py --update
"""

import argparse
import os
import ssl
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import psycopg2
from dotenv import dotenv_values

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from laughtrack.infrastructure.database.connection import get_transaction  # noqa: E402

CDN_HOST = "laughtrack.b-cdn.net"


def get_connection():
    v = {**dotenv_values(".env"), **os.environ}
    return psycopg2.connect(
        dbname=v["DATABASE_NAME"],
        user=v["DATABASE_USER"],
        password=v["DATABASE_PASSWORD"],
        host=v["DATABASE_HOST"],
        port=v.get("DATABASE_PORT", "5432"),
        sslmode="require",
    )


def check_image(name: str) -> tuple[str, bool]:
    url = f"https://{CDN_HOST}/clubs/{urllib.parse.quote(name)}.png"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            return (name, r.status == 200)
    except urllib.error.HTTPError:
        return (name, False)
    except Exception:
        return (name, False)


def main():
    parser = argparse.ArgumentParser(description="Sync club has_image flag with CDN")
    parser.add_argument(
        "--update", action="store_true", help="Update has_image column in DB"
    )
    args = parser.parse_args()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT name, has_image FROM clubs ORDER BY name")
    rows = cur.fetchall()
    names = [r[0] for r in rows]
    current_state = {r[0]: r[1] for r in rows}

    print(f"Checking {len(names)} clubs against CDN...", file=sys.stderr)

    results: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_image, n): n for n in names}
        for i, f in enumerate(as_completed(futures)):
            name, has_img = f.result()
            results[name] = has_img

    has_image = [n for n, v in results.items() if v]
    missing = [n for n, v in results.items() if not v]

    newly_found = [n for n in has_image if not current_state.get(n)]
    newly_missing = [n for n in missing if current_state.get(n)]

    print(f"\n=== Club CDN Image Sync ===")
    print(f"Total checked: {len(names)}")
    print(f"Has image:     {len(has_image)} ({100 * len(has_image) / len(names):.1f}%)")
    print(f"Missing:       {len(missing)} ({100 * len(missing) / len(names):.1f}%)")
    print(f"\nChanges from current DB state:")
    print(f"  Newly found (false -> true): {len(newly_found)}")
    print(f"  Newly missing (true -> false): {len(newly_missing)}")

    if newly_found:
        print(f"\n  New images found for:")
        for n in sorted(newly_found):
            print(f"    + {n}")

    if newly_missing:
        print(f"\n  Images removed for:")
        for n in sorted(newly_missing):
            print(f"    - {n}")

    if args.update and (newly_found or newly_missing):
        with get_transaction() as wconn:
            with wconn.cursor() as wcur:
                if newly_found:
                    placeholders = ", ".join(["%s"] * len(newly_found))
                    wcur.execute(f"UPDATE clubs SET has_image = true WHERE name IN ({placeholders})", tuple(newly_found))
                    print(f"\nUpdated {wcur.rowcount} rows to has_image=true")

                if newly_missing:
                    placeholders = ", ".join(["%s"] * len(newly_missing))
                    wcur.execute(f"UPDATE clubs SET has_image = false WHERE name IN ({placeholders})", tuple(newly_missing))
                    print(f"Updated {wcur.rowcount} rows to has_image=false")
        print("Changes committed to DB.")
    elif args.update:
        print("\nNo changes needed — DB is already up to date.")

    conn.close()


if __name__ == "__main__":
    main()
