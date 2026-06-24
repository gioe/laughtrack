# LaughTrack — Project Conventions

Detailed conventions live in the **tusk conventions database**, not inline in this file.
Loading every rule on every conversation wastes context budget on rules that don't
apply to the file you're touching. Conventions are keyed by topic tags so they can
be loaded on demand.

## Discover relevant rules

```bash
tusk conventions inject <path>      # auto-match conventions by file path heuristics
tusk conventions search <term>      # full-text search across body and topics
tusk conventions list --topic <tag> # filter by tag (e.g. prisma, vitest, scraper)
tusk conventions list               # full list, grouped by topic
```

Run `tusk conventions inject <path>` before editing in an unfamiliar area —
it surfaces gotchas, workarounds, and invariants you would otherwise hit the hard way.

## Common topic tags

- **Scraper**: `scraper`, `scraper-chains`, `eventbrite`, `playwright`, `seatengine`,
  `scraping_sources`, `tixr`
- **Prisma / DB**: `prisma`, `migrations`, `neon`, `transactions`, `sql`
- **Frontend**: `frontend`, `nextjs`, `react`, `ssr`, `middleware`, `tailwind`,
  `dev-server`, `routes`, `rate-limit`
- **Testing**: `vitest`, `pytest`, `mocking`, `sys.modules`, `auth`, `happy-dom`
- **Tooling**: `tusk`, `git`, `bash`, `makefile`, `paths`

## Cross-reference files

- `apps/scraper/SCRAPERS.md` — platform-specific venue onboarding guides
  (StageTime, Prekindle, Humanitix, Tixr, Eventbrite, SeatEngine, Squarespace,
  Tockify, OvationTix, OpenDate, TicketSource, etc.)
- `apps/scraper/CONTRIBUTING.md` — scraper testing patterns (smoke tests, module
  loading, mocking, async, VCR cassettes)
- `ios/CLAUDE.md` — native SwiftUI iOS app conventions: simulator test flow
  (`swift test` vs `test_sim`), the iOS 26 HostedView accessibility-tree
  regression and CI sim pin, OpenAPI client regeneration (lockstep with
  `apps/web` `/api/v1` contract), and the ios-libs bridge-target architecture.
  Read this before touching anything under `ios/`.
- `android/README.md` — native Kotlin/Compose Android client conventions: module
  layout (`:core:*` / `:feature:*`), the Hilt API-provider pattern, the OpenAPI
  client regen/drift workflow (`android/bin/regen-openapi.sh`), the
  `MainActivity` auth-callback vs `LaughTrackDeepLink` dispatch, and design-token
  parity with iOS + web. Read this before touching anything under `android/`.

## Adding new conventions

When you learn a non-obvious rule about this codebase — a gotcha, workaround,
invariant, or an incident's root cause — capture it as a tusk convention with
topic tags rather than appending to this file:

```bash
tusk conventions add --topics "tag1,tag2,tag3" "Short, action-oriented rule. \
Why it matters. How to apply it."
```

Use multi-line text for code examples. The body can include fenced code blocks.

## Scraper Configuration Model — quick reminder

Per-platform scrape configuration belongs in `scraping_sources` (keyed by
`(club_id, platform, priority)`), not on `clubs`. Treat `clubs` as venue identity
only. When onboarding or switching a venue, insert/update the appropriate
`scraping_sources` row — do not add new flat scraper config columns to `clubs`.
Run `tusk conventions search scraping_sources` for the full column reference.

## Cross-client parity — quick reminder

LaughTrack has three user-facing clients in this monorepo: **`apps/web`**
(Next.js), **`ios/`** (native SwiftUI), and **`android/`** (native
Kotlin/Compose). They render the same domain (shows, clubs, comedians, podcasts)
through separate UI stacks, so a UX or copy change in one client is **not**
automatically reflected in the others.

When making a user-facing change in one client, check whether the same surface
exists in the other client and decide explicitly:

- **Mirror it** — file or include an equivalent change in the sibling client(s)
  (e.g. TASK-2596 / TASK-2600 fixed web empty-state copy → TASK-2603 mirrored
  it on iOS `ShowsListView`).
- **Skip it with a reason** — the surface doesn't exist there, the other client
  already handles the case, or the platforms have a deliberate UX divergence.
  Capture the reason in the task description or scope note so reviewers don't
  re-investigate.

Same rule for API/contract changes, and it spans **both** native clients: iOS
(`ios/Sources/LaughTrackAPIClient/`) and Android
(`android/core/network/.../generated/`) each consume `apps/web` `/api/v1` through
a generated OpenAPI client, both produced from the single source-of-truth spec at
`ios/Sources/LaughTrackAPIClient/openapi.json`. Any `/api/v1` edit must ship
**both** regenerated clients in lockstep in the same PR (convention #220) — see
`ios/CLAUDE.md` for the iOS recipe and `android/README.md` for the Android
`regen-openapi.sh` / drift-check workflow.
