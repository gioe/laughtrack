DELETE FROM shows
WHERE date > NOW() + INTERVAL '18 months';
