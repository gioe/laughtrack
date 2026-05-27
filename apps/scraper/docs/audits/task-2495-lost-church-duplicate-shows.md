# TASK-2495: The Lost Church (club 1047) PatronTicket duplicate-show cleanup

Date: 2026-05-27
Club: The Lost Church, club 1047 (San Francisco, timezone America/Los_Angeles)
Scraper: generic `patron_ticket` (legacy rows tagged `lost_church`)
Follow-up to: [task-2485-patronticket-duplicate-shows.md](task-2485-patronticket-duplicate-shows.md)
(the club-187 cleanup) and TASK-2494 (instance-id dedup prevention, already merged)

## Summary

Same defect as club 187: a single PatronTicket performance (one Salesforce `#/instances/<id>`)
was stored as multiple `shows` rows because the start time changed between scrapes and the
`shows` unique key `@@unique([club_id, date, room])` includes the full timestamp, so the upsert's
`ON CONFLICT (club_id, date, room)` missed the existing row and inserted a near-duplicate. Root
cause and the chosen fix (match on the stable instance id) are documented in the club-187 audit;
TASK-2494 shipped that instance-id reconciliation for both the generic `patron_ticket` scraper and
the bespoke `up_comedy_club`, so this cleanup will **not** regenerate.

The time drift here is larger than club 187's 30 min — the legacy `lost_church` rows sit 7 h later
in UTC than the current `patron_ticket` rows (a timezone-handling difference between the old and new
scrapers), but the dedup defect and the remediation are identical.

## 1. Quantification

Instance id = the `#/instances/<id>` fragment of `show_page_url` / `purchase_url`. A duplicate is
two+ `shows` rows for one club sharing one instance id.

Before cleanup, club 1047 had **42 shows across 24 distinct instances → 18 stale rows**:

- 16 instances are duplicated: **14 pairs + 2 triples**.
  - Triple 1 — `a0FUh000006z5k5MAA` (Jenny Zigrino): the show was postponed then re-dated; the
    current row is "NEW DATE: Jenny Zigrino" on 2026-10-18 (id 1400541, scraped 2026-05-27).
  - Triple 2 — `a0FTU00000Mnu612AB` ("The Setup", 2026-05-03): three rows at 02:00 / 03:00 / 10:00 UTC.
- The remaining 8 instances are singletons and were left untouched.

## 2. Stale-vs-current decision

Per the club-187 procedure and the task guidance ("most-recently-scraped is the live one"), for each
duplicated instance we **keep the row with the max `last_scraped_date`** and delete the rest. The kept
rows for every upcoming show were refreshed by `patron_ticket` on 2026-05-27 (the live source as of
this date); kept rows for past shows carry the most recent scrape on record. The 18 stale rows are all
older `lost_church`/null-scraper rows or superseded postpone/re-date rows.

18 stale `shows` ids to delete:

```
916707, 916708, 916709, 916710, 916711, 916712, 916713, 916714, 916715, 916716,
916717, 916718, 916719, 916720, 916721, 916722, 935096, 935103
```

## 3. Referential safety

The 18 stale rows carry, by cascade (`shows.id` FKs are all `ON DELETE CASCADE`:
tickets, tagged_shows, lineup_items, sent_notifications, ticket_purchase_click_events):

| Child table | Rows on stale shows | Coverage check |
|---|---|---|
| tickets | 18 | All $0 "General Admission" placeholder tickets — no purchase data |
| tagged_shows | 49 | **No coverage lost** — for every instance, the kept row's tag set is an equal-or-superset of the stale rows' tags (verified per-instance) |
| lineup_items | 10 | All comedians except one are already on the kept row |
| sent_notifications | 0 | — |
| ticket_purchase_click_events | 0 | — |

The single comedian dropped is Spencer Bland (`58c3e00b103ced091cd42be0b86c259d`) on instance
`a0FUh000007gsMXMAY`: the stale row is "Will Abeles + Spencer Bland", the current row is
"Will Abeles + Hannah Roeschlein". This is a genuine source lineup change, so dropping the stale
Spencer-Bland link is correct, not data loss.

## 4. Remediation

Deleted the 18 stale rows; cascade removed their 18 tickets, 49 tagged_shows, and 10 lineup_items.

Post-cleanup: club 1047 has **24 shows = 24 distinct instances, 0 duplicates.**

### Recovery snapshot

Full pre-deletion snapshot of the 18 shows + their tickets + tagged_shows + lineup_items, for restore
if needed. Captured 2026-05-27 before deletion. Restore order: shows → tickets → tagged_shows → lineup_items.

