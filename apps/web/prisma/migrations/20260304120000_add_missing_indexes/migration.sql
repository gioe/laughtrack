-- CreateIndex
CREATE INDEX "shows_date_idx" ON "shows"("date");

-- CreateIndex
CREATE INDEX "clubs_visible_idx" ON "clubs"("visible");

-- CreateIndex
CREATE INDEX "comedians_parent_comedian_id_idx" ON "comedians"("parent_comedian_id");
