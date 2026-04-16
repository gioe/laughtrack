-- [TASK-1480] Onboard Laff House as first production company
--
-- Laff House is a comedy production company that produces shows at
-- The Lounge at World Stage (3025 Walnut St, Philadelphia, PA).
-- This is the first real-world test of the production company data model.
--
-- The venue sells tickets through Etix (venue_id=26727). The generic
-- etix scraper handles it with no Python changes.
--
-- Charlotte NC and Raleigh NC venues have no Etix listings yet —
-- they can be added later when events go on sale.

-- Step 1: Insert The Lounge at World Stage as a venue club
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Lounge at World Stage') THEN
        INSERT INTO clubs (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, country
        )
        VALUES (
            'The Lounge at World Stage',
            '3025 Walnut St, Philadelphia, PA 19104',
            'https://worldcafelive.org',
            'https://www.etix.com/ticket/v/26727/the-lounge-at-world-stage',
            'etix',
            true,
            '19104',
            'America/New_York',
            'Philadelphia',
            'PA',
            'US'
        );
    END IF;
END $$;

-- Step 2: Insert Laff House as a production company
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM production_companies WHERE slug = 'laff-house') THEN
        INSERT INTO production_companies (name, slug, website, scraping_url, visible)
        VALUES (
            'Laff House',
            'laff-house',
            'https://laffhousecomedyclub.com',
            'https://www.etix.com/ticket/v/26727/the-lounge-at-world-stage',
            true
        );
    END IF;
END $$;

-- Step 3: Link Laff House to The Lounge at World Stage via join table
DO $$
DECLARE
    v_club_id INTEGER;
    v_pc_id INTEGER;
BEGIN
    SELECT id INTO v_club_id FROM clubs WHERE name = 'The Lounge at World Stage';
    SELECT id INTO v_pc_id FROM production_companies WHERE slug = 'laff-house';

    IF v_club_id IS NOT NULL AND v_pc_id IS NOT NULL THEN
        INSERT INTO production_company_venues (production_company_id, club_id)
        VALUES (v_pc_id, v_club_id)
        ON CONFLICT DO NOTHING;
    END IF;
END $$;
