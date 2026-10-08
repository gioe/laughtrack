# TASK-4143 production verification

Applied the committed reviewed plan on 2026-10-08; independently verified at
19:25:58 UTC. Criteria 13489 and 13490 share this execution/preservation record.

- Removed exactly 36 reviewed musical shows, 36 tickets and 29 tag relations.
- Preserved all 287 historical shows and their relationships, including 10
  comedy lineup entries. Venue fields are unchanged except total_shows=287.
- Source 77 remains disabled with every field unchanged.
- Preserved all 1,726 click records, clearing only the 134 retiring show links.
  The 32 previously detached venue clicks and all other click fields are unchanged.
- Fresh database snapshot exactly equals the planned after-image. Repeating the
  repair reports already_applied without modifying rows. No upcoming active
  shows remain for club 88.
- Public API before: 36 exact reviewed IDs. After: HTTP 200, data=[], total=0 at
  https://www.laugh-track.com/api/v1/clubs/88/shows?size=100&verification=4143
  (Vercel cache MISS). The original URL initially returned its cached response;
  response headers advertise public max-age=60.

Private recovery files (0600, verified) remain on the operator machine:
`/private/tmp/task4143-production-backup.json` and the complete recovery image
`/private/tmp/task4143-production-backup.json.after.json`. Do not commit these
files: they contain private row data. Recovery from the scraper directory:

```sh
PYTHONPATH=src:. .venv/bin/python scripts/archive/retire_barrel_room_noncomedy_2026_10_08.py --plan docs/audits/2026-10-08-barrel-room-noncomedy/reviewed-plan.json --restore /private/tmp/task4143-production-backup.json.after.json
```

Recovery refuses any schema or affected after-image drift. A transaction-only
production rehearsal performed cleanup, repeat, and exact restoration before
rolling back; the actual committed repair was not restored.

Validation: 42 focused PostgreSQL tests passed (18 new cleanup tests plus source
disable and identity repair regressions). The full commit gate is blocked by
pre-existing missing tzdata during collection; clean HEAD reproduced it 3/3
times without upstream divergence. The documented raw, path-limited commit
recovery was used. No claim of full-suite success is made.
