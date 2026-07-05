-- Groups sent_notifications rows that belonged to the same notification run
-- (one grouped push per user). The in-app notification center reads by this id
-- to render one entry per push sent instead of one row per show. Nullable:
-- rows written before this column fall back to per-show rendering.

ALTER TABLE sent_notifications
  ADD COLUMN IF NOT EXISTS notification_group_id TEXT;

CREATE INDEX IF NOT EXISTS "sent_notifications_user_id_notification_group_id_idx"
  ON sent_notifications (user_id, notification_group_id);
