-- TASK-2100: decode HTML entities already persisted in shows.description and
-- shows.room before Show.__post_init__ normalized those fields at the scraper
-- boundary. Production audit found 18,768 affected descriptions and 0 affected
-- rooms on 2026-05-09.

WITH decoded AS (
    SELECT
        id,
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(description,
            '&quot;', '"'),
            '&apos;', ''''),
            '&nbsp;', ' '),
            '&amp;', '&'),
            '&lt;', '<'),
            '&gt;', '>'),
            '&#39;', ''''),
            '&#039;', ''''),
            '&#34;', '"'),
            '&#64;', '@'),
            '&#61;', '='),
            '&#43;', '+'),
            '&#010;', chr(10)),
            '&#x1f3a4;', chr(127908)),
            '&#x1f30a;', chr(127754)),
            '&#xfeff;', chr(65279)) AS description,
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(
        replace(room,
            '&quot;', '"'),
            '&apos;', ''''),
            '&nbsp;', ' '),
            '&amp;', '&'),
            '&lt;', '<'),
            '&gt;', '>'),
            '&#39;', ''''),
            '&#039;', ''''),
            '&#34;', '"'),
            '&#64;', '@'),
            '&#61;', '='),
            '&#43;', '+'),
            '&#010;', chr(10)),
            '&#x1f3a4;', chr(127908)),
            '&#x1f30a;', chr(127754)),
            '&#xfeff;', chr(65279)) AS room
    FROM shows
    WHERE description ~ '&(amp|lt|gt|quot|apos|nbsp|#[0-9]+|#x[0-9A-Fa-f]+);'
       OR room ~ '&(amp|lt|gt|quot|apos|nbsp|#[0-9]+|#x[0-9A-Fa-f]+);'
)
UPDATE shows AS s
SET
    description = decoded.description,
    room = decoded.room
FROM decoded
WHERE s.id = decoded.id
  AND (s.description IS DISTINCT FROM decoded.description
       OR s.room IS DISTINCT FROM decoded.room);
