-- Denormalized cheapest *paid* ticket price per show. Lets shows search
-- ORDER BY price without a correlated subquery; kept in sync by a trigger on
-- tickets so any writer (Next.js, Python scraper, ad-hoc SQL) stays consistent
-- without remembering to touch a second column.

ALTER TABLE shows
  ADD COLUMN IF NOT EXISTS min_price NUMERIC(7, 2);

-- Recomputes shows.min_price for a single show. Excludes price = 0 and NULL
-- so "free / RSVP" tickets do not collapse the cheapest-paid signal — those
-- shows surface via the separate Free filter (TASK-2141) instead.
CREATE OR REPLACE FUNCTION refresh_show_min_price(p_show_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE shows
    SET min_price = (
        SELECT MIN(price)
        FROM tickets
        WHERE show_id = p_show_id
          AND price IS NOT NULL
          AND price > 0
    )
    WHERE id = p_show_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION tickets_trickle_show_min_price()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        PERFORM refresh_show_min_price(OLD.show_id);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.show_id IS DISTINCT FROM NEW.show_id THEN
            PERFORM refresh_show_min_price(OLD.show_id);
        END IF;
        PERFORM refresh_show_min_price(NEW.show_id);
        RETURN NEW;
    ELSE
        PERFORM refresh_show_min_price(NEW.show_id);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- TRUNCATE does not fire row-level triggers, so keep the denormalized value
-- consistent for whole-table ticket rewrites by recomputing every show.
CREATE OR REPLACE FUNCTION tickets_refresh_all_show_min_prices()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE shows
    SET min_price = sub.min_price
    FROM (
        SELECT s.id AS show_id, MIN(t.price) AS min_price
        FROM shows s
        LEFT JOIN tickets t
          ON t.show_id = s.id
         AND t.price IS NOT NULL
         AND t.price > 0
        GROUP BY s.id
    ) sub
    WHERE shows.id = sub.show_id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tickets_trickle_show_min_price ON tickets;
DROP TRIGGER IF EXISTS tickets_trickle_show_min_price_ins ON tickets;
DROP TRIGGER IF EXISTS tickets_trickle_show_min_price_del ON tickets;
DROP TRIGGER IF EXISTS tickets_trickle_show_min_price_upd ON tickets;
DROP TRIGGER IF EXISTS tickets_refresh_all_show_min_prices_trunc ON tickets;

-- Split per-event so the UPDATE trigger can gate on actual value change. The
-- nightly scraper bulk-updates sold_out / purchase_url on tens of thousands
-- of unchanged-price rows; without the WHEN clause those would each fire a
-- shows-row UPDATE for no behavioral change.
CREATE TRIGGER tickets_trickle_show_min_price_ins
AFTER INSERT ON tickets
FOR EACH ROW
EXECUTE FUNCTION tickets_trickle_show_min_price();

CREATE TRIGGER tickets_trickle_show_min_price_del
AFTER DELETE ON tickets
FOR EACH ROW
EXECUTE FUNCTION tickets_trickle_show_min_price();

CREATE TRIGGER tickets_trickle_show_min_price_upd
AFTER UPDATE ON tickets
FOR EACH ROW
WHEN (OLD.price IS DISTINCT FROM NEW.price OR OLD.show_id IS DISTINCT FROM NEW.show_id)
EXECUTE FUNCTION tickets_trickle_show_min_price();

CREATE TRIGGER tickets_refresh_all_show_min_prices_trunc
AFTER TRUNCATE ON tickets
FOR EACH STATEMENT
EXECUTE FUNCTION tickets_refresh_all_show_min_prices();

-- One-shot backfill. MIN() already ignores NULLs; the join price > 0 guard is
-- what excludes free tickets from the denormalized value. The LEFT JOIN also
-- clears stale values for shows that no longer have priced tickets.
UPDATE shows
SET min_price = sub.min_price
FROM (
    SELECT s.id AS show_id, MIN(t.price) AS min_price
    FROM shows s
    LEFT JOIN tickets t
      ON t.show_id = s.id
     AND t.price IS NOT NULL
     AND t.price > 0
    GROUP BY s.id
) sub
WHERE shows.id = sub.show_id;
