# Sports Drink purchase-confirmation exclusion (TASK-4108)

The Sports Drink OpenDate listing includes an administrative card named
`Thank You For Your Purchase!!!`, pointing to
`https://app.opendate.io/e/thank-you-for-your-purchase-december-31-2099-579525?default_theme=true`.
The September 28 and October 5 captured listings contain this same card. The
preceding TASK-4107 live scrape sent it through persistence, where its 2099 date
failed the shared validator and consequently prevented stale-show reconciliation.

The extractor now excludes this specific URL path and host only when the
normalized title also matches. Query parameters, case, whitespace and trailing
exclamation marks do not affect the match. The check precedes detail-page price
fetching and transformation. Similar titles on other URLs and unrelated
far-future shows remain in the ordinary pipeline.

Regression verification:

```sh
cd apps/scraper
PYTHONPATH=src:. .venv/bin/python3 -m pytest \
  tests/scrapers/implementations/venues/sports_drink \
  tests/utilities/domain/scraper/test_result_processor.py \
  tests/core/entities/show/test_handler_stale_reconciliation.py -q
```

84 tests passed. Four new tests failed before the implementation, demonstrating
119 instead of 118 extracted events and the unwanted detail fetch. The October 5
captured listing now yields exactly the same 118 legitimate title/URL pairs in
the same order. An unrelated 2099 event still fails the 18-month date validator.
The TASK-4107 offline cleanup replay also still verifies 77 retired and 8 held rows.

The full commit gate could not collect tests because the local environment lacks
`tzdata`. `tusk test-precheck --flake-retries 2` reproduced that failure in all
three clean-HEAD runs, with no upstream divergence or flakiness; the documented
path-scoped commit fallback was used.

Live verification on October 5, 2026, 20:10–20:12 UTC used:

```sh
PYTHONPATH=src:. make scrape-club CLUB='Sports Drink'
```

The command exited 0. `live-scrape.txt` preserves relevant log lines and
`live-metrics.json` contains the exported metrics: 118 scraped, 118 saved/updated,
0 inserted, 0 validation failures and 0 database errors. The purchase-confirmation
exclusion is explicitly logged. No persistence-error skip, cap refusal,
reconciliation failure or deletion was logged. The unchanged reconciler returns
silently when its stale count is zero.

Read-only production verification (`post-scrape.json`) found 537 stored shows,
118 future shows, all 118 refreshed by this run, zero stale future Sports Drink
shows and zero rows for placeholder event 579525. The earlier cleanup remains
intact: all 77 retired rows are absent, all 8 held and 28 replacement identities
are preserved, and all 136 retained click records match the recovery snapshot.
No cap override was present: the effective deletion cap remains 10 and the shared
future-date limit remains 18 months. No generic validator or reconciliation code
was changed.
