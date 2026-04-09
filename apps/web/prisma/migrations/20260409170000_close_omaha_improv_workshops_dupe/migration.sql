-- Close and hide Omaha Improv Festival (Workshops) (id=780)
-- Duplicate of Omaha Improv Festival (Shows) (id=784) — both point to omahaimprovfest.com
-- Keep id=784 for seasonal scraping

UPDATE clubs SET status = 'closed', visible = false WHERE id = 780;
