# TASK-3519 — Decision: how comedy-branded Eventbrite organizer clubs surface their shows

**Date:** 2026-06-29
**Type:** product + data-model decision (no code shipped in this task).
**Origin:** TASK-3511 dry-source triage + convention #292 (eventbrite organizer feeds are
dry-by-design; each event routes to its own per-venue club).

## Decision

**Option (c): accept the split.** The per-event venue club is the canonical home for an
Eventbrite organizer feed's routed shows; the organizer feed-club does **not** also surface
them. No data-model change.

## Why (the problem is already largely handled)

Investigation showed the system already implements the split correctly through two existing
mechanisms, so the "comedy-brand club appears empty in the UI" risk is minimal:

1. **Active high-volume routing organizers are already `visible=false`.** The organizer
   feed-clubs whose events route to *distinct* venue clubs are already hidden:
   - Comedy Oakland (11089), Gold Coast Comedy Club (11449), The Spotlight Comedy (11081),
     The Comedy Bar - Pittsburgh (8708), BATS Improv (11133) — all `visible=false`, 0 own
     upcoming shows. Their shows live on the venue clubs they route to (e.g. Gold Coast →
     Bokampers Sports Bar & Grill (11450) + Ovivi's Restaurant (11451)), which **are**
     browsable and carry the comedy lineup.

2. **Browse already requires an upcoming show.** `apps/web/lib/data/club/search/
   findClubsWithCount.tsx` filters `visible: true AND shows: { some: { date: { gt: now } } }`.
   So a `visible=true` organizer club with 0 upcoming shows **never appears in browse** — it
   is only reachable by a direct `/club/<slug>` URL, where it would render an empty state.

Of the 60 enabled eventbrite `/o/` organizer clubs: 32 have their own upcoming shows (events
happen at the organizer's own venue → fine); 28 have 0 own upcoming shows; 13 of those 28 are
`visible=true`. The 13 are **real low-volume comedy venues** (Comedy on Collins 200, The Drop
Comedy Club 9065, Pagliacci's Comedy Club 8701, Lots of Laughs Comedy Lounge 10950,
Chatterbox 8855, Bobby's Place Night Club 10951, McCues Comedy Club 10959, Blend Comedy
10960, Martinez Campbell Theater 11104, Clayton Club Saloon 11105, Deja Blue 11119, Music
City Starfactory 11121, CBA Event Center 11251) — **not** pure feed placeholders. They
correctly stay visible and will appear in browse when their own feed has upcoming shows. Per
the owner's keep-rule, real venues are kept.

## Why not (a) or (b)

- **(a) Surface routed shows on the organizer page** — would require new persistence linking
  an organizer *club* to its routed venue clubs (today only the curated `production_companies`
  set carries `eventbrite_organizer_venues` rows; the organizer *clubs* do not), and would
  duplicate each show across two club pages. High effort for a problem already mitigated by
  `visible=false` + the browse filter. Rejected.
- **(b) Reclassify organizers as producers/chains** — semantically cleaner but overlaps what
  `visible=false` already achieves, and needs aggregation UI work. Disproportionate for a
  Low-priority concern. Rejected.

## Affected organizer club IDs

- Already-hidden routing organizers (working as intended): **11089, 11449, 11081, 8708,
  11133**.
- Real venues kept visible (populate when their feed has upcoming shows): **200, 9065, 8701,
  10950, 8855, 10951, 10959, 10960, 11104, 11105, 11119, 11121, 11251**.

## Follow-up

Captured as **TASK-3522** — "Guard: keep show-routing eventbrite organizer feed-clubs
visible=false": a small audit/guard that flags any organizer feed-club routing 100% of its
shows to distinct venue clubs but still `visible=true`, and sets it hidden, while leaving
genuine organizer-venue clubs visible. This makes the invariant durable for future onboards.
The decision itself requires no migration today (no club is currently mis-configured).
