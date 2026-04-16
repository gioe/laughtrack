-- Close Chuckles Comedy House (club 813) — permanently closed Sept 2024
UPDATE clubs
SET visible = false,
    status = 'closed',
    closed_at = NOW()
WHERE id = 813;
