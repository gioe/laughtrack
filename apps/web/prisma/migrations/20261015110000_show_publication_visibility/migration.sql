-- Shared soft-suppression substrate for show curation and TASK-4159.
-- Ordered before club intake, whose block projection also suppresses shows.
ALTER TABLE shows ADD COLUMN IF NOT EXISTS visible boolean NOT NULL DEFAULT true;
COMMENT ON COLUMN shows.visible IS 'Publication suppression, independent of source cancellation. False retains saved-show, ticket and audit references.';
