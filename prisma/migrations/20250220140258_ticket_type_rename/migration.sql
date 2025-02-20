/*
  Warnings:

  - You are about to drop the column `ticket_type` on the `tickets` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "tickets" DROP COLUMN "ticket_type",
ADD COLUMN     "type" TEXT;
