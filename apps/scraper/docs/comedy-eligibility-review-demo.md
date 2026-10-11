## Mixed-programming review demonstration

This synthetic demonstration represents the Harvelle's problem: a venue can
host both music and comedy. It makes no claim about actual Harvelle's events and
does not connect to production or call a model API.

Run from `apps/scraper`:

```sh
PYTHONPATH=src:. .venv/bin/python3 -m pytest \
  tests/integration/test_comedy_eligibility_review_demo.py -q -s
```

The fixture uses one enabled, mixed-programming source in enforcement mode:

| Event | Supplied evidence | Operator action | Next normal scrape |
| --- | --- | --- | --- |
| Blue Room Sessions | Description bills an instrumental blues concert | Reject with reason | Still withheld |
| Friday Late Set | Description bills stand-up; blocked alias resolves to visible parent 102 | Approve with reason | Published through `ShowHandler.insert_shows` |
| Stand-up comedy showcase | Explicit comedy billing | None | Remains published |

The demonstration invokes the real CLI `main()` for inspect, preview, and apply,
with the real `ReviewStore`. It confirms the preview has not applied the action,
retries each apply with the same idempotency key, and checks there are still only
two attributed review records. Applying a review creates no public shows. New
scrape deliveries go through the real eligibility gate and normal show-handler
dispatch; repeated comedy delivery does not create a duplicate public show.

The source policy, enabled state, and identity visibility remain unchanged. The
blocked alias stays blocked and linked to its visible parent. The music decision
does not suppress the unrelated comedy event at the same venue.

Executed result:

```json
{
  "comedy": "parent 102 resolved; approved and published through normal handler",
  "fixture": "synthetic Harvelle's-style mixed programming",
  "identity_visibility": "unchanged",
  "music": "rejected and still withheld on next scrape",
  "production_writes": 0,
  "public_events": 2,
  "review_actions": 2,
  "review_apply_public_writes": 0,
  "source_policy": "unchanged",
  "unrelated_event": "still published without duplicate"
}
```

The command passed: **1 passed**. Database I/O, staging persistence, and the
physical public writer are isolated memory doubles. This demonstrates application
behavior; it does not claim to verify PostgreSQL durability, locking, or production
publication. The separate PGlite migration suite covers SQL constraints and writes.
