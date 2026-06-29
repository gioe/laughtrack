-- TASK-3509: seed pilot YouTube channel IDs for WebSub live notification rollout.
--
-- Each row below was verified from the canonical YouTube channel page link and
-- its matching WebSub feed topic:
--
-- Andrew Schulz
--   Source: https://www.youtube.com/@TheAndrewSchulz
--   Feed:   https://www.youtube.com/feeds/videos.xml?channel_id=UCLZc32yrTEMxH1ZO-6fKOzA
-- Bert Kreischer
--   Source: https://www.youtube.com/@bertkreischer
--   Feed:   https://www.youtube.com/feeds/videos.xml?channel_id=UCz_sgiKcwX6V52KPn_B6PxQ
-- Bill Burr
--   Source: https://www.youtube.com/@BillBurrOfficial
--   Feed:   https://www.youtube.com/feeds/videos.xml?channel_id=UCAp990eMLzmei84WNR4ptgA
-- Mark Normand
--   Source: https://www.youtube.com/@marknormand
--   Feed:   https://www.youtube.com/feeds/videos.xml?channel_id=UCGmMFJB36GBXTgaLtfGd6Jg
-- Sam Morril
--   Source: https://www.youtube.com/@sammorril
--   Feed:   https://www.youtube.com/feeds/videos.xml?channel_id=UCTrOYaMDI7QiPnRzwWdYK6Q
-- Stavros Halkias
--   Source: https://www.youtube.com/@StavvyBaby
--   Feed:   https://www.youtube.com/feeds/videos.xml?channel_id=UC7bouvhSTd2RQwYOi7zq0hQ
-- Taylor Tomlinson
--   Source: https://www.youtube.com/@taylortomlinsoncomedy
--   Feed:   https://www.youtube.com/feeds/videos.xml?channel_id=UCYIEv9W7RmdpvFkHX7IEmyg

UPDATE comedians
SET youtube_channel_id = 'UCLZc32yrTEMxH1ZO-6fKOzA'
WHERE uuid = '52fff4aa2c108bf2f94d7388f53a3558'
  AND NULLIF(youtube_channel_id, '') IS NULL;

UPDATE comedians
SET youtube_channel_id = 'UCz_sgiKcwX6V52KPn_B6PxQ'
WHERE uuid = '9bb6e8c84387e7f07e0c64f89f2c6dce'
  AND NULLIF(youtube_channel_id, '') IS NULL;

UPDATE comedians
SET youtube_channel_id = 'UCAp990eMLzmei84WNR4ptgA'
WHERE uuid = '258a6d8425ed0336c5229a29bfa6c597'
  AND NULLIF(youtube_channel_id, '') IS NULL;

UPDATE comedians
SET youtube_channel_id = 'UCGmMFJB36GBXTgaLtfGd6Jg'
WHERE uuid = 'e7b44caab5051dae1127e4189f37a5bb'
  AND NULLIF(youtube_channel_id, '') IS NULL;

UPDATE comedians
SET youtube_channel_id = 'UCTrOYaMDI7QiPnRzwWdYK6Q'
WHERE uuid = 'c7b0bed1655f8259184895cdc1c3b386'
  AND NULLIF(youtube_channel_id, '') IS NULL;

UPDATE comedians
SET youtube_channel_id = 'UC7bouvhSTd2RQwYOi7zq0hQ'
WHERE uuid = 'db4c56cfe37e1913d8cbe7df9af4aa14'
  AND NULLIF(youtube_channel_id, '') IS NULL;

UPDATE comedians
SET youtube_channel_id = 'UCYIEv9W7RmdpvFkHX7IEmyg'
WHERE uuid = '67b2a98f21fc7b4a0c1b986fc02346fd'
  AND NULLIF(youtube_channel_id, '') IS NULL;
