-- Per-API-route request counter, bucketed by the hour. The composite primary
-- key (route_pattern, method, status_class, hour_bucket) is the ON CONFLICT
-- target for the counter UPSERT performed by the withRequestMetrics wrapper,
-- so a busy route is a handful of rows per hour instead of one row per request.
CREATE TABLE "api_request_metrics" (
    "route_pattern" TEXT NOT NULL,
    "method" TEXT NOT NULL,
    "status_class" TEXT NOT NULL,
    "hour_bucket" TIMESTAMPTZ NOT NULL,
    "count" INTEGER NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "api_request_metrics_pkey" PRIMARY KEY ("route_pattern", "method", "status_class", "hour_bucket")
);

-- Supports retention deletes and the time-series dashboard panels.
CREATE INDEX "api_request_metrics_hour_bucket_idx" ON "api_request_metrics"("hour_bucket");
-- Supports the per-route-over-time panel.
CREATE INDEX "api_request_metrics_route_pattern_hour_bucket_idx" ON "api_request_metrics"("route_pattern", "hour_bucket");
