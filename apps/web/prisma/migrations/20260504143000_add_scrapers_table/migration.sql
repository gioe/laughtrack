-- Per-scraper runtime configuration. The Python scraper loads
-- use_residential_proxy=TRUE rows once at process startup so operators can
-- flip a venue's proxy bit via plain SQL without a redeploy.
--
-- Seed list: 5 platforms that pilot validation (TASK-1892, 2026-05-04)
-- showed are blocked by IP-level WAFs (Vercel + Cloudflare classes) and
-- clear when routed through a residential proxy.

-- CreateTable
CREATE TABLE "scrapers" (
    "key" TEXT NOT NULL,
    "use_residential_proxy" BOOLEAN NOT NULL DEFAULT false,
    "notes" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL,

    CONSTRAINT "scrapers_pkey" PRIMARY KEY ("key")
);

-- CreateIndex
CREATE INDEX "scrapers_use_residential_proxy_idx" ON "scrapers"("use_residential_proxy");

-- Seed: 5 platforms blocked by IP-level WAFs (TASK-1892 pilot, 2026-05-04)
INSERT INTO "scrapers" ("key", "use_residential_proxy", "notes", "updated_at") VALUES
    ('comedy_mothership', true, 'Vercel WAF — pilot validated 2026-05-04 (200 + 850KB)', CURRENT_TIMESTAMP),
    ('comedy_clubhouse', true, 'Vercel WAF — same hosting class as comedy_mothership', CURRENT_TIMESTAMP),
    ('palm_beach_improv', true, 'Vercel WAF — onboarded post-merge from worktree branch', CURRENT_TIMESTAMP),
    ('ticketweb', true, 'Cloudflare WAF on storefront pages', CURRENT_TIMESTAMP),
    ('tixr', true, 'Cloudflare WAF on storefront pages', CURRENT_TIMESTAMP);
