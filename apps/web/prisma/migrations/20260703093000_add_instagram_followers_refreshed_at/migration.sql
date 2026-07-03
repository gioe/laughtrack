-- Track when each comedian's Instagram follower count was last refreshed so the
-- weekly refresh job can skip anyone updated within the staleness window
-- (see scripts.core.refresh_social_followers --platform instagram).
-- IF NOT EXISTS keeps `prisma migrate deploy` a safe no-op if the column was
-- already applied out-of-band (it was pre-applied to prod to smoke-test the job).
ALTER TABLE "comedians"
  ADD COLUMN IF NOT EXISTS "instagram_followers_refreshed_at" TIMESTAMPTZ;
