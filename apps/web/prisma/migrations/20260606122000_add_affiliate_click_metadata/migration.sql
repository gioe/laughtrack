ALTER TABLE ticket_purchase_click_events
    ADD COLUMN destination_provider TEXT,
    ADD COLUMN routed_destination_url TEXT,
    ADD COLUMN affiliate_applied BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN fallback_reason TEXT;
