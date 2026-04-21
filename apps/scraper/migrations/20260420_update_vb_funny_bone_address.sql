-- TASK-1679: Update Virginia Beach Funny Bone (id=1033) address to reflect
-- the Aug 2025 physical relocation from Town Center to Pembroke Square.
--
-- Old address (DB):  4554 Virginia Beach Blvd Suite 100, Virginia Beach, VA 23462
-- New address:       217 Central Park Ave, Virginia Beach, VA 23462
--
-- Source: Ticketmaster Discovery API venue record Z7r9jZadLz reports
-- address.line1="217 Central Park Ave", city="Virginia Beach", stateCode="VA",
-- postalCode="23462". The zip code is unchanged (Pembroke Square is within
-- 23462), so only the street address column needs updating.
--
-- Relocation context: https://www.wavy.com/news/local-news/virginia-beach/funny-bone-comedy-club-expanding-at-old-pembroke-mall-in-virginia-beach/

UPDATE clubs
SET address = '217 Central Park Ave, Virginia Beach, VA 23462'
WHERE id = 1033;
