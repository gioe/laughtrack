-- Global observe-first rollout flags for YouTube WebSub.
CREATE TABLE youtube_websub_settings (
  id INTEGER PRIMARY KEY DEFAULT 1,
  feed_ingestion_enabled BOOLEAN NOT NULL DEFAULT false,
  push_delivery_enabled BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT youtube_websub_settings_singleton_check CHECK (id = 1)
);

INSERT INTO youtube_websub_settings (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- Per-comedian rollout gates. Defaults keep the feed and push delivery dark
-- until an admin explicitly opts a comedian into each stage.
ALTER TABLE comedians
  ADD COLUMN youtube_live_feed_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN youtube_live_notifications_enabled BOOLEAN NOT NULL DEFAULT false;

-- User-level preference is distinct from show push notifications so live
-- delivery can be rolled out independently.
ALTER TABLE user_profiles
  ADD COLUMN push_youtube_live_notifications BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE youtube_websub_subscriptions (
  id SERIAL PRIMARY KEY,
  comedian_id TEXT NOT NULL,
  youtube_channel_id TEXT NOT NULL,
  topic_url TEXT NOT NULL,
  callback_url TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  lease_seconds INTEGER,
  lease_expires_at TIMESTAMPTZ,
  subscribed_at TIMESTAMPTZ,
  unsubscribed_at TIMESTAMPTZ,
  last_subscribe_attempt_at TIMESTAMPTZ,
  last_subscribe_status_code INTEGER,
  last_subscribe_error TEXT,
  last_verified_at TIMESTAMPTZ,
  last_notification_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT youtube_websub_subscriptions_comedian_id_fkey
    FOREIGN KEY (comedian_id) REFERENCES comedians(uuid) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE UNIQUE INDEX youtube_websub_subscriptions_youtube_channel_id_key
  ON youtube_websub_subscriptions(youtube_channel_id);

CREATE INDEX youtube_websub_subscriptions_comedian_id_idx
  ON youtube_websub_subscriptions(comedian_id);

CREATE INDEX youtube_websub_subscriptions_status_lease_expires_at_idx
  ON youtube_websub_subscriptions(status, lease_expires_at);

CREATE TABLE youtube_websub_events (
  id SERIAL PRIMARY KEY,
  comedian_id TEXT,
  youtube_channel_id TEXT,
  youtube_video_id TEXT,
  video_title TEXT,
  video_url TEXT,
  topic_url TEXT,
  event_status TEXT NOT NULL DEFAULT 'received',
  verification_status TEXT,
  live_broadcast_content TEXT,
  scheduled_start_time TIMESTAMPTZ,
  actual_start_time TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  feed_updated_at TIMESTAMPTZ,
  verified_at TIMESTAMPTZ,
  failure_reason TEXT,
  suppression_reason TEXT,
  payload_xml TEXT NOT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT youtube_websub_events_comedian_id_fkey
    FOREIGN KEY (comedian_id) REFERENCES comedians(uuid) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX youtube_websub_events_received_at_idx
  ON youtube_websub_events(received_at);

CREATE INDEX youtube_websub_events_youtube_channel_id_received_at_idx
  ON youtube_websub_events(youtube_channel_id, received_at);

CREATE INDEX youtube_websub_events_youtube_video_id_idx
  ON youtube_websub_events(youtube_video_id);

CREATE INDEX youtube_websub_events_event_status_received_at_idx
  ON youtube_websub_events(event_status, received_at);

CREATE INDEX youtube_websub_events_verification_status_received_at_idx
  ON youtube_websub_events(verification_status, received_at);

ALTER TABLE youtube_live_notifications
  ADD COLUMN youtube_websub_event_id INTEGER,
  ADD CONSTRAINT youtube_live_notifications_youtube_websub_event_id_fkey
    FOREIGN KEY (youtube_websub_event_id) REFERENCES youtube_websub_events(id) ON DELETE SET NULL ON UPDATE CASCADE;

CREATE INDEX youtube_live_notifications_youtube_websub_event_id_idx
  ON youtube_live_notifications(youtube_websub_event_id);

CREATE TABLE youtube_live_notification_deliveries (
  id SERIAL PRIMARY KEY,
  youtube_live_notification_id INTEGER NOT NULL,
  push_token_id TEXT,
  platform TEXT,
  delivery_status TEXT NOT NULL DEFAULT 'pending',
  status_code INTEGER,
  failure_reason TEXT,
  attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT youtube_live_notification_deliveries_notification_id_fkey
    FOREIGN KEY (youtube_live_notification_id) REFERENCES youtube_live_notifications(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT youtube_live_notification_deliveries_push_token_id_fkey
    FOREIGN KEY (push_token_id) REFERENCES user_push_tokens(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX youtube_live_notification_deliveries_notification_id_idx
  ON youtube_live_notification_deliveries(youtube_live_notification_id);

CREATE INDEX youtube_live_notification_deliveries_push_token_id_idx
  ON youtube_live_notification_deliveries(push_token_id);

CREATE INDEX youtube_live_notification_deliveries_delivery_status_attempted_at_idx
  ON youtube_live_notification_deliveries(delivery_status, attempted_at);
