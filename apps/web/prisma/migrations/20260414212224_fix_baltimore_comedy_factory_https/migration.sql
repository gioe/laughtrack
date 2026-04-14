-- Fix Baltimore Comedy Factory website URL from http to https
UPDATE "Club"
SET website = 'https://www.baltimorecomedy.com/'
WHERE id = 86;
