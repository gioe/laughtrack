-- Track when each comedian's YouTube subscriber count was last refreshed so the
-- weekly refresh job can skip anyone updated within the staleness window,
-- mirroring instagram_followers_refreshed_at so both platforms refresh as a
-- weekly cohort (see scripts.core.refresh_social_followers --platform youtube).
-- IF NOT EXISTS keeps `prisma migrate deploy` a safe no-op if the column was
-- already applied out-of-band (it was pre-applied to prod to smoke-test the job).
ALTER TABLE "comedians"
  ADD COLUMN IF NOT EXISTS "youtube_followers_refreshed_at" TIMESTAMPTZ;
