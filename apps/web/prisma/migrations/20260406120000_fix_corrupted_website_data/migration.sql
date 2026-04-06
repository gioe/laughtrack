-- Fix corrupted website data: clear single-char junk values
UPDATE "Comedian"
SET website = NULL
WHERE website IS NOT NULL AND LENGTH(website) < 5;

-- Prepend https:// to website values missing a scheme
UPDATE "Comedian"
SET website = 'https://' || website
WHERE website IS NOT NULL
  AND website != ''
  AND website NOT LIKE 'http://%'
  AND website NOT LIKE 'https://%';
