# Optional event comedy enrichment

The deterministic classifier and staging gate work without OpenAI. Both optional
model controls default off. Normal scraping never calls a model, needs no API
key, and does not read model cache tables when cache consumption is disabled.

The separate enrichment command examines staged deterministic `review` events.
It snapshots source policy and relevant canonical-parent/deny state, closes its
transaction, then requests a bounded structured decision. It never writes shows,
comedians or lineups. A later scrape may consume a matching validated cache entry
through the existing policy and publication fence.

Enable enrichment with `COMEDY_MODEL_ENABLED=1`. Independently enable cached
result consumption with `COMEDY_MODEL_CACHE_ENABLED=1`. Turning consumption off
immediately returns subsequent scrapes to deterministic decisions; this does not
delete cache entries or previously published shows. Changing policy, event data,
identity/block state, classifier, prompt/schema, model/provider or output-token
limit invalidates the matching cache key.

Configure `COMEDY_MODEL_PROVIDER=openai`, an explicit `COMEDY_MODEL_NAME`, and
`OPENAI_API_KEY` for enrichment only. Supply verified model prices in
`COMEDY_MODEL_INPUT_USD_PER_MILLION` and
`COMEDY_MODEL_OUTPUT_USD_PER_MILLION`; no price or paid model is guessed. Cache
consumption requires the same model configuration but neither API key nor prices.
After deploying the optional cache migration, run from `apps/scraper`:

```sh
.venv/bin/python -m scripts.core.enrich_comedy_eligibility --limit 25
```

`--candidate-id ID` narrows one candidate. The command is not automatically
scheduled by scraping. Source modes `off` and disabled sources are excluded.
Missing configuration, cache failures and provider failures retain review.

Bounds are configurable: `COMEDY_MODEL_TIMEOUT_SECONDS` (15),
`COMEDY_MODEL_RETRIES` (0, at most 2), `COMEDY_MODEL_MAX_INPUT_CHARS` (12000),
`COMEDY_MODEL_MAX_OUTPUT_TOKENS` (400), `COMEDY_MODEL_MAX_COST_MICROS` (10000),
`COMEDY_MODEL_DAILY_BUDGET_MICROS` (1000000),
`COMEDY_MODEL_DAILY_REQUEST_LIMIT` (100), and `COMEDY_MODEL_CONCURRENCY` (2).
Costs use integer millionths of a US dollar. Each attempt reserves its maximum
before calling; failures retain that charge, and retries reserve again. A
conservative UTF-8 input-token bound plus output cap must fit the reservation
before any request. Pricing configuration must match the selected model. The
provider uses a cancellable total deadline, bounded response size, no redirect
following and no hidden retries. The database coordinates reservations and
leases across workers; expired attempts remain charged.

Responses use the [OpenAI strict structured-output contract](https://developers.openai.com/api/docs/guides/structured-outputs).
Only event title and description are sent as untrusted data; tools and external
knowledge are unavailable. Exact cited passages must also contain explicit
performance billing. Unsupported statements, instructions, negation, conflicting
programming, biographies and unresolved blocked/identity conflicts stay review.
Deterministic accepts/rejects cannot be overturned. This conservative validation
may abstain on genuine comedy described indirectly; confidence is a rule score,
not measured model accuracy. Synthetic contract tests prove mechanics only.

No live model evaluation was run, at the user's explicit request. False
acceptance, false rejection, abstention and actual provider cost are unmeasured.
The feature remains optional and disabled; a later evaluation can measure those
rates without changing the normal scraping dependency.
