ALTER TABLE comedians
  ADD COLUMN youtube_channel_id TEXT;

CREATE TABLE youtube_live_notifications (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  comedian_id TEXT NOT NULL,
  youtube_channel_id TEXT NOT NULL,
  youtube_video_id TEXT NOT NULL,
  video_title TEXT,
  video_url TEXT NOT NULL,
  notification_type TEXT NOT NULL DEFAULT 'push',
  sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT youtube_live_notifications_notification_type_check
    CHECK (notification_type IN ('email', 'push')),
  CONSTRAINT youtube_live_notifications_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT youtube_live_notifications_comedian_id_fkey
    FOREIGN KEY (comedian_id) REFERENCES comedians(uuid) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE UNIQUE INDEX youtube_live_notifications_unique_per_channel
  ON youtube_live_notifications(user_id, comedian_id, youtube_video_id, notification_type);

CREATE INDEX youtube_live_notifications_user_id_idx
  ON youtube_live_notifications(user_id);

CREATE INDEX youtube_live_notifications_comedian_id_idx
  ON youtube_live_notifications(comedian_id);

CREATE INDEX youtube_live_notifications_youtube_channel_id_idx
  ON youtube_live_notifications(youtube_channel_id);
