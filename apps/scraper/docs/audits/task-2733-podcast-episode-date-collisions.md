# TASK-2733 Podcast Episode Date Collisions

## YMH correction

Podcast `5407` (`Your Mom's House with Christina P. and Tom Segura`) had 77
numbered historical episodes in one weak collision group:

- `release_date`: `2016-10-17T00:00:00+00:00`
- normalized title: `your mom's house with christina pazsitzky and tom segura`
- distinct GUIDs: 77
- distinct audio URLs: 77

The current FeedBurner RSS feed and PodcastIndex feed listing only go back to
episode 185, so they cannot correct episodes 104-183. PodcastIndex `byguid`
also returns the stale `2016-10-17` date for those rows. Archived FeedBurner
snapshots in Wayback still contain the original Libsyn item `pubDate` values.

`scripts/core/backfill_ymh_episode_dates_from_wayback.py --confirm` matched all
77 affected numbered rows by episode number against archived feed items and
updated those row IDs only. Each updated row now carries
`evidence.ymh_wayback_release_date_backfill` with the archive snapshot timestamp
and archived title used.

Post-backfill verification for podcast `5407` shows no remaining
normalized-title/date collision groups.

## Remaining weak groups

After the YMH backfill, the remaining weak normalized-title/date groups are all
two-row groups with distinct GUIDs and distinct audio URLs:

| podcast_id | podcast | release_date | notes |
| --- | --- | --- | --- |
| 1805 | Respectfully | `2024-05-31T23:07:00+00:00` | `32 - ...` and `#32 - ...` have different hosts/CDN URLs; left as distinct source rows. |
| 2395 | Music History Today Network | `2022-01-14T09:00:00+00:00` | Case-only title variant but different Anchor play IDs and audio files; left as distinct source rows. |
| 5391 | Wealth On Main Street | `2026-04-09T13:14:54+00:00` | Same episode number/title with different Castos episode IDs/audio files; left as distinct source rows. |
| 7067 | Steve Martin and Edie Brickell: Meet the Musicians | `2013-05-03T02:00:00+00:00` | US and WW media variants for `ep2.m4a`; intentional regional variants. |
| 7067 | Steve Martin and Edie Brickell: Meet the Musicians | `2013-05-03T02:01:00+00:00` | US and WW media variants for `ep1.m4v`; intentional regional variants. |
| 8635 | Ones Ready | `2022-10-22T05:00:00+00:00` | Prefix/no-prefix title variant with different Buzzsprout episode IDs/audio files; left as distinct source rows. |

No remaining group has the YMH failure shape of many different numbered episodes
collapsed onto one stale date.
