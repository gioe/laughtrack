# TASK-2485: PatronTicket duplicate shows (start-time drift defeats dedup)

Date: 2026-05-27
Club: UP Comedy Club, club 187 (Second City Chicago, timezone America/Chicago)
Follow-up to: [task-2468-up-comedy-salesforce-ticket-path.md](task-2468-up-comedy-salesforce-ticket-path.md)
(the "26-of-190 reused instance id" out-of-scope observation)

## Summary

A single PatronTicket performance (one Salesforce instance id, e.g.
`#/instances/a0FTP000004XeKY2A0`) was stored as **two** `shows` rows on the same date,
30–60 min apart. The venue moved a recurring show's start time and our `shows` unique key
`@@unique([club_id, date, room])` includes the full timestamp, so the upsert's
`ON CONFLICT (club_id, date, room)` did not match the existing row — it inserted a near-duplicate
instead of updating. The old-time row then lingers forever (no reaper covers future shows).

## 1. Quantification

Instance id = the `#/instances/<18-char id>` fragment of `show_page_url` / `purchase_url`.
A duplicate is two+ `shows` rows for one club sharing one instance id.

Across all Salesforce-Sites / PatronTicket venues:

| Club | Venue | Scraper | Shows | Distinct instances | Duplicate rows |
|---|---|---|---|---|---|
| 187 | UP Comedy Club | `up_comedy_club` (bespoke) | 190 | 164 | **26** |
| 1047 | The Lost Church | `patron_ticket` (generic) | 42 | 24 | **18** |
| 2368 | Reilly Arts Center | `patron_ticket` | 2 | 2 | 0 |
| 3289 | Marion Theatre | `patron_ticket` | 10 | 10 | 0 |

Club 187: every duplicated instance is exactly a **pair** — 0 rows have a missing instance id.
In each pair, the older row (id ~`481xxx`, `last_scraped_date = 2026-03-30`) sits at **15:00
local** and the newer row (id ~`535xxx`, `last_scraped_date = 2026-05-27`) sits at **15:30 local**:

```
instance              old (15:00)            new (15:30)
a0FTP000004XeKY2A0    481928 07-11 15:00     535489 07-11 15:30
a0FTP000004XeKT2A0    481913 06-06 15:00     535474 06-06 15:30
... (26 pairs total)
```

The Lost Church (club 1047) shows the same shape on the **generic** `patron_ticket` scraper,
so this is a PatronTicket-platform issue, not specific to the bespoke `up_comedy_club` scraper.

## 2. Root cause and match strategy

### Why the duplicate appears

1. The PatronTicket source identifies a performance by a stable Salesforce **instance id**
   (the `#/instances/<id>` fragment), **not** by start time. The start time is mutable.
2. The venue changed the show's start time. Confirmed against the live source on 2026-05-27 —
   every `Best of The Second City` instance now reports `formattedDates.ISO8601 = ...T20:30:00Z`
   with the human label "at 3:30 PM" (was 3:00 PM / `T20:00:00Z` at the 2026-03-30 scrape, and
   still 3:00 PM when TASK-2468 sampled it on 2026-05-26).
3. The scraper faithfully converts the new UTC instant to a new `date` (15:30 local). The
   `shows` unique key `@@unique([club_id, date, room])` includes the timestamp, so
   `ON CONFLICT (club_id, date, room)` (see `sql/show_queries.py` `BATCH_INSERT_SHOWS`) finds no
   match at 15:30 and **inserts** a second row rather than updating the 15:00 row.
4. Nothing removes the stale 15:00 row. `DELETE_ORPHANED_SHOWS` only deletes lineup-less shows
   `date < CURRENT_DATE - INTERVAL '30 days'`; these are future shows, so they are never reaped.

The "30 minutes apart" in the task title is just the size of this particular reschedule — the
defect is general to any start-time change for a PatronTicket instance.

### Decided strategy: match on the stable instance id

The correct match key is the **PatronTicket instance id**, not the start time:

- **Dedup on instance id (chosen).** When a PatronTicket-family scraper re-emits a show whose
  `#/instances/<id>` already exists for the club, update that row's `date` in place instead of
  inserting. This survives reschedules and is the only key the source treats as identity.
- **Normalize / snap start time (rejected).** The time genuinely changed (3:00→3:30 PM); snapping
  would either be too coarse (collapse legitimately distinct showtimes) or too fine (not catch a
  30–60 min move), and would silently hide real schedule changes.

Implementing instance-id reconciliation touches the shared show-upsert path and affects every
PatronTicket venue (and the generic `patron_ticket` scraper used by club 1047), so it is tracked
as a separate follow-up rather than done inline with this club-187 cleanup.

### Adjacent source-data bug (noted, not fixed here)

The source's `ISO8601` is itself DST-naive: it reports a fixed `T20:30:00Z` for every instance
while its own label always says "3:30 PM". For dates after the Nov 1 2026 DST change that fixed
UTC instant converts to **2:30 PM** local, disagreeing with the label by one hour (e.g. instance
`a0FTP000004XeKp2AK`, Sat Nov 7). Trusting the human label over `ISO8601` would correct this;
tracked as a follow-up.

