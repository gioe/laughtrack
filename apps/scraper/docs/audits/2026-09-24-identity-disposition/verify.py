import argparse,json
from pathlib import Path
from psycopg2.extras import RealDictCursor
from scripts.core import audit_false_positive_comedians
from laughtrack.infrastructure.database.connection import get_connection
parser=argparse.ArgumentParser(description='Read-only post-repair and post-scrape verification for TASK-4043')
parser.add_argument('--receipt',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
p=Path(__file__).resolve().parent;d=json.loads((p/'decisions.json').read_text());old={'shows':[json.loads(line) for line in (p/'shows.jsonl').read_text().splitlines()]};receipt=json.loads(args.receipt.read_text())
assert receipt['committed'] and receipt['mode']=='repair'
suppressed=[c for c in d['identities'] if c['action']=='suppress'];uuids=[c['uuid'] for c in d['identities']];names=[c['name'].lower() for c in suppressed];showids=sorted({s['show_id'] for s in old['shows']})
with get_connection() as conn:
 with conn.cursor(cursor_factory=RealDictCursor) as cur:
  cur.execute('SET default_transaction_read_only=on')
  cur.execute('SELECT id,uuid,name,visible,parent_comedian_id,block_added_by FROM comedians WHERE id=ANY(%s) ORDER BY id',([c['id'] for c in d['identities']],));now=[dict(x) for x in cur.fetchall()]
  byid={x['id']:x for x in now}
  assert all(not byid[c['id']]['visible'] and byid[c['id']]['block_added_by']=='TASK-4043' for c in suppressed)
  assert all(byid[c['id']]['name']==c['canonical_name'] and byid[c['id']]['visible'] for c in d['identities'] if c['action']=='canonicalize')
  assert all(byid[c['id']]['parent_comedian_id'] is None for c in d['identities'] if c['detach_parent'])
  assert all(byid[c['id']]['visible']==c['visible'] for c in d['identities'] if c['action']=='retain')
  cur.execute('SELECT id,name FROM comedians WHERE visible AND lower(name)=ANY(%s)',(names,));duplicates=[dict(x) for x in cur.fetchall()];assert not duplicates
  cur.execute('SELECT id FROM shows WHERE id=ANY(%s)',(showids,));surviving={x['id'] for x in cur.fetchall()};assert surviving==set(showids)
  cur.execute('SELECT show_id,comedian_id FROM lineup_items WHERE show_id=ANY(%s)',(showids,));links={(x['show_id'],x['comedian_id']) for x in cur.fetchall()}
  assert all((x['show_id'],x['comedian_id']) in links for x in receipt['inserted_lineups'])
  falseuuids={c['uuid'] for c in suppressed}
  before={(s['show_id'],uuid) for s in old['shows'] for uuid in s['existing_cast'] if uuid not in falseuuids}
  removed=sorted(before-links)
  cur.execute('SELECT count(*) n FROM favorite_comedians WHERE comedian_id=ANY(%s)',(uuids,));favoritecount=cur.fetchone()['n'];assert favoritecount==sum(c['favorites'] for c in d['identities'])
  cur.execute('SELECT show_id,count(*) n FROM lineup_items WHERE show_id IN (480151,2699858) GROUP BY show_id ORDER BY show_id');io=[dict(x) for x in cur.fetchall()]
result={'checked_at_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'suppressed':len(suppressed),'visible_false_duplicates':duplicates,'corrected_names':3,'detached_parents':3,'preserved_shows':len(surviving),'added_links_still_present':len(receipt['inserted_lineups']),'candidate_favorites':favoritecount,'removed_other_cast_links':removed,'io_lineup_counts':io,'identities':now}
args.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='identities'},indent=2))
assert not removed, 'Investigate removed real cast links'
assert {x['show_id']:x['n'] for x in io}=={480151:63,2699858:23}, 'iO cast regression'