```sql
-- Recovery snapshot for TASK-2495: 18 stale The Lost Church (club 1047) duplicate shows

INSERT INTO shows (id, name, date, show_page_url, club_id, popularity, last_scraped_date, description, room, production_company_id, last_scraped_by, min_price) VALUES
  (916707, 'The Setup', '2026-05-03 10:00:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FTU00000Mnu612AB', 1047, 0, '2026-04-08 16:17:56.250492+00', '', '', NULL, NULL, NULL),
  (916710, 'Improv at UCSF 2026 Show!', '2026-04-19 10:15:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000006z0hBMAQ', 1047, 0, '2026-04-08 16:17:56.250503+00', '', '', NULL, NULL, NULL),
  (916712, 'Jamel Johnson: Big Baller Comedy Tour', '2026-04-27 10:15:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000006w1gDMAQ', 1047, 0, '2026-04-08 16:17:56.250505+00', '', '', NULL, NULL, NULL),
  (916713, 'The Muslims are Coming!...with Equally Threatening Friends! A Comedy Show.', '2026-04-30 10:15:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007ZQ3dMAG', 1047, 0, '2026-04-08 16:17:56.250506+00', '', '', NULL, NULL, NULL),
  (916715, 'Brown Noise - A Kinda Brown Comedy Show', '2026-05-08 10:15:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007ubGzMAI', 1047, 0, '2026-04-08 16:17:56.250509+00', '', '', NULL, NULL, NULL),
  (916708, 'The Setup', '2026-06-07 10:00:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FTU00000Mnu9F2AR', 1047, 0, '2026-04-08 16:17:56.250501+00', '', '', NULL, 'lost_church', NULL),
  (916709, 'The Setup', '2026-07-05 10:00:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FTU00000MnuHJ2AZ', 1047, 0, '2026-04-08 16:17:56.250502+00', '', '', NULL, 'lost_church', NULL),
  (916716, '“Am I the A*hole?” - Standup Comedy Settling YOUR Disputes', '2026-05-24 10:15:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007WAmbMAG', 1047, 0, '2026-04-08 16:17:56.25051+00', '', '', NULL, 'lost_church', NULL),
  (916720, 'Chrissa Sparkles', '2026-06-29 10:15:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007ucL7MAI', 1047, 0, '2026-04-08 16:17:56.250521+00', '', '', NULL, 'lost_church', NULL),
  (916714, 'Jenny Zigrino', '2026-05-02 10:15:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000006z5k5MAA', 1047, 0.12042, '2026-04-08 16:17:56.250508+00', '', '', NULL, NULL, NULL),
  (916719, 'Gus Johnson, Ryan Leader, Sean Dolan', '2026-06-28 09:30:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007ck7RMAQ', 1047, 0.066, '2026-04-08 16:17:56.250513+00', '', '', NULL, 'lost_church', NULL),
  (935096, 'The Setup', '2026-05-03 03:00:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FTU00000Mnu612AB', 1047, 0, '2026-04-27 07:45:42.932602+00', '', '', NULL, NULL, NULL),
  (916721, 'Sunny Laprade & Emma Dalenberg', '2026-07-09 10:15:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007ooVRMAY', 1047, 0.34672267963506564, '2026-04-08 16:17:56.250522+00', '', '', NULL, 'lost_church', NULL),
  (916722, 'Ahmed Al-kadri Live in SF!', '2026-09-28 10:15:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000006zT85MAE', 1047, 0.12150000000000001, '2026-04-08 16:17:56.250523+00', '', '', NULL, 'lost_church', NULL),
  (935103, 'POSTPONED Jenny Zigrino', '2026-05-02 03:15:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000006z5k5MAA', 1047, 0.12042, '2026-04-29 07:07:38.64834+00', '', '', NULL, NULL, NULL),
  (916717, 'The Maestro of Comedy - Armando Anto', '2026-05-30 10:00:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FTU00000GmdCL2AZ', 1047, 0.12, '2026-04-08 16:17:56.250511+00', '', '', NULL, 'lost_church', NULL),
  (916718, 'Will Abeles + Spencer Bland', '2026-06-27 09:30:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007gsMXMAY', 1047, 0.2743914320815447, '2026-04-08 16:17:56.250512+00', '', '', NULL, 'lost_church', NULL),
  (916711, 'Abbas Wahab LIVE Dialed-In Tour', '2026-04-25 09:30:00+00', 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FTU00000MqhnN2AR', 1047, 0.12, '2026-04-08 16:17:56.250504+00', '', '', NULL, NULL, NULL);

INSERT INTO tickets (id, purchase_url, price, sold_out, show_id, type) VALUES
  (853564, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FTU00000Mnu612AB', 0.00, 't', 916707, 'General Admission'),
  (853565, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FTU00000Mnu9F2AR', 0.00, 't', 916708, 'General Admission'),
  (853566, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FTU00000MnuHJ2AZ', 0.00, 't', 916709, 'General Admission'),
  (853567, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000006z0hBMAQ', 0.00, 'f', 916710, 'General Admission'),
  (853568, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FTU00000MqhnN2AR', 0.00, 'f', 916711, 'General Admission'),
  (853569, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000006w1gDMAQ', 0.00, 'f', 916712, 'General Admission'),
  (853570, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007ZQ3dMAG', 0.00, 'f', 916713, 'General Admission'),
  (853571, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000006z5k5MAA', 0.00, 'f', 916714, 'General Admission'),
  (853572, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007ubGzMAI', 0.00, 'f', 916715, 'General Admission'),
  (853573, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007WAmbMAG', 0.00, 'f', 916716, 'General Admission'),
  (853574, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FTU00000GmdCL2AZ', 0.00, 'f', 916717, 'General Admission'),
  (853575, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007gsMXMAY', 0.00, 'f', 916718, 'General Admission'),
  (853576, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007ck7RMAQ', 0.00, 'f', 916719, 'General Admission'),
  (853577, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007ucL7MAI', 0.00, 'f', 916720, 'General Admission'),
  (853578, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000007ooVRMAY', 0.00, 'f', 916721, 'General Admission'),
  (853579, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000006zT85MAE', 0.00, 'f', 916722, 'General Admission'),
  (872644, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FTU00000Mnu612AB', 0.00, 't', 935096, 'General Admission'),
  (872651, 'https://thelostchurch.my.salesforce-sites.com/ticket/#/instances/a0FUh000006z5k5MAA', 0.00, 't', 935103, 'General Admission');

INSERT INTO tagged_shows (id, show_id, tag_id) VALUES
  (1809176, 916707, 9), (1809147, 916707, 1083),
  (1809177, 916708, 9), (1809148, 916708, 1083),
  (1809178, 916709, 9), (1809149, 916709, 1083),
  (1809179, 916710, 9), (1809174, 916710, 16), (1809150, 916710, 1083), (1809171, 916710, 1194),
  (1809180, 916711, 9), (1809169, 916711, 953), (1809151, 916711, 1083),
  (1809181, 916712, 9), (1809164, 916712, 1043), (1809152, 916712, 1083),
  (1809182, 916713, 9), (1809165, 916713, 1043), (1809153, 916713, 1083), (1809172, 916713, 1194),
  (1809183, 916714, 9), (1809154, 916714, 1083),
  (1809184, 916715, 9), (1809166, 916715, 1043), (1809155, 916715, 1083), (1809173, 916715, 1194),
  (1809185, 916716, 9), (1809167, 916716, 1043), (1809156, 916716, 1083), (1809175, 916716, 1217),
  (1809186, 916717, 9), (1809168, 916717, 1043), (1809157, 916717, 1083),
  (1809187, 916718, 9), (1809158, 916718, 1083),
  (1809188, 916719, 9), (1809159, 916719, 1083),
  (1809189, 916720, 9), (1809160, 916720, 1083),
  (1809190, 916721, 9), (1809161, 916721, 1083),
  (1809191, 916722, 9), (1809170, 916722, 953), (1809162, 916722, 1083), (1809163, 916722, 8225),
  (1846832, 935096, 9), (1846799, 935096, 1083),
  (1846839, 935103, 9), (1846806, 935103, 1083);

INSERT INTO lineup_items (id, show_id, comedian_id, role) VALUES
  (118260, 916711, '9122752e355da4edf44b3222dcded9b5', NULL),
  (118261, 916714, '1d1b4063512ccb7bef2012d63b2ca235', NULL),
  (118262, 916717, 'a63f2807f010a72dd1bab3154a91d872', NULL),
  (118263, 916718, '58c3e00b103ced091cd42be0b86c259d', NULL),
  (118264, 916718, 'fae699e954ebbf56f0ee676728de88d8', NULL),
  (118265, 916719, '3c3b7eadb9f613f0f7642e784303cd18', NULL),
  (118267, 916721, 'e4a903a687976613513f64c6e643b818', NULL),
  (118266, 916721, 'ebc85984fb919cd81464aa736ccf26f8', NULL),
  (118268, 916722, '5d33832f8674907a8c91425510b6ac00', NULL),
  (119764, 935103, '1d1b4063512ccb7bef2012d63b2ca235', NULL);
```
