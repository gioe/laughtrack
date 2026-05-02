# Zero-Upcoming Clubs Audit

Snapshot date: 2026-05-01

This folder tracks active, visible clubs that currently have zero upcoming shows in the database (`shows.date >= NOW()`). Each club gets its own reference note so investigation findings, source behavior, and the eventual decision stay easy to review. Handled entries are struck through.

## Query

```sql
SELECT c.id, c.name, COALESCE(c.city, ''), COALESCE(c.state, ''), MAX(s.date) AS last_show
FROM clubs c
LEFT JOIN shows s ON s.club_id = c.id
WHERE c.visible IS TRUE
  AND c.status = 'active'
GROUP BY c.id, c.name, c.city, c.state
HAVING COUNT(*) FILTER (WHERE s.date >= NOW()) = 0
ORDER BY c.name;
```

## Clubs

| ID | Club | Location | Last show | Reference |
|---:|---|---|---|---|
| ~~190~~ | ~~CIC Theater~~ | ~~Chicago, IL~~ | ~~never~~ | [handled: custom scraper](cic-theater.md) |
| ~~329~~ | ~~Carolina Comedy Club~~ |  | ~~never~~ | handled: closed |
| 520 | Comedy Club at The Park | Richmond, VA | never | pending |
| 200 | Comedy on Collins | Miami Beach, FL | never | pending |
| ~~21~~ | ~~Comic Strip Live~~ | ~~New York, NY~~ | ~~2026-04-25~~ | handled: updated Eventbrite organizer source |
| ~~583~~ | ~~Cultural Center for the Arts with Krackpots Comedy Club~~ | ~~Canton, OH~~ | ~~never~~ | handled: hidden |
| ~~1527~~ | ~~Dry Bar Comedy  [Deactivated]~~ |  | ~~never~~ | handled: hidden |
| ~~642~~ | ~~Encore Comedy - Kentucky~~ |  | ~~never~~ | handled: hidden; follow-up TASK-1891 |
| ~~640~~ | ~~Encore Comedy - Maryland~~ |  | ~~never~~ | handled: hidden; follow-up TASK-1891 |
| ~~639~~ | ~~Encore Comedy - Virginia~~ |  | ~~2026-04-26~~ | handled: hidden; follow-up TASK-1891 |
| ~~574~~ | ~~Go Bananas Comedy Club~~ |  | ~~never~~ | handled: custom scraper |
| 602 | Laugh And Enjoy | West Chicago, IL | never | pending |
| 589 | Midtown Comedy Lounge | El Paso, TX | never | pending |
| 196 | Nashville Improv | Nashville, TN | 2026-04-11 | pending |
| 1474 | Omaha Improv Festival (Shows) |  | never | pending |
| 379 | Palm Beach Improv |  | never | pending |
| 12 | Rodney's | New York, NY | 2026-04-18 | pending |
| 16 | St. Marks Comedy Club | New York, NY | 2026-04-26 | pending |
| 456 | SuperNova Comedy | Los Angeles, CA | never | pending |
| 568 | The Brick Room | Noblesville, Indiana | never | pending |
| 1438 | The Comedy Scene |  | never | pending |
| 60 | The Comedy Zone - Cherokee | Cherokee, NC | 2026-02-04 | pending |
| 518 | The Port Comedy Club |  | never | pending |
| 521 | The Royal Comedy Theatre |  | never | pending |
| 660 | The Setup Chicago | Chicago, IL | never | pending |
| 661 | The Setup Vancouver | Vancouver, BC | 2026-04-25 | pending |
| 5 | The Stand | New York, NY | 2026-04-25 | pending |
| 1059 | West River Comedy Club | Rapid City, SD | never | pending |
| 636 | Wicked Funny Comedy Club Danvers |  | 2026-04-13 | pending |
| 586 | Wiseguys - Westgate |  | never | pending |
| 448 | Wiseguys Las Vegas |  | never | pending |
