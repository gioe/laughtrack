ALTER TABLE user_profiles
  ADD COLUMN IF NOT EXISTS nearby_distance_miles INTEGER;
