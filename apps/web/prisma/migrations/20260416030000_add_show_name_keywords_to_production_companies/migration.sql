-- Add show_name_keywords column to production_companies.
-- When non-empty, only shows whose name matches at least one keyword
-- get stamped with the production_company_id during scraping.
-- When empty (default), all shows are stamped (backwards-compatible).
ALTER TABLE production_companies
  ADD COLUMN show_name_keywords text[] NOT NULL DEFAULT '{}';

-- Populate Laff House (id=1) with comedy-related keywords so music
-- events at shared venues are excluded from production company tagging.
UPDATE production_companies
SET show_name_keywords = ARRAY[
  'comedy', 'stand-up', 'standup', 'stand up',
  'comedian', 'comic', 'laugh', 'laff',
  'open mic', 'open-mic', 'improv', 'roast',
  'funny', 'humor', 'jokes'
]
WHERE id = 1;
