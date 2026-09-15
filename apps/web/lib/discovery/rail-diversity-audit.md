# Discover overlap audit — TASK-4000

These are deterministic representative candidate fixtures, not a production traffic measurement. Reproduce with the bounded feed candidate selection cases in railSelector.test.ts and the dense payload integration case in the home feed route tests.

## Dense candidate pool

Tonight has shows 1–8, each with a different featured performer. This Week has those same eight followed by eight other eligible shows, 21–28. Limited Time has show 31 featuring Tonight performer 1 and show 32 featuring visitor 40. Momentum has show 41 featuring visitor 40 and show 42 featuring performer 50. Limits are eight for the time rails and one for the two small illustrative dynamic rails.

| Rail | Before (provider truncation + exact ID removal) | After |
| --- | --- | --- |
| Tonight | 1–8 | 1–8 |
| This Week | empty: first eight all removed | 21–28 |
| Limited Time | 31: repeats Tonight performer 1 | 32: distinct eligible visitor 40 |
| Momentum | 41: repeats visitor 40 selected above | 42: distinct eligible performer 50 |

The earlier policy rail retains priority. The later rail chooses from its own eligible candidates, never from an unrelated rail. For the before fixture, Momentum performer 40 is distinct from the visitor actually displayed before; its change after selection prevents the new overlap with visitor 40. Across the entire fixture, repeated featured-performer exposures fall from one to zero while This Week gains eight useful shows. Exact show duplicates are zero in both versions; the benefit is avoiding an empty rail and repeated faces.

## Sparse candidate pool

Each of the four rails has only shows 1 and 2, with two distinct featured performers, each independently satisfying that rail's eligibility. Previously Tonight retained both and the three later rails disappeared. Now all four retain their two eligible matches. Six repeated show/performer exposures are intentional fallback: the time window, visiting-performer evidence, and momentum evidence answer different questions. The selector never adds filler, fabricates urgency, or duplicates an item within a rail.

## Ordered-feed inspection

Tonight remains chronological and useful for immediate plans. This Week can reach eligible later dates beyond the Tonight overlap. Limited Time retains verified scarcity and unique canonical visitors even in candidate mode. Momentum retains its evidence threshold, reason, and provider score order among selected items. Personalized rails use only their existing followed/podcast matches. Candidate selection preserves provider order; it changes membership, not the ranking signals or rail policy order.

The cap remains eight in response payloads. Candidates are bounded at fifty. Soft preferences prioritize a new show with a new featured performer, then a new show with a repeated performer, then a repeated show only when the eligible pool cannot fill the rail. Canonical featured identity is used; incidental supporting lineup members do not suppress shows. This is a backend feed change; native clients continue resolving the existing rail-plan item IDs.
