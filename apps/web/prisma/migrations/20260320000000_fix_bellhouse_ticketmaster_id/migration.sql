-- Fix ticketmaster_id for The Bellhouse.
-- The previous migration set '393383' which is not a valid Ticketmaster venue ID.
-- The correct Ticketmaster Discovery API venue ID is 'KovZ917ARvk'.
UPDATE clubs
SET "ticketmaster_id" = 'KovZ917ARvk'
WHERE name = 'The Bellhouse';
