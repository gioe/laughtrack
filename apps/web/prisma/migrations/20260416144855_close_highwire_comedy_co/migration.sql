-- Close Highwire Comedy Co. (club 793)
-- Permanently closed venue in Doraville, GA. Yelp marked CLOSED (March 2026),
-- website domain (highwirecomedy.com) is for sale, SeatEngine API returns 404.
UPDATE clubs
SET visible = false,
    status = 'closed',
    closed_at = NOW()
WHERE id = 793;
