-- Tag known comedy festivals with club_type = 'festival'
UPDATE clubs
SET club_type = 'festival'
WHERE id IN (
    301,  -- Cape Fear Comedy Festival
    549,  -- DC Sketchfest
    559,  -- DEMO Big Pine Comedy Festival
    573,  -- Big Pine Comedy Festival
    780,  -- Omaha Improv Festival (Workshops)
    784,  -- Omaha Improv Festival (Shows)
    795,  -- Show Em Comedy Festival
    834,  -- Limestone Comedy Festival
    836,  -- 208 Comedy Fest
    839   -- Submit to the 208 Comedy Festival Please
);
