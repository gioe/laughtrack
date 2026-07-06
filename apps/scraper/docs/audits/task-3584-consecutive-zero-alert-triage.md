# TASK-3584 Consecutive-Zero Alert Triage

Live Neon audit time: 2026-07-06.

## Summary

- Current `mv_scraper_health_consecutive_zero`: 105 firing clubs before the TASK-3584 retune.
- Root cause: 92 of 105 firing clubs have no current future shows in LaughTrack and no recent failure/bot-block signal; these are mostly one-off aggregate listings aging out or filtering to zero, not scraper failures.
- Retuned view validation and live apply: 13 firing clubs remain, 26 total rows including one-extra-run recovery retention.
- The retune keeps clubs whose latest/previous run failed, latest/previous run detected a bot block, or persisted future shows still exist while the scraper returns zero.

## Classification Counts

- `alert_noise_clean_zero_inventory_aged_out`: 91
- `alert_noise_filtered_zero_inventory_no_future`: 1
- `real_regression_future_inventory_still_present`: 8
- `real_regression_recent_failure`: 3
- `real_regression_bot_block`: 2

## Source Breakdown

| Primary source | Classification | Clubs |
|---|---:|---:|
| `ticketmaster:ticketmaster_comedy` | `alert_noise_clean_zero_inventory_aged_out` | 40 |
| `eventbrite:eventbrite` | `alert_noise_clean_zero_inventory_aged_out` | 37 |
| `ticketmaster:ticketmaster_comedy` | `real_regression_future_inventory_still_present` | 4 |
| `custom:json_ld` | `alert_noise_clean_zero_inventory_aged_out` | 3 |
| `squarespace:squarespace` | `alert_noise_clean_zero_inventory_aged_out` | 3 |
| `crowdwork:crowdwork` | `alert_noise_clean_zero_inventory_aged_out` | 1 |
| `custom:aeg_axs` | `alert_noise_clean_zero_inventory_aged_out` | 1 |
| `custom:barclays_center` | `alert_noise_clean_zero_inventory_aged_out` | 1 |
| `custom:comedy_clubhouse` | `real_regression_bot_block` | 1 |
| `custom:comedy_magic_club` | `alert_noise_clean_zero_inventory_aged_out` | 1 |
| `custom:improv_asylum` | `real_regression_recent_failure` | 1 |
| `custom:kellars` | `real_regression_future_inventory_still_present` | 1 |
| `custom:seetickets_whitelabel` | `real_regression_recent_failure` | 1 |
| `custom:sports_drink` | `real_regression_recent_failure` | 1 |
| `custom:the_auricle` | `alert_noise_clean_zero_inventory_aged_out` | 1 |
| `custom:tks_comedy` | `alert_noise_clean_zero_inventory_aged_out` | 1 |
| `custom:tock` | `real_regression_bot_block` | 1 |
| `etix:etix` | `real_regression_future_inventory_still_present` | 1 |
| `ninkashi:ninkashi` | `real_regression_future_inventory_still_present` | 1 |
| `seatengine:seatengine` | `alert_noise_clean_zero_inventory_aged_out` | 1 |
| `seatengine:seatengine_classic` | `real_regression_future_inventory_still_present` | 1 |
| `shopify:shopify` | `alert_noise_clean_zero_inventory_aged_out` | 1 |
| `ticketmaster:live_nation` | `alert_noise_filtered_zero_inventory_no_future` | 1 |

## Retune

The migration `apps/scraper/migrations/20260706174000_retune_consecutive_zero_health_alert.sql` recreates only `mv_scraper_health_consecutive_zero`.

It was applied to Neon after dry-run confirmed it was the only pending scraper
migration. The post-apply live check returned `rows = 26`, `firing = 13`.

The new condition still requires:

- latest and previous full scraper runs both returned zero shows, and
- the club had positive output in the trailing 30-day scraper/verify history.

It additionally requires at least one active regression signal:

- latest or previous run failed,
- latest or previous run detected a bot block, or
- the `shows` table still has future shows for the club.

## Row-Level Output

See `apps/scraper/docs/audits/task-3584-consecutive-zero-alert-triage.csv` for the per-club breakdown.
