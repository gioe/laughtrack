/*
  Warnings:

  - You are about to drop the column `key_words` on the `tags` table. All the data in the column will be lost.
  - You are about to drop the column `pattern` on the `tags` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "tags" DROP COLUMN "key_words",
DROP COLUMN "pattern";
