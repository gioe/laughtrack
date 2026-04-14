-- Fix Baltimore Comedy Factory website URL from http to https
UPDATE clubs
SET website = 'https://www.baltimorecomedy.com/'
WHERE id = 86;
