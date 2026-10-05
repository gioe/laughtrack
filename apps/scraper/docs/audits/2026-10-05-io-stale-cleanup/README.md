# TASK-4105: iO Theater bounded stale-performance cleanup

Fresh inspection on October 5, 2026 revalidated all 42 IDs from TASK-4063.
The native scraper HTTP stack returned 80 Crowdwork listings; its Playwright
browser retrieved all 13 affected event pages. The complete sanitized feed,
page dates and descriptions, database identities, and per-ID decisions are
hash-locked by manifest.json. Raw HTML and credentials are not committed.

29 future performances remain absent from both the complete feed and their
public pages: 18 Orbit occurrences, 10 individual omitted dates, and the old
This Year in Music date. This establishes delisting/schedule changes, not an
assertion that the venue explicitly canceled them. The This Year in Music
replacement, row 1044696 on December 11, remains present in source and storage.

13 IDs are held:

- 1863553, 480646 and 3736581 are now past. Retain historical rows; 3736581
  also remains the explicit missing People Being Funny replacement hold.
- 480692, Flex Improv: the description still lists 11/05 at 7:30pm even though
  the feed and date selector omit it. The conflict is unresolved.
- 3736583–3736585, 3767701 and 4880163: five more People Being Funny source-listed
  earlier-time replacements are now missing from storage. Retain these rows
  under the same replacement-preservation rule and TASK-4106 identity work.
- 2084643, 3013099, 4282370 and 5600935: the original Mystery Movie Club IDs now
  contain Battleprov. Their URL/title/freshness changed; never delete by ID alone.

The runtime reconciliation cap remains 10. No scraper runtime logic or source
configuration changes are part of this task. TASK-4106 owns simultaneous-event
identity repair. All 13 held IDs have explicit reasons in decisions.json.

Offline evidence verification (from apps/scraper):

```sh
PYTHONPATH=src:. .venv/bin/python3 docs/audits/2026-10-05-io-stale-cleanup/replay.py
```
