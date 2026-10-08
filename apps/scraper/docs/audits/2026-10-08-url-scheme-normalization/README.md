# TASK-4138 — Mixed-case HTTP scheme verification

`URLUtils.normalize_url` now recognizes HTTP and HTTPS case-insensitively and
lowercases only the scheme. Authority, path, query, fragment and percent-encoding
case remain intact. Existing schemeless and trailing-slash behavior is preserved.

## Reproduction and tests

Before the fix, `Http://www.deafpuppyclub.com` normalized to
`https://Http://www.deafpuppyclub.com`, whose hostname is `http`.
The new regression file produced **11 failures and 7 passes** before the fix.
Afterward, **197 tests passed** across:

```sh
PYTHONPATH=src .venv/bin/python3 -m pytest tests/foundation/test_url_scheme_normalization.py tests/foundation/infrastructure/http/test_client.py tests/scripts/test_audit_club_source_geo.py -q
```

The 18 new tests cover mixed/lowercase schemes, case-sensitive URL contents,
schemeless and empty inputs, both trailing-slash modes, and the URL passed to
the native HTTP session. Pyflakes passed for the helper and regression file.

The full scraper gate stopped during collection because `tzdata` is missing.
Three clean-HEAD precheck runs reproduced the same failure, with
`pre_existing=true`, `flaky_suspect=false`, and `diverged_from_default=false`.
The documented recovery used path-limited Git commits. The typed regression
criterion also executed successfully through Tusk; the full suite did not pass.

## Native read-only verification

[live-verification.json](live-verification.json) records the October 8 live run.
The existing `seatengine.geo.resolve_venue("531", timeout=90)` path fetched the
native venue API, then passed its exact mixed-case website value to the shared
HTTP client. An observing wrapper around `curl_cffi.requests.AsyncSession.get`
recorded URL, status, final URL, response length and digest without changing
request arguments or recording authorization headers.

- API response: HTTP 200, exact website `Http://www.deafpuppyclub.com`.
- Website request: `http://www.deafpuppyclub.com`, HTTP 200 after redirect to
  `https://www.deafpuppyclub.com/`; no request to hostname `Http`.
- Resolver outcome: `missing_metadata / no_eventvenue_jsonld`. Fetchability is
  repaired; this result does not establish a postal identity or authorize a
  geography correction.

Before and after the resolver call, a PostgreSQL connection configured with
`default_transaction_read_only=on` read full `to_jsonb` rows for club 551 and
source 594. Both rows were equal. The source remains enabled with SeatEngine
venue 531 and its original mixed-case source URL; the club remains visible.
No scraper persistence or database mutation was performed. Private full rows
were compared in memory and were not published. This proves equality at the
observation points, not absence of unrelated intervening writes.
