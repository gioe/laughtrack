import collections
import datetime
import hashlib
import json
from pathlib import Path

p = Path(__file__).parent
groups = json.loads((p / 'groups.json').read_text())
shows = json.loads((p / 'shows.json').read_text())
flags = {}
def add(indices, category, reason):
    for index in indices:
        assert index not in flags
        flags[index] = {'assessment': category, 'reason': reason}

add([305,307,437,636,986,1136,1149,1362,1606,1839,1840,1841,1843,2017],
    'strong_non_comedy_flag', 'Listing bills music, a band, a concert, or a music open mic; no live comedy billing in the returned event evidence.')
add([235,410,415,585,869,1222,1383], 'strong_non_comedy_flag',
    'Listing bills bingo/trivia/skills games without an explicit comedy performance; requires event-level confirmation before removal.')
add([658,664,820,1893], 'strong_non_comedy_flag', 'Listing bills karaoke without an explicit comedy performance.')
add([413,520], 'strong_non_comedy_flag', 'Football viewing event; Game Day description explicitly advertises televised games and food/drink specials.')
add([838,839], 'strong_non_comedy_flag', 'Listing bills Swan Lake ballet, including explicit Oregon Ballet Theatre billing.')
add([1047,1052,1055,1056], 'strong_non_comedy_flag', 'Listing bills a ghost/history walking tour without comedy evidence in the API; confirm the actual tour before removal.')
add([282], 'strong_non_comedy_flag', 'Listing bills a paint-and-sip activity.')
add([366], 'strong_non_comedy_flag', 'Description sells mechanical bull rides with a waiver, not a comedy performance.')
add([440,441], 'strong_non_comedy_flag', 'Community meetup or sewing circle, without comedy billing.')
add([661], 'strong_non_comedy_flag', 'Listing bills a dance event without comedy evidence in the API.')
add([1943,1944], 'strong_non_comedy_flag', 'Description advertises a General Hospital actor meet-and-greet, autograph/photo session, dinner or Q&A without comedy billing.')
add([2055], 'strong_non_comedy_flag', 'Title and description bill Gotham Wrestling without comedy billing.')
add([29,774,2020], 'screening_not_live_comedy', 'Movie screening rather than a live comedy performance. A comedy film may still be comedy content; this is a format distinction.')
add([556,1023,2086], 'promotion_or_unavailable_event', 'Holiday party booking promotion or closed-for-private-event notice; unsuitable as a public show listing regardless of genre.')
add([69,70,110,383,434,496,553,559,721,722,724,846,868,925,926,992,1029,1034,1045,1199,1202,1416,1494,1687,1719,2033,2062],
    'class_workshop_or_mixer_review', 'Training/workshop/mixer rather than an obvious audience show. Keep separate from non-comedy: comedy can occur in these activities, and graduation showcases are not included by this rule.')
add([32,98,254,257,258,259,260,325,355,371,431,435,438,442,443,459,460,461,464,568,596,645,656,657,659,660,662,663,665,666,667,671,693,695,706,729,779,860,921,931,956,965,1022,1031,1066,1141,1142,1150,1157,1160,1164,1167,1219,1223,1224,1225,1226,1227,1229,1230,1231,1232,1269,1286,1290,1335,1345,1376,1377,1378,1410,1460,1474,1509,1512,1555,1556,1557,1605,1654,1685,1756,1757,1838,1842,1930,2034],
    'needs_more_evidence', 'Ambiguous or mixed format, sparse description, or a suspected music/social/variety event. No conclusive non-comedy label from this API response.')

entries = []
for g in groups:
    if g['index'] in flags:
        entries.append({**g, **flags[g['index']], 'show_urls':[f'https://www.laugh-track.com/show/{i}' for i in g['ids']]})
counts = collections.Counter()
for e in entries:
    counts[e['assessment']] += e['count']
