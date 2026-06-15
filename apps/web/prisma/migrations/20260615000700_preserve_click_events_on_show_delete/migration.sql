-- Preserve ticket-purchase click attribution when a show is hard-deleted.
-- Stale-show reconciliation, the cleanup scripts, and the bulk future-show
-- purges all DELETE FROM shows; with ON DELETE CASCADE that cascade-removed the
-- historical click/affiliate-attribution events for those shows. Switch show_id
-- to nullable + ON DELETE SET NULL so the click event survives the show: club_id
-- stays valid and the denormalized routing fields (destination_url,
-- routed_destination_url, destination_provider, affiliate_applied,
-- fallback_reason, source_surface) keep the attribution intact.

-- DropForeignKey
ALTER TABLE "ticket_purchase_click_events" DROP CONSTRAINT "ticket_purchase_click_events_show_id_fkey";

-- AlterTable
ALTER TABLE "ticket_purchase_click_events" ALTER COLUMN "show_id" DROP NOT NULL;

-- AddForeignKey
ALTER TABLE "ticket_purchase_click_events" ADD CONSTRAINT "ticket_purchase_click_events_show_id_fkey" FOREIGN KEY ("show_id") REFERENCES "shows"("id") ON DELETE SET NULL ON UPDATE CASCADE;
