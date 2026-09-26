-- TASK-4054: Tock loads locally but GitHub Actions direct egress receives
-- Cloudflare challenges. The existing solver needs matching proxy egress.
INSERT INTO scrapers (key, use_residential_proxy, notes, updated_at)
VALUES (
    'tock', true,
    'TASK-4054: Tock business pages block GitHub Actions direct egress; use the shared residential proxy and Cloudflare fallback.',
    CURRENT_TIMESTAMP
)
ON CONFLICT (key) DO UPDATE
SET use_residential_proxy = true,
    updated_at = CURRENT_TIMESTAMP
WHERE scrapers.use_residential_proxy = false;
