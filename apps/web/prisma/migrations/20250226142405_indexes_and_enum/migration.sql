/*
  Warnings:

  - You are about to drop the column `display` on the `tags` table. All the data in the column will be lost.
  - You are about to drop the column `value` on the `tags` table. All the data in the column will be lost.
  - A unique constraint covering the columns `[type,slug]` on the table `tags` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateEnum
CREATE TYPE "TagVisibility" AS ENUM ('PUBLIC', 'ADMIN');

-- DropIndex
DROP INDEX "tags_type_value_key";

-- AlterTable
ALTER TABLE "tags" DROP COLUMN "display",
DROP COLUMN "value",
ADD COLUMN     "name" TEXT,
ADD COLUMN     "restrictContent" BOOLEAN NOT NULL DEFAULT false,
ADD COLUMN     "selectable" BOOLEAN NOT NULL DEFAULT true,
ADD COLUMN     "slug" TEXT,
ADD COLUMN     "visibility" "TagVisibility" NOT NULL DEFAULT 'PUBLIC';

-- CreateIndex
CREATE INDEX "tags_visibility_idx" ON "tags"("visibility");

-- CreateIndex
CREATE INDEX "tags_selectable_idx" ON "tags"("selectable");

-- CreateIndex
CREATE INDEX "tags_restrictContent_idx" ON "tags"("restrictContent");

-- CreateIndex
CREATE UNIQUE INDEX "tags_type_slug_key" ON "tags"("type", "slug");
