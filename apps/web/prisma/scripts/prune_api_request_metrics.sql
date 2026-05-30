-- Retention/cleanup for the api_request_metrics counter table.
--
-- The table is bucketed (one row per route_pattern × method × status_class ×
-- hour), so it grows slowly — but unbounded over time. This script deletes
-- buckets older than the retention window so the table stays bounded.
--
-- Retention window: 90 days. The Grafana API-request dashboard looks back at
-- most a few weeks; 90 days leaves comfortable headroom for month-over-month
-- comparisons. Widen/narrow by editing the interval below.
--
-- Idempotent and safe to re-run. Intended to run on a schedule — e.g. a daily
-- Vercel Cron / GitHub Actions step, or a Neon scheduled query:
--   psql "$DIRECT_URL" -f prisma/scripts/prune_api_request_metrics.sql
--
-- The hour_bucket index (api_request_metrics_hour_bucket_idx) makes the range
-- delete cheap.
DELETE FROM public.api_request_metrics
WHERE hour_bucket < NOW() - INTERVAL '90 days';
