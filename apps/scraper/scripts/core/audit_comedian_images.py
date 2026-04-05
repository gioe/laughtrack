"""Audit comedian CDN images and update has_image column.

Usage:
    # Dry-run: show which comedians have/don't have CDN images
    python scripts/core/audit_comedian_images.py

    # Update the has_image column in the DB
    python scripts/core/audit_comedian_images.py --update
"""

import argparse
import ssl
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
from dotenv import dotenv_values

CDN_HOST = "laughtrack.b-cdn.net"


def get_connection():
    v = dotenv_values(".env")
    return psycopg2.connect(
        dbname=v["DATABASE_NAME"],
        user=v["DATABASE_USER"],
        password=v["DATABASE_PASSWORD"],
        host=v["DATABASE_HOST"],
        port=v.get("DATABASE_PORT", "5432"),
        sslmode="require",
    )


def check_image(name: str) -> tuple[str, bool]:
    url = f"https://{CDN_HOST}/comedians/{urllib.parse.quote(name)}.png"
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
    parser = argparse.ArgumentParser(description="Audit comedian CDN images")
    parser.add_argument(
        "--update", action="store_true", help="Update has_image column in DB"
    )
    args = parser.parse_args()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT name, has_image FROM comedians WHERE parent_comedian_id IS NULL ORDER BY name")
    rows = cur.fetchall()
    names = [r[0] for r in rows]
    current_state = {r[0]: r[1] for r in rows}

    print(f"Checking {len(names)} non-alias comedians against CDN...", file=sys.stderr)

    results: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_image, n): n for n in names}
        for i, f in enumerate(as_completed(futures)):
            name, has_img = f.result()
            results[name] = has_img
            if (i + 1) % 500 == 0:
                print(f"  Checked {i + 1}/{len(names)}...", file=sys.stderr)

    has_image = [n for n, v in results.items() if v]
    missing = [n for n, v in results.items() if not v]

    # Compute changes
    newly_found = [n for n in has_image if not current_state.get(n)]
    newly_missing = [n for n in missing if current_state.get(n)]

    print(f"\n=== CDN Image Audit ===")
    print(f"Total checked: {len(names)}")
    print(f"Has image:     {len(has_image)} ({100 * len(has_image) / len(names):.1f}%)")
    print(f"Missing:       {len(missing)} ({100 * len(missing) / len(names):.1f}%)")
    print(f"\nChanges from current DB state:")
    print(f"  Newly found (false -> true): {len(newly_found)}")
    print(f"  Newly missing (true -> false): {len(newly_missing)}")

    if newly_found:
        print(f"\n  New images found for:")
        for n in sorted(newly_found)[:20]:
            print(f"    + {n}")
        if len(newly_found) > 20:
            print(f"    ... and {len(newly_found) - 20} more")

    if newly_missing:
        print(f"\n  Images removed for:")
        for n in sorted(newly_missing)[:20]:
            print(f"    - {n}")
        if len(newly_missing) > 20:
            print(f"    ... and {len(newly_missing) - 20} more")

    if args.update and (newly_found or newly_missing):
        if newly_found:
            placeholders = ", ".join(["%s"] * len(newly_found))
            cur.execute(f"UPDATE comedians SET has_image = true WHERE name IN ({placeholders})", tuple(newly_found))
            print(f"\nUpdated {cur.rowcount} rows to has_image=true")

        if newly_missing:
            placeholders = ", ".join(["%s"] * len(newly_missing))
            cur.execute(f"UPDATE comedians SET has_image = false WHERE name IN ({placeholders})", tuple(newly_missing))
            print(f"Updated {cur.rowcount} rows to has_image=false")

        conn.commit()
        print("Changes committed to DB.")
    elif args.update:
        print("\nNo changes needed — DB is already up to date.")

    conn.close()


if __name__ == "__main__":
    main()
