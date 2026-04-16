-- Close ComedyWorks (club 810) — permanently closed June 2014, Montreal comedy club
UPDATE clubs
SET visible = false,
    status = 'closed',
    closed_at = NOW()
WHERE id = 810;
