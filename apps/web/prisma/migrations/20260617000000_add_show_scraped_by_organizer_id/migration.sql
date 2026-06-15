-- Per-show Eventbrite organizer attribution (TASK-2861).
-- shows.scraped_by_organizer_id records the production company whose organizer
-- /o/ feed most recently produced the show (stamped at persist time for
-- organizer-mode scrapes; NULL for single-venue / direct shows). The stale-show
-- reconciler scopes its DELETE to (club_id, scraped_by_organizer_id) so a sibling
-- organizer/source's shows at a shared venue are never deleted, and cancelled
-- shows at multi-organizer venues ARE reconciled — fully closing the TASK-2859
-- conservative-skip bootstrap gap.

-- AlterTable
ALTER TABLE "shows" ADD COLUMN "scraped_by_organizer_id" INTEGER;

-- AddForeignKey
ALTER TABLE "shows" ADD CONSTRAINT "shows_scraped_by_organizer_id_fkey" FOREIGN KEY ("scraped_by_organizer_id") REFERENCES "production_companies"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- CreateIndex
CREATE INDEX "shows_club_id_scraped_by_organizer_id_idx" ON "shows"("club_id", "scraped_by_organizer_id");
