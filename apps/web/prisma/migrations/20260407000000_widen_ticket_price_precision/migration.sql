-- AlterTable: widen ticket price from DECIMAL(5,2) to DECIMAL(7,2)
-- to support prices over 999.99 (e.g. VIP/premium ticket tiers)
ALTER TABLE "tickets" ALTER COLUMN "price" TYPE DECIMAL(7,2);
