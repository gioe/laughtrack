/*
  Warnings:

  - You are about to drop the column `scaper` on the `clubs` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "clubs" DROP COLUMN "scaper",
ADD COLUMN     "scraper" TEXT;
