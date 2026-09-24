"""TASK-4043 one-shot reviewed repair. Default: execute and roll back.

Run from apps/scraper with PYTHONPATH="$PWD/src:$PWD" and the scraper venv.
The --apply switch commits; --receipt is required and must not already exist.
Rollback uses the exact inserted lineup IDs and guarded original identity state.
Valid newly created canonicals intentionally survive rollback (no cascading deletes).
"""
import argparse
import json
from pathlib import Path

# Load environment exactly as the production audit does.
from scripts.core import audit_false_positive_comedians  # noqa: F401
from psycopg2.extras import RealDictCursor
from laughtrack.infrastructure.database.connection import create_connection
from laughtrack.utilities.domain.comedian.utils import ComedianUtils

ROOT = Path(__file__).resolve().parent
FIELDS = ['id', 'uuid', 'name', 'visible', 'parent_comedian_id', 'block_reason', 'block_added_by', 'block_added_at']
TAG = 'TASK-4043'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def serial(value):
    return json.loads(json.dumps(value, default=str))


def rows(cur, sql, args=()):
    cur.execute(sql, args)
    return [dict(r) for r in cur.fetchall()]


def identities(cur, ids):
    return rows(cur, 'SELECT '+','.join(FIELDS)+' FROM comedians WHERE id=ANY(%s) ORDER BY id FOR UPDATE', (ids,))


def protected(cur, uuids, show_ids):
    return {
        'favorites': rows(cur, 'SELECT * FROM favorite_comedians WHERE comedian_id=ANY(%s) ORDER BY profile_id,comedian_id', (uuids,)),
        'shows': rows(cur, 'SELECT * FROM shows WHERE id=ANY(%s) ORDER BY id', (show_ids,)),
        'lineups': rows(cur, 'SELECT * FROM lineup_items WHERE show_id=ANY(%s) ORDER BY id', (show_ids,)),
    }


