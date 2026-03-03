/*
  Warnings:

  - You are about to drop the column `selectable` on the `tags` table. All the data in the column will be lost.

*/
-- DropIndex
DROP INDEX "tags_selectable_idx";

-- AlterTable
ALTER TABLE "tags" DROP COLUMN "selectable",
ALTER COLUMN "visibility" SET DEFAULT 'ADMIN';
