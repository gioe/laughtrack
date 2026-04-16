-- Close Jester's Comedy Club (club 798)
-- Venue is defunct — bulk-imported from SeatEngine on 2026-04-06, never returned shows
-- Primary domain jesters.cc does not resolve (DNS failure — domain expired)
-- Alternate domain clubjester.com (referenced on do317 aggregator) also fails DNS lookup
-- SeatEngine API returns 404 for stored venue ID 219
-- SeatEngine subdomain www-jesters-cc.seatengine.com redirects to seatengine.com home (account deactivated)
-- do317 aggregator lists no upcoming events, only past; X account @jesters_comedy returns 402 (restricted)
-- Previously located at 402 Brown Street, West Lafayette, IN (confirmed via do317 archived address)
UPDATE clubs SET visible = false, status = 'closed', closed_at = NOW() WHERE id = 798;