def restore(cur, receipt):
    for link in receipt['inserted_lineups']:
        cur.execute('DELETE FROM lineup_items WHERE id=%s AND show_id=%s AND comedian_id=%s AND role IS NOT DISTINCT FROM %s',
                    (link['id'], link['show_id'], link['comedian_id'], link['role']))
        require(cur.rowcount == 1, f'Rollback lineup drift: {link}')
    for before, after in zip(receipt['before'], receipt['after']):
        if before == after:
            continue
        current = serial(identities(cur, [after['id']]))
        require(current == [after], f'Rollback identity drift: {after["id"]}')
        cur.execute('UPDATE comedians SET name=%s,visible=%s,parent_comedian_id=%s,block_reason=%s,block_added_by=%s,block_added_at=%s WHERE id=%s AND uuid=%s',
                    tuple(before[k] for k in ['name','visible','parent_comedian_id','block_reason','block_added_by','block_added_at','id','uuid']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--rollback', type=Path, help='Committed repair receipt to restore; dry-run unless --apply')
    args = parser.parse_args()
    require(not args.receipt.exists(), 'Refusing to overwrite receipt')
    plan = json.loads((ROOT/'decisions.json').read_text())
    attributions = json.loads((ROOT/'attributions.json').read_text())['attributions']
    candidates = plan['identities']
    ids = [c['id'] for c in candidates]
    shows = [json.loads(line) for line in (ROOT/'shows.jsonl').read_text().splitlines()]
    show_by_id = {s['show_id']:s for s in shows}
    conn = create_connection(autocommit=False)
    receipt = {'mode': 'rollback' if args.rollback else 'repair', 'committed': False}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            cur.execute("SET LOCAL lock_timeout='5s'")
            cur.execute('SELECT pg_advisory_xact_lock(4043)')
            if args.rollback:
                original = json.loads(args.rollback.read_text())
                require(original.get('committed') is True and original.get('mode') == 'repair', 'Expected committed repair receipt')
                restore(cur, original)
                receipt['restored_identities'] = len([1 for a,b in zip(original['before'],original['after']) if a!=b])
            else:
                before = serial(identities(cur, ids))
                expected = [{k:c[k] for k in FIELDS} for c in candidates]
                require(before == expected, 'Identity snapshot drift; refresh and review before applying')
                receipt['before'] = before
                protected_before = protected(cur, [c['uuid'] for c in candidates], list(show_by_id))
                for s in shows:
                    actual = next((r for r in protected_before['shows'] if r['id']==s['show_id']), None)
                    require(actual is not None, f'Missing show {s["show_id"]}')
                    require(all(serial(actual[k]) == s[k] for k in ['name','date','club_id','show_page_url']), f'Show identity drift {s["show_id"]}')
                receipt['created_canonicals'] = []
                receipt['inserted_lineups'] = []
                for c in candidates:
                    if c['action'] == 'canonicalize':
                        require(ComedianUtils.generate_uuid(c['canonical_name']) == c['uuid'], 'Canonical UUID mismatch')
                        require(not rows(cur, 'SELECT id FROM comedians WHERE lower(name)=lower(%s) AND id<>%s', (c['canonical_name'],c['id'])), 'Canonical name collision')
                        cur.execute('UPDATE comedians SET name=%s WHERE id=%s AND uuid=%s', (c['canonical_name'],c['id'],c['uuid']))
                canonical = {}
                for name in sorted({n for a in attributions for n in a['names']}):
                    normalized = ComedianUtils.normalize_name(name)
                    uuid = ComedianUtils.generate_uuid(normalized)
                    require(not rows(cur, 'SELECT name FROM comedian_deny_list WHERE lower(name)=lower(%s)', (normalized,)), f'Denied canonical: {name}')
                    matches = rows(cur, 'SELECT id,uuid,name,visible,parent_comedian_id FROM comedians WHERE lower(name)=lower(%s) OR uuid=%s FOR UPDATE', (normalized, uuid))
                    require(len(matches)<=1, f'Ambiguous canonical: {name}')
                    if matches:
                        c = matches[0]
                        require(c['name'].casefold()==normalized.casefold() and c['visible'] and c['parent_comedian_id'] is None, f'Unsafe canonical: {name}')
                    else:
                        c = rows(cur, 'INSERT INTO comedians(name,uuid) VALUES(%s,%s) RETURNING id,uuid,name,visible,parent_comedian_id', (normalized,uuid))[0]
                        receipt['created_canonicals'].append(c)
                    canonical[name] = c
                for a in attributions:
                    require(a['show_id'] in show_by_id, 'Unreviewed show')
                    for name in a['names']:
                        receipt['inserted_lineups'] += rows(cur, 'INSERT INTO lineup_items(show_id,comedian_id) VALUES(%s,%s) ON CONFLICT(show_id,comedian_id) DO NOTHING RETURNING *', (a['show_id'],canonical[name]['uuid']))
                for c in candidates:
                    if c['action'] != 'suppress':
                        continue
                    cur.execute('UPDATE comedians SET visible=false,parent_comedian_id=%s,block_reason=%s,block_added_by=%s,block_added_at=now() WHERE id=%s AND uuid=%s',
                                (None if c['detach_parent'] else c['parent_comedian_id'],c['reason'],TAG,c['id'],c['uuid']))
                    require(cur.rowcount==1, 'Unexpected update count')
                receipt['after'] = serial(identities(cur, ids))
                protected_after = protected(cur, [c['uuid'] for c in candidates], list(show_by_id))
                require(protected_before['favorites']==protected_after['favorites'], 'Favorites changed')
                require(protected_before['shows']==protected_after['shows'], 'Shows changed')
                added_ids = {x['id'] for x in receipt['inserted_lineups']}
                require(protected_before['lineups']==[x for x in protected_after['lineups'] if x['id'] not in added_ids], 'Existing cast changed')
                receipt['preserved'] = {k:len(v) for k,v in protected_before.items()}
                receipt['suppressed'] = sum(c['action']=='suppress' for c in candidates)
                receipt['canonicalized'] = sum(c['action']=='canonicalize' for c in candidates)
                receipt['detached'] = sum(c['detach_parent'] for c in candidates)
                # Exercise exact rollback without losing the applied state.
                cur.execute('SAVEPOINT rollback_check')
                restore(cur, serial(receipt))
                require(serial(identities(cur,ids))==before, 'Rollback failed to restore identities')
                require(protected(cur,[c['uuid'] for c in candidates],list(show_by_id))==protected_before, 'Rollback failed to restore protected rows')
                cur.execute('ROLLBACK TO SAVEPOINT rollback_check')
                receipt['rollback_verified'] = True
            args.receipt.write_text(json.dumps(serial(receipt),indent=2)+'\n')
            if args.apply:
                conn.commit()
                receipt['committed'] = True
            else:
                conn.rollback()
            args.receipt.write_text(json.dumps(serial(receipt),indent=2)+'\n')
            print(json.dumps({k:v for k,v in receipt.items() if k not in ['before','after','created_canonicals','inserted_lineups']},indent=2))
            print('New canonicals:',len(receipt.get('created_canonicals',[])),'new lineup links:',len(receipt.get('inserted_lineups',[])))
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
