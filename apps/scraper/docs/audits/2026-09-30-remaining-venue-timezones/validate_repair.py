"""Validate the exact timezone repair against local fixtures or production; always roll back.

Usage: python validate_repair.py --local-dsn 'host=127.0.0.1 port=55475 dbname=postgres'
       python validate_repair.py --env-file apps/scraper/.env --output /tmp/proof.json
The production path uses a dedicated connection and never commits.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import psycopg2
from psycopg2.extensions import parse_dsn
from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
TABLES = ('shows', 'tickets', 'lineup_items', 'tagged_shows', 'saved_shows',
          'sent_notifications', 'ticket_purchase_click_events', 'discovery_show_feature_snapshots')


def digest(rows):
    values = sorted(json.dumps(row, sort_keys=True, separators=(',', ':'), default=str) for row in rows)
    return {'count': len(values), 'sha256': hashlib.sha256('\n'.join(values).encode()).hexdigest()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--local-dsn')
    group.add_argument('--env-file')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.local_dsn:
        if parse_dsn(args.local_dsn).get('host') not in ('localhost', '127.0.0.1', '::1'):
            p.error('Local validation requires an explicit loopback host')
        conn = psycopg2.connect(args.local_dsn)
    else:
        v = dotenv_values(args.env_file)
        conn = psycopg2.connect(host=v['DATABASE_HOST'], dbname=v['DATABASE_NAME'], user=v['DATABASE_USER'],
                                password=v['DATABASE_PASSWORD'], port=v.get('DATABASE_PORT', 5432), sslmode='require')
    plan = json.loads((HERE / 'repair-plan.json').read_text())
    snapshot = json.loads((HERE / 'before.json').read_text())
    cohort = [c['id'] for c in snapshot['clubs']]
    expected = {r['id']: r['new_timezone'] for r in plan}
    sql = (HERE.parents[4] / 'apps/web/prisma/migrations/20260930020000_resolve_remaining_venue_timezones/migration.sql').read_text()
    conn.set_session(isolation_level='REPEATABLE READ')
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='60s'")
            if args.local_dsn:
                cur.execute('CREATE TEMP TABLE clubs(id integer PRIMARY KEY,name text,address text,zip_code text,visible boolean,timezone text,extra jsonb)')
                cur.executemany('INSERT INTO clubs VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb)', [
                    tuple(c[k] for k in ('id','name','address','zip_code','visible','timezone')) + (json.dumps(c),)
                    for c in snapshot['clubs']])
                cur.execute('CREATE TEMP TABLE shows(id integer PRIMARY KEY,club_id integer,date timestamptz)')
                cur.executemany('INSERT INTO shows VALUES(%s,%s,%s)', [(s['id'],s['club_id'],s['date']) for s in snapshot['shows']])
                cur.execute('SET LOCAL search_path=pg_temp')

            def clubs():
                cur.execute('SELECT to_jsonb(c) FROM clubs c WHERE id=ANY(%s) ORDER BY id', (cohort,))
                return [r[0] for r in cur.fetchall()]

            def related():
                cur.execute('SELECT id FROM shows WHERE club_id=ANY(%s)', (cohort,))
                ids = [r[0] for r in cur.fetchall()]
                result = {}
                for t in (('shows',) if args.local_dsn else TABLES):
                    col = 'id' if t == 'shows' else 'show_id'
                    cur.execute(f'SELECT to_jsonb(t) FROM {t} t WHERE {col}=ANY(%s)', (ids,))
                    result[t] = digest([r[0] for r in cur.fetchall()])
                return result

            before = clubs(); before_related = related()
            cur.execute('SAVEPOINT baseline')
            cur.execute(sql)
            after = clubs()
            assert len(before) == len(after)
            changed = []
            for old, new in zip(before, after):
                assert {k:v for k,v in old.items() if k != 'timezone'} == {k:v for k,v in new.items() if k != 'timezone'}
                assert new['timezone'] == expected.get(old['id'], old['timezone'])
                if new['timezone'] != old['timezone']: changed.append(old['id'])
            assert set(changed) == set(expected), 'Expected all four fresh changes in validation snapshot'
            assert related() == before_related
            cur.execute(sql); assert clubs() == after
            cur.execute('ROLLBACK TO SAVEPOINT baseline'); assert clubs() == before
            checks = []
            for target in plan:
                for field, value in [('name','changed'),('address','changed'),('zip_code','00000'),('visible',False),('timezone','Europe/London'),('timezone',''),('timezone',' ')]:
                    cur.execute(f'UPDATE clubs SET {field}=%s WHERE id=%s', (value,target['id']))
                    cur.execute('SAVEPOINT drift')
                    try:
                        cur.execute(sql)
                    except psycopg2.Error as e:
                        assert 'TASK-4075' in str(e)
                        cur.execute('ROLLBACK TO SAVEPOINT drift')
                    else:
                        raise AssertionError(f'Missed {field} guard for {target["id"]}')
                    cur.execute('ROLLBACK TO SAVEPOINT baseline')
                    assert clubs() == before
                    checks.append({'id':target['id'],'field':field,'result':'rejected'})
            result = {'captured_at':datetime.now(timezone.utc).isoformat(), 'mode':'local' if args.local_dsn else 'production_rollback',
                      'migration_sha256':hashlib.sha256(sql.encode()).hexdigest(),'changed_ids':changed,'idempotence':'passed',
                      'guards':checks,'unrelated_club_fields':'unchanged','related':before_related,'rollback':'passed'}
        conn.rollback()
        args.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:
        conn.rollback(); conn.close()

if __name__ == '__main__':
    main()
