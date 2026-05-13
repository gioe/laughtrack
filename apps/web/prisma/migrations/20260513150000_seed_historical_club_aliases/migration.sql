-- TASK-2167: seed vetted aliases from historical duplicate-club resolutions.
--
-- Each row below is backed by a prior merge/hide/delete audit that established
-- same physical venue + same location + canonical club. The JOIN against clubs
-- is intentionally strict so this migration never creates an alias for a
-- missing or unexpectedly changed canonical venue.

WITH alias_seed (
    club_id,
    canonical_name,
    alias_name,
    normalized_alias_name,
    city,
    state,
    normalized_city,
    normalized_state,
    source
) AS (
    VALUES
        -- Comedy on State: 20260414014323 hid club 826 as duplicate of club 435;
        -- 20260416225053 confirmed same 202 State Street / madisoncomedy.com URL.
        (435, 'Comedy on State', 'Comedy Club On State', 'comedy club on state',
         'Madison', 'WI', 'madison', 'wi',
         'TASK-2167: 20260414014323 + 20260416225053 duplicate resolution'),
        (435, 'Comedy on State', 'The Comedy Club On State', 'the comedy club on state',
         'Madison', 'WI', 'madison', 'wi',
         'TASK-2167: 20260414014323 + 20260416225053 duplicate resolution'),

        -- Bananas: 20260411133329 hid club 87 as duplicate of club 850;
        -- 20260416225053 confirmed same Rutherford address and bananascomedyclub.com.
        (850, 'Bananas Comedy Club', 'Bananas Comedy Club Renaissance Hotel',
         'bananas comedy club renaissance hotel', 'Rutherford', 'NJ', 'rutherford', 'nj',
         'TASK-2167: 20260411133329 + 20260416225053 duplicate resolution'),

        -- Laugh Factory: TASK-1956 audit and 20260508160000 documented
        -- Eventbrite ghost rows/aliases for canonical chain locations.
        (160, 'Laugh Factory Hollywood', 'Laugh Factory - Hollywood',
         'laugh factory hollywood', 'Los Angeles', 'CA', 'los angeles', 'ca',
         'TASK-2167: TASK-1956 audit + 20260508160000 orphan cleanup'),
        (169, 'Laugh Factory Long Beach', 'Long Beach Laugh Factory',
         'long beach laugh factory', 'Long Beach', 'CA', 'long beach', 'ca',
         'TASK-2167: TASK-1956 audit Eventbrite ghost row'),
        (170, 'Laugh Factory San Diego', 'Laugh Factory',
         'laugh factory', 'San Diego', 'CA', 'san diego', 'ca',
         'TASK-2167: TASK-1956 audit + 20260508160000 orphan cleanup'),

        -- Big Couch: TASK-1916/TASK-1919 established Eventbrite organizer
        -- naming split; fold_big_couch_dup_clubs_row.py hid club 2287.
        (654, 'Big Couch New Orleans', 'Big Couch',
         'big couch', 'New Orleans', 'LA', 'new orleans', 'la',
         'TASK-2167: TASK-1916 audit + TASK-1925 fold script'),

        -- Fort Lauderdale Improv: TASK-2114 merge log folded abbreviated
        -- tour-date text into canonical club 53.
        (53, 'Fort Lauderdale Improv', 'Ft. Lauderdale Improv',
         'fort lauderdale improv', 'Dania Beach', 'FL', 'dania beach', 'fl',
         'TASK-2167: TASK-2114 abbreviation duplicate merge')
)
INSERT INTO club_aliases (
    club_id,
    alias_name,
    normalized_alias_name,
    city,
    state,
    normalized_city,
    normalized_state,
    source,
    verified
)
SELECT
    s.club_id,
    s.alias_name,
    s.normalized_alias_name,
    s.city,
    s.state,
    s.normalized_city,
    s.normalized_state,
    s.source,
    TRUE
FROM alias_seed AS s
JOIN clubs AS c
  ON c.id = s.club_id
 AND c.name = s.canonical_name
 AND LOWER(TRIM(c.city)) = s.normalized_city
 AND LOWER(TRIM(c.state)) = s.normalized_state
WHERE c.visible = TRUE
  AND c.status = 'active'
ON CONFLICT (normalized_alias_name, normalized_city, normalized_state) DO NOTHING;