page_info = []
ids = []
for f in sorted(p.glob('page-*.json')):
    d=json.loads(f.read_text()); ids += [x['id'] for x in d['data']]
    page_info.append({'file': f.name, 'sha256':hashlib.sha256(f.read_bytes()).hexdigest(), 'reported_total':d['total'], 'returned':len(d['data']), 'saved_at_utc':datetime.datetime.fromtimestamp(f.stat().st_mtime,datetime.timezone.utc).isoformat()})
assert len(ids)==len(set(ids))==2886
assert all(x['reported_total']==2886 for x in page_info)
strong_ids={i for x in entries if x['assessment']=='strong_non_comedy_flag' for i in x['ids']}
venues=collections.Counter(x['clubName'] for x in shows if x['id'] in strong_ids)
report={
    'scope':{'endpoint':'https://www.laugh-track.com/api/v1/shows/search', 'params':{'fromDate':'2026-10-11','toDate':'2026-10-17','size':500,'page':'0 through 5','sort':'date_asc'},'authentication':'anonymous','location_filter':None,'timezone_header':None,'unique_shows':len(shows),'unique_venue_title_groups':len(groups),'unique_clubs':len({x['clubId'] for x in shows}),'pagination':page_info},
    'method':'Agent title triage across all 2175 exact venue/title groups, followed by targeted reading of returned descriptions and lineups for suspicious listings. Repeated occurrences grouped for review, counted separately in show totals. No production classifier run and no provider-model API call. These are content audit judgments, not independently verified ground truth.',
    'limitations':['Flags are a conservative triage set, not an exhaustive false-positive rate; remaining listings are not certified comedy.','No description or lineup is not evidence of non-comedy.','Public lineups do not expose blocked identities or parent links, so blocked-only and blocked-only-with-parents rates cannot be calculated from this endpoint.','A non-comedy event at a venue does not establish that comedy never occurs there.','Movie screenings, workshops, mixed variety and drag require separate format decisions; do not blanket exclude them.','Offset pagination is not a transactional snapshot, though all six pages reported the same total and all 2886 IDs were unique.','This assesses published-content precision; cannot measure missed comedy/recall or substitute for the fresh validation required by TASK-4160.','This audit exposes these listings to the agent. Do not subsequently treat these judgments as blind independent validation labels.'],
    'show_counts':dict(counts), 'strong_flag_share':len(strong_ids)/len(shows), 'strong_flag_venue_count':len(venues), 'strong_flags_by_venue':dict(venues.most_common()),
    'missing_description_count':sum(not x.get('description') for x in shows), 'empty_public_lineup_count':sum(not x['lineup'] for x in shows),
    'flags':entries,
    'counterexamples':[{'index':i,'name':groups[i-1]['name'],'description':groups[i-1]['description'],'assessment':'Explicit comedy/improv evidence; keyword-based exclusion would be wrong or overbroad.'} for i in [372,1343,1801,2014,2024]]
}
(p/'audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
lines=['Public shows search content audit: October 11–17, 2026', '',f"Fetched {len(shows)} unique shows from {report['scope']['unique_clubs']} venues; triaged {len(groups)} venue/title groups.", '', 'Counts refer to show occurrences:']
lines += [f'{k}: {v}' for k,v in counts.items()]
lines += ['',f'Strong non-comedy flags: {len(strong_ids)}/{len(shows)} ({100*len(strong_ids)/len(shows):.2f}%), across {len(venues)} venues. This is a flagged share, not a confirmed or exhaustive false-positive rate.','',report['method'],'','Limitations:']+['- '+x for x in report['limitations']]
lines += ['','Flag details (full API descriptions and occurrence IDs in audit.json):']
for e in entries:
    lines += ['',f"{e['assessment']} | {e['count']} occurrence(s) | {e['club']} | {e['name']}",e['reason'],f"IDs: {e['ids']}",f"Ticket URL: {e['url']}"]
(p/'report.txt').write_text('\n'.join(lines))
print(json.dumps({k:report[k] for k in ['show_counts','strong_flag_share','strong_flag_venue_count','strong_flags_by_venue','missing_description_count','empty_public_lineup_count']},indent=2))
