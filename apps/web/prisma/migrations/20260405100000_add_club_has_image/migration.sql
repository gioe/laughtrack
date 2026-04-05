-- Add has_image column to clubs table
ALTER TABLE clubs ADD COLUMN has_image BOOLEAN NOT NULL DEFAULT false;

-- Populate has_image for 39 clubs with existing CDN images
UPDATE clubs SET has_image = true WHERE name IN (
  'Addison Improv', 'Arlington Improv', 'Brea Improv', 'Brokerage Comedy Club',
  'Bushwick Comedy Club', 'Caveat', 'Chelsea Music Hall', 'Chicago Improv',
  'Comedy Cellar New York', 'Comedy Shop', 'Comedy Village', 'Comic Strip Live',
  'Dark Horse Comedy Club', 'Eastville Comedy Club Brooklyn', 'Gotham Comedy Club',
  'Governors'' Comedy Club', 'Grove 34', 'Hollywood Improv', 'Houston Improv',
  'Irvine Improv', 'McGuire''s Comedy Club', 'Milwaukee Improv',
  'New York Comedy Club East Village', 'New York Comedy Club Midtown',
  'New York Comedy Club Upper West Side', 'Ontario Improv', 'Pittsburgh Improv',
  'Raleigh Improv', 'Rodney''s', 'San Jose Improv', 'St. Marks Comedy Club',
  'The Bellhouse', 'The Broadway Comedy Club', 'The Grisly Pear Greenwich Village',
  'The Grisly Pear Midtown', 'The Stand', 'The Tiny Cupboard', 'Union Hall',
  'West Side Comedy Club'
);