## 3. Remediation (club 187)

Deleted the 26 stale `481xxx` rows (the older row of each pair — `last_scraped_date` below the
per-instance max), keeping the 26 current `535xxx` rows that reflect the live 3:30 PM source.

Referential safety before deletion: the 26 stale rows had 26 tickets (cascade), 52 `tagged_shows`,
0 `lineup_items`, 0 `sent_notifications`. The 26 surviving rows already carry identical tag
coverage (tag ids 9 and 1083, 52 rows), so no tag coverage is lost. Cascade deletes the stale
rows' tickets and tags automatically (`onDelete: Cascade`).

Post-cleanup: club 187 has 164 shows = 164 distinct instances, 0 duplicates.

### Recovery snapshot

Full pre-deletion snapshot of the 26 shows + their tickets + tagged_shows, for restore if needed:

```sql
-- Recovery snapshot for TASK-2485: 26 stale UP Comedy Club (club 187) duplicate shows
-- Captured 2026-05-27 before deletion. Restore order: shows -> tickets -> tagged_shows.

INSERT INTO shows (id, name, date, show_page_url, club_id, popularity, last_scraped_date, description, room, production_company_id, last_scraped_by, min_price) VALUES
  (481943, 'Best of The Second City', '2026-08-15T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKd2AK', 187, 0.12, '2026-03-30T06:40:26.114489+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481934, 'Best of The Second City', '2026-07-25T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKa2AK', 187, 0.12, '2026-03-30T06:40:26.114479+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481957, 'Best of The Second City', '2026-09-19T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKi2AK', 187, 0.12, '2026-03-30T06:40:29.649123+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481937, 'Best of The Second City', '2026-08-01T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKb2AK', 187, 0.12, '2026-03-30T06:40:26.114482+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481963, 'Best of The Second City', '2026-10-10T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKl2AK', 187, 0.12, '2026-03-30T06:40:29.64913+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481967, 'Best of The Second City', '2026-10-24T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKn2AK', 187, 0.12, '2026-03-30T06:40:29.649135+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481940, 'Best of The Second City', '2026-08-08T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKc2AK', 187, 0.12, '2026-03-30T06:40:26.114486+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481965, 'Best of The Second City', '2026-10-17T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKm2AK', 187, 0.12, '2026-03-30T06:40:29.649133+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481969, 'Best of The Second City', '2026-10-31T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKo2AK', 187, 0.12, '2026-03-30T06:40:29.649137+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481946, 'Best of The Second City', '2026-08-22T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKe2AK', 187, 0.12, '2026-03-30T06:40:26.114493+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481931, 'Best of The Second City', '2026-07-18T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKZ2A0', 187, 0.12, '2026-03-30T06:40:26.114476+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481973, 'Best of The Second City', '2026-11-14T21:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKq2AK', 187, 0.12, '2026-03-30T06:40:29.649141+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481925, 'Best of The Second City', '2026-07-04T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKX2A0', 187, 0.12, '2026-03-30T06:40:26.11447+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481952, 'Best of The Second City', '2026-09-05T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKg2AK', 187, 0.12, '2026-03-30T06:40:29.649117+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481922, 'Best of The Second City', '2026-06-27T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKW2A0', 187, 0.12, '2026-03-30T06:40:26.114465+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481959, 'Best of The Second City', '2026-09-26T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKj2AK', 187, 0.12, '2026-03-30T06:40:29.649125+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481926, 'Best of The Second City', '2026-07-05T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKz2AK', 187, 0.12, '2026-03-30T06:40:26.114471+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481928, 'Best of The Second City', '2026-07-11T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKY2A0', 187, 0.12, '2026-03-30T06:40:26.114473+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481971, 'Best of The Second City', '2026-11-07T21:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKp2AK', 187, 0.12, '2026-03-30T06:40:29.649139+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481975, 'Best of The Second City', '2026-11-21T21:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKr2AK', 187, 0.12, '2026-03-30T06:40:29.649144+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481913, 'Best of The Second City', '2026-06-06T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKT2A0', 187, 0.12, '2026-03-30T06:40:26.114455+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481949, 'Best of The Second City', '2026-08-29T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKf2AK', 187, 0.12, '2026-03-30T06:40:29.649113+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481916, 'Best of The Second City', '2026-06-13T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKU2A0', 187, 0.12, '2026-03-30T06:40:26.114459+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481919, 'Best of The Second City', '2026-06-20T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKV2A0', 187, 0.12, '2026-03-30T06:40:26.114462+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481955, 'Best of The Second City', '2026-09-12T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKh2AK', 187, 0.12, '2026-03-30T06:40:29.649121+00:00', '', '', NULL, 'up_comedy_club', NULL),
  (481961, 'Best of The Second City', '2026-10-03T20:00:00+00:00', 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKk2AK', 187, 0.12, '2026-03-30T06:40:29.649128+00:00', '', '', NULL, 'up_comedy_club', NULL);

INSERT INTO tickets (id, purchase_url, price, sold_out, show_id, type) VALUES
  (413953, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKd2AK', 0.0, FALSE, 481943, 'General Admission'),
  (413944, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKa2AK', 0.0, FALSE, 481934, 'General Admission'),
  (413967, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKi2AK', 0.0, FALSE, 481957, 'General Admission'),
  (413947, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKb2AK', 0.0, FALSE, 481937, 'General Admission'),
  (413973, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKl2AK', 0.0, FALSE, 481963, 'General Admission'),
  (413977, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKn2AK', 0.0, FALSE, 481967, 'General Admission'),
  (413950, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKc2AK', 0.0, FALSE, 481940, 'General Admission'),
  (413975, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKm2AK', 0.0, FALSE, 481965, 'General Admission'),
  (413979, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKo2AK', 0.0, FALSE, 481969, 'General Admission'),
  (413956, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKe2AK', 0.0, FALSE, 481946, 'General Admission'),
  (413941, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKZ2A0', 0.0, FALSE, 481931, 'General Admission'),
  (413983, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKq2AK', 0.0, FALSE, 481973, 'General Admission'),
  (413935, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKX2A0', 0.0, FALSE, 481925, 'General Admission'),
  (413962, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKg2AK', 0.0, FALSE, 481952, 'General Admission'),
  (413932, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKW2A0', 0.0, FALSE, 481922, 'General Admission'),
  (413969, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKj2AK', 0.0, FALSE, 481959, 'General Admission'),
  (413936, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKz2AK', 0.0, FALSE, 481926, 'General Admission'),
  (413938, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKY2A0', 0.0, FALSE, 481928, 'General Admission'),
  (413981, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKp2AK', 0.0, FALSE, 481971, 'General Admission'),
  (413985, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKr2AK', 0.0, FALSE, 481975, 'General Admission'),
  (413923, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKT2A0', 0.0, FALSE, 481913, 'General Admission'),
  (413959, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKf2AK', 0.0, FALSE, 481949, 'General Admission'),
  (413926, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKU2A0', 0.0, FALSE, 481916, 'General Admission'),
  (413929, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKV2A0', 0.0, FALSE, 481919, 'General Admission'),
  (413965, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKh2AK', 0.0, FALSE, 481955, 'General Admission'),
  (413971, 'https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKk2AK', 0.0, FALSE, 481961, 'General Admission');

INSERT INTO tagged_shows (id, show_id, tag_id) VALUES
  (860173, 481943, 9), (860073, 481943, 1083),
  (860164, 481934, 9), (860064, 481934, 1083),
  (860237, 481957, 9), (860187, 481957, 1083),
  (860167, 481937, 9), (860067, 481937, 1083),
  (860243, 481963, 9), (860193, 481963, 1083),
  (860247, 481967, 9), (860197, 481967, 1083),
  (860170, 481940, 9), (860070, 481940, 1083),
  (860245, 481965, 9), (860195, 481965, 1083),
  (860249, 481969, 9), (860199, 481969, 1083),
  (860226, 481946, 9), (860176, 481946, 1083),
  (860161, 481931, 9), (860061, 481931, 1083),
  (860253, 481973, 9), (860203, 481973, 1083),
  (860155, 481925, 9), (860055, 481925, 1083),
  (860232, 481952, 9), (860182, 481952, 1083),
  (860152, 481922, 9), (860052, 481922, 1083),
  (860239, 481959, 9), (860189, 481959, 1083),
  (860156, 481926, 9), (860056, 481926, 1083),
  (860158, 481928, 9), (860058, 481928, 1083),
  (860251, 481971, 9), (860201, 481971, 1083),
  (860255, 481975, 9), (860205, 481975, 1083),
  (860143, 481913, 9), (860043, 481913, 1083),
  (860229, 481949, 9), (860179, 481949, 1083),
  (860146, 481916, 9), (860046, 481916, 1083),
  (860149, 481919, 9), (860049, 481919, 1083),
  (860235, 481955, 9), (860185, 481955, 1083),
  (860241, 481961, 9), (860191, 481961, 1083);
```

## Follow-ups

- **Instance-id reconciliation in the PatronTicket upsert path** — match an existing show by
  `(club_id, instance id)` and update its `date` in place, so reschedules update rather than
  duplicate. Affects the generic `patron_ticket` scraper and the bespoke `up_comedy_club`.
- **Clean up club 1047 (The Lost Church)** — 18 duplicate rows of the same shape, on the generic
  `patron_ticket` scraper.
- **DST-naive source `ISO8601`** — for post-DST dates the source's fixed `T20:30:00Z` is one hour
  off its own "3:30 PM" label; consider trusting the label over `ISO8601` in the scraper.
