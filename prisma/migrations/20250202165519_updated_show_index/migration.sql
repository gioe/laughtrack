/*
  Warnings:

  - A unique constraint covering the columns `[club_id,date,name]` on the table `shows` will be added. If there are existing duplicate values, this will fail.

*/
-- DropIndex
DROP INDEX "shows_club_id_date_key";

-- CreateIndex
CREATE UNIQUE INDEX "shows_club_id_date_name_key" ON "shows"("club_id", "date", "name");
