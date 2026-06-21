-- Notification center high-water mark: notifications sent after this timestamp
-- are "unread". POST /api/v1/me/notifications/seen stamps it to now() to clear
-- the unread badge. NULL means the user has never opened the center.
ALTER TABLE "user_profiles" ADD COLUMN "notifications_last_seen_at" TIMESTAMPTZ;
