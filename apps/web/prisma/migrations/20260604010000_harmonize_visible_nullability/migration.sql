-- Harmonize the visibility soft-flag nullability across clubs, comedians,
-- and production_companies. production_companies.visible is already
-- BOOLEAN NOT NULL DEFAULT true; clubs.visible and comedians.visible were
-- created as BOOLEAN DEFAULT true (nullable) and are tightened here so all
-- three models share one shape.
--
-- DEFAULT true is honored on every INSERT, and a live audit at the time of
-- this migration reported 0 NULL rows across all three columns. The defensive
-- UPDATE statements still run first so the migration is safe to re-apply
-- against any environment where a NULL might have slipped in (e.g. a legacy
-- branch where DEFAULT was added after rows landed).

UPDATE "clubs"     SET "visible" = true WHERE "visible" IS NULL;
UPDATE "comedians" SET "visible" = true WHERE "visible" IS NULL;

ALTER TABLE "clubs"     ALTER COLUMN "visible" SET NOT NULL;
ALTER TABLE "comedians" ALTER COLUMN "visible" SET NOT NULL;
