# Live verification — 2026-10-05

After the guarded cleanup committed, ran the actual scraper with worktree-local
imports (the shared venv's editable install otherwise points at the primary checkout):

```sh
PYTHONPATH=src:. make scrape-club CLUB='Big Pine Comedy Festival'
```

The October 5 19:38 EDT run fetched SeatEngine venue 553 successfully (HTTP 200,
1/1 successful targets), received 17 native products, excluded all 17, and produced
zero performance shows. Final diagnostics reported `items_before_filter=17`, no
bot block, no fetch failure. The run key was `scraper:2026-10-05T19:38:05.018390`.

This is a valid all-filtered result, not a clean empty upstream calendar. The
unchanged reconciliation predicate rejects zero-show results with nonzero
pre-filter inventory. No bypass flag, empty-feed override, or deletion-cap change
was used. Positive regression fixtures retain genuine festival performances and
admission passes; unrelated SeatEngine sources have no title exclusions.

A fresh read-only database comparison after the scrape matched **every** cleanup
after-image exactly: 53 held shows, 55 tickets, 8 lineup relationships, 110 tags,
all 1,063 click records (417 with detached show references), club fields, all three
protected source rows, and both source targets. None of the 19 audited IDs remained
or was recreated. No alternate-ID insertion occurred: the complete show-row set
and before/after field comparison matched.

Focused validation: 46 tests passed across SeatEngine and the real PostgreSQL
cleanup tests. The full commit gate stopped during collection because the shared
venv lacks `tzdata`; clean-HEAD precheck reproduced the same error on all three
attempts, with no upstream divergence and no flake. This is an environment
limitation, not a passing full-suite claim.
