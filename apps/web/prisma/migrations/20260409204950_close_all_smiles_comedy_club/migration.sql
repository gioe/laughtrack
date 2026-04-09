-- Close All Smiles Comedy Club (id=597, Humble, TX)
-- Website allsmilescomedyclub.com returns 404 on all pages
-- SeatEngine API /api/venues/581/shows returns 404
-- No alternative ticketing platform found; Facebook page is inactive placeholder

UPDATE clubs
SET status = 'closed',
    visible = false,
    closed_at = NOW()
WHERE id = 597;
