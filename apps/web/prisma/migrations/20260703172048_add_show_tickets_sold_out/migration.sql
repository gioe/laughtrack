-- Denormalized ticket-only sold-out state per show. The home and show search
-- availability filters used to express "no tickets OR any unsold ticket" as
-- relation predicates, which PostgreSQL planned as full tickets-table scans for
-- hot LIMIT queries. This column keeps that ticket state on shows so those
-- paths can filter without scanning tickets.

ALTER TABLE shows
  ADD COLUMN IF NOT EXISTS tickets_sold_out BOOLEAN NOT NULL DEFAULT false;

-- Recomputes shows.tickets_sold_out for a single show. Empty ticket sets are
-- not sold out; otherwise the value is true only when every ticket is sold_out.
CREATE OR REPLACE FUNCTION refresh_show_tickets_sold_out(p_show_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE shows
    SET tickets_sold_out = COALESCE(
        (
            SELECT BOOL_AND(sold_out)
            FROM tickets
            WHERE show_id = p_show_id
        ),
        false
    )
    WHERE id = p_show_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION tickets_trickle_show_tickets_sold_out()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        PERFORM refresh_show_tickets_sold_out(OLD.show_id);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.show_id IS DISTINCT FROM NEW.show_id THEN
            PERFORM refresh_show_tickets_sold_out(OLD.show_id);
        END IF;
        PERFORM refresh_show_tickets_sold_out(NEW.show_id);
        RETURN NEW;
    ELSE
        PERFORM refresh_show_tickets_sold_out(NEW.show_id);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- TRUNCATE does not fire row-level triggers, so keep the denormalized value
-- consistent for whole-table ticket rewrites by recomputing every show.
CREATE OR REPLACE FUNCTION tickets_refresh_all_show_tickets_sold_out()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE shows
    SET tickets_sold_out = sub.tickets_sold_out
    FROM (
        SELECT
            s.id AS show_id,
            COALESCE(
                BOOL_AND(t.sold_out) FILTER (WHERE t.id IS NOT NULL),
                false
            ) AS tickets_sold_out
        FROM shows s
        LEFT JOIN tickets t ON t.show_id = s.id
        GROUP BY s.id
    ) sub
    WHERE shows.id = sub.show_id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tickets_trickle_show_tickets_sold_out_ins ON tickets;
DROP TRIGGER IF EXISTS tickets_trickle_show_tickets_sold_out_del ON tickets;
DROP TRIGGER IF EXISTS tickets_trickle_show_tickets_sold_out_upd ON tickets;
DROP TRIGGER IF EXISTS tickets_refresh_all_show_tickets_sold_out_trunc ON tickets;

CREATE TRIGGER tickets_trickle_show_tickets_sold_out_ins
AFTER INSERT ON tickets
FOR EACH ROW
EXECUTE FUNCTION tickets_trickle_show_tickets_sold_out();

CREATE TRIGGER tickets_trickle_show_tickets_sold_out_del
AFTER DELETE ON tickets
FOR EACH ROW
EXECUTE FUNCTION tickets_trickle_show_tickets_sold_out();

CREATE TRIGGER tickets_trickle_show_tickets_sold_out_upd
AFTER UPDATE ON tickets
FOR EACH ROW
WHEN (
    OLD.sold_out IS DISTINCT FROM NEW.sold_out
    OR OLD.show_id IS DISTINCT FROM NEW.show_id
)
EXECUTE FUNCTION tickets_trickle_show_tickets_sold_out();

CREATE TRIGGER tickets_refresh_all_show_tickets_sold_out_trunc
AFTER TRUNCATE ON tickets
FOR EACH STATEMENT
EXECUTE FUNCTION tickets_refresh_all_show_tickets_sold_out();

-- One-shot backfill. Empty ticket sets remain false; shows with mixed tickets
-- remain false; only shows whose existing tickets are all sold_out become true.
UPDATE shows
SET tickets_sold_out = sub.tickets_sold_out
FROM (
    SELECT
        s.id AS show_id,
        COALESCE(
            BOOL_AND(t.sold_out) FILTER (WHERE t.id IS NOT NULL),
            false
        ) AS tickets_sold_out
    FROM shows s
    LEFT JOIN tickets t ON t.show_id = s.id
    GROUP BY s.id
) sub
WHERE shows.id = sub.show_id;
