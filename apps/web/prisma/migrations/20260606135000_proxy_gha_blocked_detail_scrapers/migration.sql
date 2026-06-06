-- TASK-2688: GitHub Actions direct egress is now blocked by the venue WAFs
-- backing Flappers, McCurdy's, and The Stand's venue-owned public-card pages.
-- Local scraper runs still succeed with curl-cffi fingerprinting, so route
-- these scraper keys through the existing residential proxy allowlist rather
-- than changing venue parsers.

INSERT INTO scrapers (key, use_residential_proxy, notes, updated_at)
VALUES
    (
        'flappers',
        true,
        'Cloudflare/WAF blocks GitHub Actions on calendar and detail PHP pages; proxy validated by TASK-2688 investigation',
        CURRENT_TIMESTAMP
    ),
    (
        'mccurdys_comedy_theatre',
        true,
        'ColdFusion listing/detail pages return HTTP 403 from GitHub Actions direct egress; proxy via TASK-2688',
        CURRENT_TIMESTAMP
    ),
    (
        'tixr_public_card',
        true,
        'The Stand venue-owned public-card pages return HTTP 403 from GitHub Actions direct egress; proxy via TASK-2688',
        CURRENT_TIMESTAMP
    )
ON CONFLICT (key) DO UPDATE
SET use_residential_proxy = EXCLUDED.use_residential_proxy,
    notes = EXCLUDED.notes,
    updated_at = CURRENT_TIMESTAMP;
