# Public search development corpus v1

This archive preserves the original anonymous October 11–17, 2026 show-search
capture: **2,886 public show occurrences, 2,175 exact venue/title groups and 702
clubs**. The six `raw/page-*.json` files are the original bytes. `manifest.json`
records their SHA-256 digests, request parameters and original recorded file-save
times. No replacement search was substituted.

File-save times are local filesystem modification times retained by the original
audit, not HTTP response timestamps or request duration measurements. Requests
had no location filter or timezone header. The date parameters retain the API's
default date semantics; they do not establish seven complete venue-local days.
Offset pagination is not transactional. Consistent totals and unique IDs detect
some inconsistencies but cannot prove that inventory did not change mid-capture.

`triage/` preserves the original agent audit and its construction inputs separately
from reference labels. Its 56 strong flags are hypotheses, not gold labels or an
estimate of all false positives. Unflagged listings are not certified comedy.
`groups.json` retained only the first description and lineup per venue/title;
the corpus loader instead retains every occurrence's original evidence.

`labels.json` records an explicit agent review of flagged occurrences and varied
comedy controls. Labels keep genre, event format and public availability separate;
insufficient evidence remains unknown. This is exposed development data, not
independent validation for TASK-4160. `mappings.json` records later read-only
database identity evidence, with its own capture time. Missing or ambiguous
source attribution stays unresolved. Public show IDs are never native event IDs.
Public lineups do not reveal blocked performers or their canonical parents.

The reproducible baseline is **observed public publication**: every archived show
was returned by search. It does not replay an ingestion policy, infer why a show
was published, or execute proposed rules. Venue branding and price/format tags
remain contextual data and are not promoted into event genre evidence. Rule
evaluation and before/after metrics belong to subsequent tasks.

From `apps/scraper`, validate and summarize the immutable inputs offline:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/core/comedy_search_corpus.py
```

The command uses only local files and makes no database writes, network requests
or model calls. A changed input requires a new reviewed corpus version rather
than silently regenerating this baseline.
