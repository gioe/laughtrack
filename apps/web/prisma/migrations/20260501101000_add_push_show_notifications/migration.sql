ALTER TABLE user_profiles
  ADD COLUMN IF NOT EXISTS push_show_notifications BOOLEAN NOT NULL DEFAULT false;
