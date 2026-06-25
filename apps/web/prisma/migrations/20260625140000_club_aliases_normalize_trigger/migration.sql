-- Make club_aliases.normalized_* a DB single-source-of-truth (TASK-3462).
--
-- Background: the alias-routing dedup key was normalized in two independent
-- places — an inline SQL expression in each fold script (writer) and a Python
-- helper in the scraper's club handler (reader). TASK-3458 was caused by those
-- two copies drifting (the Python side expanded 'St.' -> 'saint', the SQL side
-- did not), so an alias for a 'St./Ft./Mt.' venue silently failed to match and
-- the importer re-created the duplicate it was meant to fold.
--
-- This collapses the contract to ONE definition in the database:
--   * lt_normalize_alias_key(text) — the canonical name/city normalization.
--   * a BEFORE INSERT/UPDATE trigger that fills normalized_alias_name /
--     normalized_city / normalized_state from alias_name / city / state, so no
--     writer can store a mismatched value (the columns are not user-supplied).
--   * the reader (scraper) compares against the stored columns using the same
--     function (see GET_CLUBS_BY_LOCATION.alias_matches_candidate), so there is
--     no second normalization to drift from.
--
-- We use a trigger rather than a GENERATED ALWAYS ... STORED column because
-- Prisma 6.5 does not represent generated-column expressions in schema.prisma
-- and would fight the migration with drift-correction. The trigger pattern is
-- the project's established convention for DB-maintained derived columns
-- (cf. shows.min_price / tickets_trickle_show_min_price). The normalized_*
-- columns stay plain String fields in schema.prisma.

-- Canonical normalization: lower-case, '&' -> ' and ', collapse every
-- non-alphanumeric run to a single space, trim. IMMUTABLE so it is usable in
-- index/where expressions and (future) generated columns. Deliberately does
-- NOT expand 'st'/'ft'/'mt' abbreviations — the stored keys never did, and
-- expanding here is exactly the drift TASK-3458 fixed.
CREATE OR REPLACE FUNCTION lt_normalize_alias_key(p_value TEXT)
RETURNS TEXT AS $$
    SELECT btrim(
        regexp_replace(
            replace(lower(COALESCE(p_value, '')), '&', ' and '),
            '[^a-z0-9]+', ' ', 'g'
        )
    );
$$ LANGUAGE sql IMMUTABLE;

-- Dedup redundant alias rows BEFORE the trigger/backfill recompute their keys.
-- Existing data holds pairs that differ only in punctuation ("City Winery
-- St. Louis" vs "City Winery - St. Louis"; a "Funny Bone Comedy Club - X" stub
-- alias plus the TASK-3321 fold alias) which collapse to the SAME normalized key
-- under lt_normalize_alias_key. Recomputing them would violate the unique index
-- (normalized_alias_name, normalized_city, normalized_state) and abort the
-- migration (this is exactly the P3009 failure observed on the first prod
-- deploy). Each colliding pair points at the SAME club_id, so the extra row is
-- a pure redundant duplicate — delete all but the lowest id per recomputed key.
-- The club_id = guard means we only ever drop a same-club duplicate; a
-- collision between DIFFERENT clubs is left in place so it fails loudly and a
-- human resolves it rather than the migration silently mis-routing a club.
DELETE FROM club_aliases a
USING club_aliases b
WHERE b.id < a.id
  AND b.club_id = a.club_id
  AND lt_normalize_alias_key(b.alias_name) = lt_normalize_alias_key(a.alias_name)
  AND lt_normalize_alias_key(b.city) = lt_normalize_alias_key(a.city)
  AND lower(COALESCE(b.state, '')) = lower(COALESCE(a.state, ''));

-- Keep club_aliases.normalized_* in lockstep with alias_name/city/state on
-- every write, regardless of which client (fold script, scraper, ad-hoc SQL)
-- performed it. normalized_state mirrors the historical lower(state) form.
CREATE OR REPLACE FUNCTION club_aliases_set_normalized()
RETURNS TRIGGER AS $$
BEGIN
    NEW.normalized_alias_name := lt_normalize_alias_key(NEW.alias_name);
    NEW.normalized_city := lt_normalize_alias_key(NEW.city);
    NEW.normalized_state := lower(COALESCE(NEW.state, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS club_aliases_set_normalized ON club_aliases;

CREATE TRIGGER club_aliases_set_normalized
BEFORE INSERT OR UPDATE ON club_aliases
FOR EACH ROW
EXECUTE FUNCTION club_aliases_set_normalized();

-- One-shot backfill so existing rows are guaranteed to match the function.
-- The dedup step above removed the same-key/same-club duplicates that would
-- otherwise collide here, so every recomputed key is now unique under
-- (normalized_alias_name, normalized_city, normalized_state). The IS DISTINCT
-- FROM guard limits the write to rows whose key actually changes.
UPDATE club_aliases
SET normalized_alias_name = lt_normalize_alias_key(alias_name),
    normalized_city = lt_normalize_alias_key(city),
    normalized_state = lower(COALESCE(state, ''))
WHERE normalized_alias_name IS DISTINCT FROM lt_normalize_alias_key(alias_name)
   OR normalized_city IS DISTINCT FROM lt_normalize_alias_key(city)
   OR normalized_state IS DISTINCT FROM lower(COALESCE(state, ''));
