-- Fix Off The Hook Comedy Club (club 122) — update website to HTTPS, populate city/state
UPDATE "clubs"
SET website = 'https://offthehookcomedy.com',
    city = 'Naples',
    state = 'FL'
WHERE id = 122;
