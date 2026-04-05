-- Remove 13 deny list entries that contain 2+ real comedian names combined
-- into a single record. The new name_splitter module now splits these patterns
-- ("X & Y", "X with Y") into individual lineup items during scraping, so these
-- entries no longer need to be blocked.

DELETE FROM comedian_deny_list WHERE name IN (
    'Amber Wallin & Jazmyn W.',
    'Charles Engle & Colin Armstrong',
    'Corey B & Marcus Monroe',
    'ENRIQUE CHACON & HEATH CORDES FROM KILL TONY',
    'Josh Sharp & Aaron Jackson',
    'Kiki Yeung & Esther Ku',
    'Landon Bryant and Mary Ryan Brown',
    'AJ Finney with Samara Suomi',
    'Brent Terhune with Eli Wilz',
    'Joe Gorga with Special Guest Frank Catania',
    'Jon Bramnick with Vinnie Brand!',
    'Kelly Collette with Santiago Garcia',
    'Mike Lester with Lily Meyer'
);
