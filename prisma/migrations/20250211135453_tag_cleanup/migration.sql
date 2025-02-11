/*
  Warnings:

  - A unique constraint covering the columns `[id]` on the table `tagged_clubs` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[id]` on the table `tagged_comedians` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[id]` on the table `tagged_shows` will be added. If there are existing duplicate values, this will fail.

*/
-- DropForeignKey
ALTER TABLE "tagged_clubs" DROP CONSTRAINT "tagged_clubs_club_id_fkey";

-- CreateIndex
CREATE UNIQUE INDEX "tagged_clubs_id_key" ON "tagged_clubs"("id");

-- CreateIndex
CREATE UNIQUE INDEX "tagged_comedians_id_key" ON "tagged_comedians"("id");

-- CreateIndex
CREATE UNIQUE INDEX "tagged_shows_id_key" ON "tagged_shows"("id");

-- AddForeignKey
ALTER TABLE "tagged_clubs" ADD CONSTRAINT "tagged_clubs_club_id_fkey" FOREIGN KEY ("club_id") REFERENCES "clubs"("id") ON DELETE CASCADE ON UPDATE CASCADE;
