-- Add optional tour platform ID fields to comedians table
ALTER TABLE "comedians" ADD COLUMN IF NOT EXISTS "songkick_id" TEXT;
ALTER TABLE "comedians" ADD COLUMN IF NOT EXISTS "bandsintown_id" TEXT;
