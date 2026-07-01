-- Backfill Orlando Funny Bone headliner lineups that were missed by show-title
-- enrichment before single-token/high-confidence title matching was broadened.
INSERT INTO lineup_items (show_id, comedian_id)
VALUES
  (2993589, '92b94ab9045a483522b41f5ab40cf6ed'), -- Dave Williamson
  (2358552, '92b94ab9045a483522b41f5ab40cf6ed'), -- Dave Williamson
  (2993591, '92b94ab9045a483522b41f5ab40cf6ed'), -- Dave Williamson
  (3543901, '92b94ab9045a483522b41f5ab40cf6ed'), -- Dave Williamson
  (1055534, 'c93cae678ac9aca52fe6289f725f937a'), -- Godfrey
  (1055535, 'c93cae678ac9aca52fe6289f725f937a'), -- Godfrey
  (1055536, 'c93cae678ac9aca52fe6289f725f937a'), -- Godfrey
  (1055537, 'c93cae678ac9aca52fe6289f725f937a'), -- Godfrey
  (1055561, '81eec3a56b51a62bd8ab360cd1fca012'), -- Don DC Curry
  (1055562, '81eec3a56b51a62bd8ab360cd1fca012'), -- Don DC Curry
  (1055563, '81eec3a56b51a62bd8ab360cd1fca012'), -- Don DC Curry
  (1055564, '81eec3a56b51a62bd8ab360cd1fca012'), -- Don DC Curry
  (2993690, 'ef35941a3acc05a46cf84b4c5ef2ef7c'), -- Jane Don't Does America
  (1055615, 'e9ad9c2394f7dc7b6a69fb43e52a7382'), -- Earthquake
  (1055616, 'e9ad9c2394f7dc7b6a69fb43e52a7382'), -- Earthquake
  (1055617, 'e9ad9c2394f7dc7b6a69fb43e52a7382'), -- Earthquake
  (1055618, 'e9ad9c2394f7dc7b6a69fb43e52a7382'), -- Earthquake
  (2993731, 'bc37359006e676eefad3282937803f2c')  -- Davide De Pierro
ON CONFLICT DO NOTHING;
