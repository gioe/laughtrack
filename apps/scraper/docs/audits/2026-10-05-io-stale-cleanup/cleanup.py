"""One-shot TASK-4105 cleanup. Defaults to rollback; requires a private export path."""
import argparse
import json
import os
import runpy
from datetime import datetime, timezone, timedelta
from pathlib import Path

from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from laughtrack.foundation.db_util import connect_with_retry
from replay import ROOT, utc, verify

TABLES = ('tickets', 'lineup_items', 'tagged_shows', 'sent_notifications',
          'ticket_purchase_click_events', 'discovery_show_feature_snapshots', 'saved_shows')


def snapshot(cursor, ids, lock=False):
    result = {}
    for table in ('shows',) + TABLES:
        key = 'id' if table == 'shows' else 'show_id'
        query = sql.SQL('SELECT * FROM {} WHERE {}=ANY(%s)' + (' FOR UPDATE' if lock else ''))
        cursor.execute(query.format(sql.Identifier(table), sql.Identifier(key)), (ids,))
        result[table] = sorted((dict(row) for row in cursor.fetchall()),
                               key=lambda row: json.dumps(row, default=str, sort_keys=True))
    return result


def run(args):
    selected = verify()
    ids = sorted(r['id'] for r in selected)
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    cutoff = utc(manifest['cutoff'])
    if not cutoff <= datetime.now(timezone.utc) <= cutoff + timedelta(hours=24):
        raise RuntimeError('Evidence expired; revalidate rather than widening the time guard')
    evidence = json.loads((ROOT / 'before.json').read_text())
    expected = {r['id']: r for r in evidence['shows']}
    query = runpy.run_path(str(ROOT.parents[2] / 'bin/query'))
    conn = connect_with_retry(query['_resolve_database_url']())
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SET LOCAL lock_timeout='5s'")
            cur.execute("SET LOCAL statement_timeout='30s'")
            # Lock venue identities, then their dependents. New referencing rows
            # cannot race the export/delete because their FK takes a key-share lock.
            cur.execute('SELECT id FROM shows WHERE club_id=182 ORDER BY id FOR UPDATE')
            all_ids = [r['id'] for r in cur.fetchall()]
            before = snapshot(cur, all_ids, lock=True)
            replacement = next((r for r in before['shows'] if r['id'] == 1044696), None)
            replacement_expected = next(r for r in evidence['club_shows'] if r['id'] == 1044696)
            if (replacement is None or replacement['show_page_url'] != replacement_expected['show_page_url']
                    or utc(replacement['date']) != utc(replacement_expected['date'])):
                raise RuntimeError('Verified replacement identity drift')
            targets = [r for r in before['shows'] if r['id'] in ids]
            if len(targets) != 29:
                raise RuntimeError('Expected exactly 29 reviewed rows; already applied or identity drift')
            for row in targets:
                prior = expected[row['id']]
                if row['club_id'] != 182:
                    raise RuntimeError('Club mismatch')
                for field in ('name', 'show_page_url', 'room', 'last_scraped_by'):
                    if row[field] != prior[field]:
                        raise RuntimeError(f'Identity drift: {row["id"]} {field}')
                for field in ('date', 'last_scraped_date'):
                    if utc(row[field]) != utc(prior[field]):
                        raise RuntimeError(f'Freshness/date drift: {row["id"]} {field}')
                if not utc(row['date']) > datetime.now(timezone.utc) or not utc(row['last_scraped_date']) < cutoff:
                    raise RuntimeError('Not a stale future row')
            for table in ('sent_notifications', 'saved_shows', 'discovery_show_feature_snapshots'):
                if any(r['show_id'] in ids for r in before[table]):
                    raise RuntimeError(f'Protected references appeared: {table}')
            for table in ('tickets', 'tagged_shows'):
                live = [r for r in before[table] if r['show_id'] in ids]
                prior = [r for r in evidence[table] if r['show_id'] in ids]
                if json.loads(json.dumps(live, default=str)) != prior:
                    # Database row order is not an identity signal.
                    if sorted(json.loads(json.dumps(live, default=str)), key=lambda r: r['id']) != sorted(prior, key=lambda r: r['id']):
                        raise RuntimeError(f'Dependent drift: {table}')
            backup = {table: [r for r in rows if r['id' if table == 'shows' else 'show_id'] in ids]
                      for table, rows in before.items()}
            backup['captured_at'] = datetime.now(timezone.utc).isoformat()
            backup['task_id'] = 4105
            # Exclusive mode prevents overwriting the only recovery copy on retry.
            with os.fdopen(os.open(args.export, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
                json.dump(backup, f, default=str, indent=2)
                f.write('\n')
                f.flush()
                os.fsync(f.fileno())
            cur.execute('DELETE FROM shows WHERE id=ANY(%s) RETURNING id', (ids,))
            deleted = sorted(r['id'] for r in cur.fetchall())
            if deleted != ids:
                raise RuntimeError('Deleted cohort mismatch')
            keep_ids = sorted(set(all_ids) - set(ids))
            after = snapshot(cur, keep_ids)
            for table, rows in before.items():
                key = 'id' if table == 'shows' else 'show_id'
                if after[table] != [r for r in rows if r[key] not in ids]:
                    raise RuntimeError(f'Retained data changed: {table}')
            clicks = sorted(backup['ticket_purchase_click_events'], key=lambda row: row['id'])
            cur.execute('SELECT * FROM ticket_purchase_click_events WHERE id=ANY(%s) ORDER BY id', ([r['id'] for r in clicks],))
            if [dict(r) for r in cur.fetchall()] != [dict(r, show_id=None) for r in clicks]:
                raise RuntimeError('Click attribution changed')
            cur.execute('UPDATE clubs SET total_shows=(SELECT count(*) FROM shows WHERE club_id=182) WHERE id=182')
            if cur.rowcount != 1:
                raise RuntimeError('Club count refresh missed')
            summary = {'mode': 'applied' if args.apply else 'rolled_back', 'deleted_ids': deleted,
                       'before_show_count': len(all_ids), 'after_show_count': len(keep_ids),
                       'held_ids': sorted(r['id'] for r in json.loads((ROOT / 'decisions.json').read_text()) if r['decision'] == 'hold'),
                       'dependent_counts': {t: len(backup[t]) for t in TABLES},
                       'preserved_clicks': len(clicks), 'retained_rows_unchanged': True,
                       'replacement_1044696_preserved': 1044696 in keep_ids,
                       'completed_at': datetime.now(timezone.utc).isoformat()}
        if args.apply:
            conn.commit()
        else:
            conn.rollback()
        print(json.dumps(summary, indent=2))
        if args.result:
            Path(args.result).write_text(json.dumps(summary, indent=2) + '\n')
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--export', required=True, help='New private recovery JSON path; contains click/user identifiers')
    parser.add_argument('--result', help='Optional sanitized result path')
    run(parser.parse_args())
