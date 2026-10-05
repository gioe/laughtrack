-- TASK-4104: remove only the verified Summer Season Pass placeholder.
-- Preserve click attribution via the existing ON DELETE SET NULL relation.
DO $cleanup$
DECLARE
    deleted_count integer;
BEGIN
    CREATE TEMP TABLE task4104_cohort (show_id integer PRIMARY KEY, ticket_id integer,
        date timestamptz, url text) ON COMMIT DROP;
    INSERT INTO task4104_cohort VALUES
    (3434154,3773351,'2026-09-30T19:00:00+00:00'::timestamptz,
     'https://www.standingroomonlytickets.com/WebOffice/EventList/536');
    PERFORM 1 FROM shows s JOIN task4104_cohort c ON c.show_id=s.id FOR UPDATE OF s;
    IF EXISTS (SELECT 1 FROM shows s JOIN task4104_cohort c ON c.show_id=s.id
        WHERE s.club_id<>11473 OR s.name IS DISTINCT FROM 'Summer Season Pass'
        OR s.date<>c.date OR s.show_page_url<>c.url OR s.last_scraped_by IS DISTINCT FROM 'standing_room_only') THEN
        RAISE EXCEPTION 'TASK-4104: audited pass identity drift';
    END IF;
    IF EXISTS (SELECT 1 FROM tickets t JOIN task4104_cohort c ON c.show_id=t.show_id
        WHERE t.id<>c.ticket_id OR t.price IS NOT NULL) THEN
        RAISE EXCEPTION 'TASK-4104: unexpected ticket or admission-price drift';
    END IF;
    IF EXISTS (SELECT 1 FROM lineup_items WHERE show_id IN (SELECT show_id FROM task4104_cohort))
        OR EXISTS (SELECT 1 FROM saved_shows WHERE show_id IN (SELECT show_id FROM task4104_cohort))
        OR EXISTS (SELECT 1 FROM sent_notifications WHERE show_id IN (SELECT show_id FROM task4104_cohort))
        OR EXISTS (SELECT 1 FROM discovery_show_feature_snapshots WHERE show_id IN (SELECT show_id FROM task4104_cohort)) THEN
        RAISE EXCEPTION 'TASK-4104: protected dependencies appeared; retain shows for review';
    END IF;
    PERFORM 1 FROM ticket_purchase_click_events WHERE show_id IN
        (SELECT show_id FROM task4104_cohort) FOR UPDATE;
    CREATE TEMP TABLE task4104_clicks ON COMMIT DROP AS
        SELECT id, to_jsonb(t)-'show_id' AS attribution FROM ticket_purchase_click_events t
        WHERE show_id IN (SELECT show_id FROM task4104_cohort);
    DELETE FROM shows WHERE id IN (SELECT show_id FROM task4104_cohort);
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    IF EXISTS (SELECT 1 FROM task4104_clicks c LEFT JOIN ticket_purchase_click_events t ON t.id=c.id
        WHERE t.id IS NULL OR t.show_id IS NOT NULL OR to_jsonb(t)-'show_id' IS DISTINCT FROM c.attribution) THEN
        RAISE EXCEPTION 'TASK-4104: click attribution was not preserved';
    END IF;
    UPDATE clubs SET total_shows=(SELECT count(*) FROM shows WHERE club_id=11473) WHERE id=11473;
    RAISE NOTICE 'TASK-4104: removed % audited pass products; preserved % click records',
        deleted_count, (SELECT count(*) FROM task4104_clicks);
END
$cleanup$;
