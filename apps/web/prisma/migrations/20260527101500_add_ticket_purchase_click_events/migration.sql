CREATE TABLE "ticket_purchase_click_events" (
    "id" SERIAL PRIMARY KEY,
    "show_id" INTEGER NOT NULL,
    "club_id" INTEGER NOT NULL,
    "profile_id" TEXT,
    "anonymous_visitor_id" TEXT NOT NULL,
    "destination_url" TEXT NOT NULL,
    "source_surface" TEXT NOT NULL,
    "user_agent" TEXT,
    "device_metadata" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT "ticket_purchase_click_events_show_id_fkey"
        FOREIGN KEY ("show_id") REFERENCES "shows"("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "ticket_purchase_click_events_club_id_fkey"
        FOREIGN KEY ("club_id") REFERENCES "clubs"("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "ticket_purchase_click_events_profile_id_fkey"
        FOREIGN KEY ("profile_id") REFERENCES "user_profiles"("id") ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX "ticket_purchase_click_events_created_at_idx"
    ON "ticket_purchase_click_events"("created_at");
CREATE INDEX "ticket_purchase_click_events_show_id_created_at_idx"
    ON "ticket_purchase_click_events"("show_id", "created_at");
CREATE INDEX "ticket_purchase_click_events_club_id_created_at_idx"
    ON "ticket_purchase_click_events"("club_id", "created_at");
CREATE INDEX "ticket_purchase_click_events_profile_id_created_at_idx"
    ON "ticket_purchase_click_events"("profile_id", "created_at");
CREATE INDEX "ticket_purchase_click_events_anonymous_visitor_id_created_at_idx"
    ON "ticket_purchase_click_events"("anonymous_visitor_id", "created_at");

CREATE OR REPLACE FUNCTION cleanup_old_ticket_purchase_click_events()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM ticket_purchase_click_events
    WHERE created_at < NOW() - INTERVAL '13 months';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;
